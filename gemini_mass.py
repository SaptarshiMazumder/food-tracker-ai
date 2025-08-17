# gemini_mass.py
from typing import Dict, Optional, List
from google.genai import types
from gemini_client import make_client, prepare_image_part, extract_text_from_response, first_json_block

NEEDED = ["grams_low","grams_high","confidence"]

def mass_from_image(project: Optional[str], location: str, model: str,
                    image_path: str,
                    dish: str = "", ingredients: Optional[List[str]] = None) -> Dict:
    """
    Ask Gemini to estimate edible mass in grams directly from the photo.
    Returns dict with grams_low, grams_high, confidence, notes OR {"error":..., "raw":...}.
    """
    client = make_client(project or "", location)
    img_part = prepare_image_part(client, image_path)

    ingredient_hint = ", ".join(ingredients or [])
    prompt = (
        "You are estimating the edible mass of the food shown in this single image.\n"
        "Rules:\n"
        "- Consider only the food, not the plate, utensils, napkins or garnish that is not eaten.\n"
        "- If multiple items are present but clearly part of one serving, estimate total mass.\n"
        "- Assume common restaurant/home portioning and typical densities for the cuisine unless an obvious oversized/small portion.\n"
        "- Provide a realistic RANGE in grams.\n"
        "- If uncertain, widen the range slightly (do not refuse).\n\n"
        f"Context (may help): dish='{dish}', ingredients='{ingredient_hint or '(unknown)'}'.\n\n"
        "Return STRICT JSON ONLY with keys:\n"
        "{ \"grams_low\": number, \"grams_high\": number, \"confidence\": number, \"notes\": string }\n"
    )

    # Attempt 1: free JSON (text)
    cfg1 = types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=1024,
        thinking_config=types.ThinkingConfig(thinking_budget=128),
    )
    resp1 = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=[img_part, types.Part.from_text(text=prompt)])],
        config=cfg1,
    )
    raw1 = extract_text_from_response(resp1) or getattr(resp1, "text", "")
    data = first_json_block(raw1)

    # Attempt 2: force schema JSON
    if not data or any(k not in data for k in NEEDED):
        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "grams_low":  types.Schema(type=types.Type.NUMBER),
                "grams_high": types.Schema(type=types.Type.NUMBER),
                "confidence": types.Schema(type=types.Type.NUMBER),
                "notes":      types.Schema(type=types.Type.STRING),
            },
            required=["grams_low","grams_high","confidence"]
        )
        cfg2 = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=schema,
            max_output_tokens=2048,
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
            return {"error": "mass_estimate_failed", "raw": raw2 or raw1}

    try:
        gL = float(data["grams_low"]); gH = float(data["grams_high"])
        if gL < 0: gL = 0.0
        if gH < gL: gH = gL
        return {
            "grams_low": gL,
            "grams_high": gH,
            "confidence": float(data.get("confidence", 0.6)),
            "notes": data.get("notes"),
        }
    except Exception:
        return {"error":"mass_estimate_cast_failed", "raw": raw1}
