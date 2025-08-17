# gemini_calories.py
from typing import Dict, List, Optional
from google.genai import types
from gemini_client import make_client, extract_text_from_response, first_json_block

NEEDED = ["items","total_kcal","confidence"]

def calories_from_ingredients(project: Optional[str], location: str, model: str,
                              dish_hint: str,
                              items: List[Dict]) -> Dict:
    """
    Input items: [{name, grams}]
    Output: { items:[{name, kcal, method?}], total_kcal, confidence, notes? } or {error, raw}
    """
    client = make_client(project or "", location)

    # compact payload for the LLM
    payload = "[" + ",".join([f'{{"name":"{i["name"]}","grams":{float(i["grams"])}}}' for i in items]) + "]"

    prompt = (
        "Using typical nutrition references, estimate ENERGY (kcal) for each ingredient given its SINGLE mass in grams.\n"
        "Assumptions:\n"
        "- Use common kcal-per-100g values for typical prepared forms (e.g., cooked pasta, cooked ground beef, bun, American cheese), "
        "unless the ingredient clearly implies raw/uncooked.\n"
        "- Return a single best kcal estimate per item (no ranges), and a single total kcal.\n\n"
        f"Dish context: {dish_hint}\n"
        f"Items: {payload}\n\n"
        "STRICT JSON ONLY (no prose), schema:\n"
        "{"
        "\"items\":[{\"name\":string, \"kcal\":number, \"method\":string}],"
        "\"total_kcal\":number, \"confidence\":number, \"notes\":string"
        "}\n"
    )

    # Pass 1
    cfg1 = types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=2048,
        thinking_config=types.ThinkingConfig(thinking_budget=128),
    )
    resp1 = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
        config=cfg1,
    )
    raw1 = extract_text_from_response(resp1) or getattr(resp1, "text", "")
    data = first_json_block(raw1)

    # Pass 2 with schema
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
                            "kcal":  types.Schema(type=types.Type.NUMBER),
                            "method":types.Schema(type=types.Type.STRING),
                        },
                        required=["name","kcal"]
                    )
                ),
                "total_kcal": types.Schema(type=types.Type.NUMBER),
                "confidence": types.Schema(type=types.Type.NUMBER),
                "notes":      types.Schema(type=types.Type.STRING),
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
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=cfg2,
        )
        raw2 = extract_text_from_response(resp2) or getattr(resp2, "text", "")
        data = first_json_block(raw2) or {}
        if any(k not in data for k in NEEDED):
            # Backcompat: if it returns kcal_low/high, collapse to midpoint
            fallback = first_json_block(raw2 or raw1) or {}
            out_items = []
            for it in (fallback.get("items") or []):
                try:
                    name = str(it.get("name","")).lower().strip()
                    if "kcal" in it:
                        k = float(it["kcal"])
                    else:
                        kL = float(it.get("kcal_low", 0.0))
                        kH = float(it.get("kcal_high", kL))
                        k = max(0.0, (kL + max(kL, kH))/2.0)
                    out_items.append({"name": name, "kcal": k, "method": it.get("method")})
                except Exception:
                    continue
            if not out_items:
                return {"error":"calorie_estimate_failed", "raw": raw2 or raw1}
            total = float(fallback.get("total_kcal", sum(i["kcal"] for i in out_items)))
            return {"items": out_items, "total_kcal": total, "confidence": float(fallback.get("confidence", 0.6)), "notes": fallback.get("notes")}

    # normalize single-kcal response
    out_items = []
    for it in (data.get("items") or []):
        try:
            out_items.append({
                "name": str(it.get("name") or "").strip().lower(),
                "kcal": float(it.get("kcal", 0.0)),
                "method": it.get("method"),
            })
        except Exception:
            continue

    return {
        "items": out_items,
        "total_kcal": float(data.get("total_kcal", sum(x["kcal"] for x in out_items))),
        "confidence": float(data.get("confidence", 0.6)),
        "notes": data.get("notes"),
    }
