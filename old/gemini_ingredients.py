# gemini_ingredients.py
from typing import Dict, List, Optional
from google.genai import types
from gemini_client import make_client, prepare_image_part, extract_text_from_response, first_json_block

NEEDED = ["items", "total_grams", "confidence"]

def ingredients_from_image(project: Optional[str], location: str, model: str,
                           image_path: str, dish_hint: str = "", ing_hint: Optional[List[str]] = None) -> Dict:
    """
    Ask Gemini to list EDIBLE components and return a SINGLE BEST estimate in grams for each item (no ranges).
    Returns:
      { items:[{name, grams, note?}], total_grams, confidence, notes? }
      or { "error": "...", "raw": "..." }
    """
    client = make_client(project or "", location)
    img_part = prepare_image_part(client, image_path)

    ingr_text = ", ".join(ing_hint or [])
    prompt = (
        "Identify each EDIBLE component visible (e.g., bun top, beef patties, cheese slices, sauce).\n"
        "For EACH item, give a SINGLE BEST estimate of its mass in grams (no ranges). Combine duplicates "
        "(e.g., two patties -> 'beef patties'). Exclude plate/utensils/wrappers.\n\n"
        f"Context (optional): dish='{dish_hint}', possible ingredients='{ingr_text or '(unknown)'}'.\n\n"
        "Return STRICT JSON ONLY (no prose) with this schema:\n"
        "{"
        "\"items\":[{\"name\":string, \"grams\":number, \"note\":string}],"
        "\"total_grams\":number, \"confidence\":number, \"notes\":string"
        "}\n"
        "Rules:\n"
        "- Units: grams only.\n"
        "- If uncertain, still pick a best estimate (median of your internal range), don't output ranges.\n"
        "- Keep numbers realistic for what is shown in the photo.\n"
    )

    # Pass 1: free JSON
    cfg1 = types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=2048,
        thinking_config=types.ThinkingConfig(thinking_budget=128),
    )
    resp1 = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=[img_part, types.Part.from_text(text=prompt)])],
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
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=schema,
            max_output_tokens=4096,
            thinking_config=types.ThinkingConfig(thinking_budget=128),
        )
        resp2 = client.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=[img_part, types.Part.from_text(text=prompt)])],
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
                        g = float(it["grams"])
                    else:
                        gL = float(it.get("grams_low", 0.0))
                        gH = float(it.get("grams_high", gL))
                        g = max(0.0, (gL + max(gL, gH)) / 2.0)
                    items.append({"name": name, "grams": g, "note": it.get("note")})
                except Exception:
                    continue
            if not items:
                return {"error":"ingredients_failed", "raw": raw2 or raw1}
            total = float(fallback.get("total_grams", sum(i["grams"] for i in items)))
            return {
                "items": items,
                "total_grams": total,
                "confidence": float(fallback.get("confidence", 0.6)),
                "notes": fallback.get("notes"),
            }

    # normalize single-grams response
    items = []
    for it in (data.get("items") or []):
        try:
            name = str(it.get("name") or "").strip().lower()
            g = float(it.get("grams", 0.0))
            if g < 0: g = 0.0
            items.append({"name": name, "grams": g, "note": it.get("note")})
        except Exception:
            continue

    return {
        "items": items,
        "total_grams": float(data.get("total_grams", sum(i["grams"] for i in items))),
        "confidence": float(data.get("confidence", 0.6)),
        "notes": data.get("notes"),
    }
