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

    # Use centralized prompt
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    from app.prompts.food_analysis.ingredients_prompt import build_ingredients_prompt
    prompt_block = build_ingredients_prompt(dish_hint, ing_hint)

    # Pass 1: free JSON (deterministic)
    cfg1 = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=2048,
        thinking_config=types.ThinkingConfig(thinking_budget=128),
    )
    parts = [types.Part.from_text(text=prompt_block)] + img_parts
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
