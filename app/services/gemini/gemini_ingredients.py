# gemini_ingredients.py
import re
from typing import Dict, List, Optional
from google.genai import types
from .gemini_client import make_client, prepare_image_parts, extract_text_from_response, first_json_block

def fnum(x, default=0.0) -> float:
    """
    Coerce anything numeric-ish to float.
    '0.95', '95%', '~12', '≈3.5' -> numbers; words like 'High' -> default.
    """
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.replace(",", "").strip()
        m = re.search(r"[-+]?\d+(\.\d+)?", s)
        if m:
            try:
                return float(m.group(0))
            except Exception:
                pass
    return float(default)

NEEDED = ["items", "total_grams", "confidence"]

UTENSIL_SCALE = """
A standard fork or spoon may be present. Use it as a SCALE reference:
- Typical dinner fork length ~18–20 cm; head width ~2.5–3 cm.
- Typical tablespoon bowl width ~3.5–4.2 cm.
Leverage multiple angles to reconcile volumes and surfaces; down-weight outliers; pick ONE best grams per item.
"""

def ingredients_from_image(project: Optional[str], location: str, model: str,
                           image_paths: List[str], dish_hint: str = "", ing_hint: Optional[List[str]] = None) -> Dict:
    """
    Ask Gemini to list EDIBLE components and return a SINGLE BEST estimate in grams for each item (no ranges).
    Returns:
      { items:[{name, grams, note?}], total_grams, confidence, notes? }
      or { "error": "...", "raw": "..." }
    """
    client = make_client(project or "", location)
    img_parts = prepare_image_parts(client, image_paths)

    prompt_block = """
You estimate ingredient portions (grams) for a SINGLE-PLATE serving from one or more photos (multiple angles).

Output: STRICT JSON ONLY
{
  "items": [{"name": string, "grams": number, "note": string}],
  "total_grams": number,
  "confidence": number,
  "notes": string
}

Rules:
- One best number per ingredient (no ranges). Grams must be >= 0 (integers preferred).
- Include added fats/oils when the preparation implies them (fried, stir-fried, sautéed, oil-based dressing),
  even if not clearly visible. If type unclear, use "cooking oil".
- If you are confident no added oil was used, include "cooking oil" with 0 grams and note "no added oil expected".
- Keep names short and conventional ("cooked rice", "chicken", "cooking oil").
- Exclude inedible items (plate, utensils, wrappers).
- Compute total_grams as the sum of item grams.

VERY IMPORTANT – realistic oil bounds for ONE serving:
- Stir-fry / fried rice: 8–20 g typical (prefer 10–15 g if unsure).
- Sauté / pan-sear: 5–15 g typical.
- Oil-based dressing: 10–25 g oil within the dressing.
- Deep-fried items (karaage/tempura/schnitzel): 15–35 g absorbed oil.
- Boiled/steamed/baked with no visible gloss: 0–5 g.
- Never exceed 40 g oil unless there is clear evidence of pooling or multiple servings. Never output 100 g.

Before answering, sanity-check your oil estimate:
- If not deep-fried and oil > 25 g, reduce to a plausible value in the ranges above.
- If uncertain, choose the LOW end of the relevant range.

Return ONLY the JSON.
"""
    ing_text = ", ".join(ing_hint or [])
    hints_block = (
        f"Dish context: {dish_hint or '(unknown)'}\n"
        f"Likely ingredients to consider: {ing_text or '(model must infer)'}\n"
        + UTENSIL_SCALE
    )

    # Pass 1: free JSON (deterministic)
    cfg1 = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=2048,
        thinking_config=types.ThinkingConfig(thinking_budget=128),
    )
    parts = [types.Part.from_text(text=hints_block), types.Part.from_text(text=prompt_block)] + img_parts
    resp1 = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=parts)],
        config=cfg1,
    )
    raw1 = extract_text_from_response(resp1) or getattr(resp1, "text", "")
    data = first_json_block(raw1)

    # Pass 2: force schema if needed
    if not data or any(k not in data for k in NEEDED):
        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "items": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "name":  types.Schema(type=types.Type.STRING),
                            "grams": types.Schema(type=types.Type.NUMBER),
                            "note":  types.Schema(type=types.Type.STRING),
                        },
                        required=["name","grams"]
                    )
                ),
                "total_grams": types.Schema(type=types.Type.NUMBER),
                "confidence":  types.Schema(type=types.Type.NUMBER),
                "notes":       types.Schema(type=types.Type.STRING),
            },
            required=NEEDED
        )
        cfg2 = types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=schema,
            max_output_tokens=4096,
            thinking_config=types.ThinkingConfig(thinking_budget=128),
        )
        resp2 = client.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=parts)],
            config=cfg2,
        )
        raw2 = extract_text_from_response(resp2) or getattr(resp2, "text", "")
        data = first_json_block(raw2) or {}
        if any(k not in data for k in NEEDED):
            # Backcompat: if model still returns grams_low/high, collapse to median.
            fallback = first_json_block(raw2 or raw1) or {}
            items = []
            for it in (fallback.get("items") or []):
                try:
                    name = str(it.get("name","")).lower().strip()
                    if "grams" in it:
                        g = fnum(it["grams"])
                    else:
                        gL = fnum(it.get("grams_low"), 0.0)
                        gH = fnum(it.get("grams_high"), gL)
                        g = max(0.0, (gL + max(gL, gH)) / 2.0)
                    items.append({"name": name, "grams": g, "note": it.get("note")})
                except Exception:
                    continue
            if not items:
                return {"error":"ingredients_failed", "raw": raw2 or raw1}
            total = fnum(fallback.get("total_grams"), sum(i["grams"] for i in items))
            return {
                "items": items,
                "total_grams": total,
                "confidence": fnum(fallback.get("confidence"), 0.6),
                "notes": fallback.get("notes"),
            }

    # normalize single-grams response (robust numbers)
    items = []
    for it in (data.get("items") or []):
        name = str(it.get("name") or "").strip().lower()
        g = fnum(it.get("grams"))
        if g < 0:
            g = 0.0
        items.append({"name": name, "grams": g, "note": it.get("note")})

    return {
        "items": items,
        "total_grams": fnum(data.get("total_grams"), sum(i["grams"] for i in items)),
        "confidence": fnum(data.get("confidence"), 0.6),
        "notes": data.get("notes"),
    }
