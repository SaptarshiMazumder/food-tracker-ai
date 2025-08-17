# gemini_calories.py
import re
from typing import Dict, List, Optional
from google.genai import types
from gemini_client import make_client, extract_text_from_response, first_json_block

def fnum(x, default=0.0) -> float:
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

NEEDED = [
    "items",
    "total_kcal",
    "total_protein_g",
    "total_carbs_g",
    "total_fat_g",
    "confidence",
]

def _items_to_text(items: List[Dict]) -> str:
    parts = []
    for it in items:
        name = str(it.get("name", "")).strip()
        grams = fnum(it.get("grams"))
        parts.append(f'{{"name":"{name}","grams":{grams}}}')
    return "[" + ", ".join(parts) + "]"

def calories_from_ingredients(
    project: Optional[str],
    location: str,
    model: str,
    dish_hint: str,
    items: List[Dict],
) -> Dict:
    """
    Input: items = [{ name, grams }]
    Output: {
      items: [{name,kcal,protein_g,carbs_g,fat_g,method?}],
      total_kcal,total_protein_g,total_carbs_g,total_fat_g,
      confidence,notes?
    }
    Enforces "single-source-of-truth" for added oil:
      - If a 'cooking oil' item (grams>0) exists, do NOT include added oil in any other item.
      - If no positive 'cooking oil', fried items may include typical absorbed oil.
    """
    client = make_client(project or "", location)

    # Detect oil presence in the request
    oil_g = 0.0
    for it in items:
        if "oil" in (it.get("name","").lower()):
            oil_g = max(oil_g, fnum(it.get("grams")))

    oil_policy = (
        "OIL ACCOUNTING RULE:\n"
        "- If 'cooking oil' grams > 0, treat ALL other items as cooked WITHOUT added oil; "
        "keep only their intrinsic fat. Do not allocate frying/stir-fry oil to those items. "
        "All added oil kcal/macros must be in the 'cooking oil' item only.\n"
        "- If 'cooking oil' grams == 0, you may include typical absorbed oil in fried items.\n"
        f"- Detected cooking oil grams in this request: {oil_g:.1f} g.\n"
    )

    items_text = _items_to_text(items)
    prompt = (
        "You are a careful nutrition estimator for cooked dishes. You only have the item names and grams.\n"
        "Return STRICT JSON ONLY with per-item kcal/macros using sane cooked-food constants.\n"
        "For fats:\n"
        "- generic cooking oils: 8.84 kcal/g (fat_g ~= grams, protein/carbs ~= 0)\n"
        "- butter: 7.17 kcal/g\n"
        "- typical cooked rice: ~1.30 kcal/g\n"
        "- lean cooked chicken breast (no skin): ~1.65 kcal/g; fried versions are higher due to batter/skin/oil\n"
        "Adjust intelligently by preparation words in names (steamed, boiled, fried, breaded, grilled, sauce, dressing, etc.)\n\n"
        + oil_policy +
        "\nRules:\n"
        "- Output a per-item array aligned to the input order and the same names.\n"
        "- Each item: {\"name\",\"kcal\",\"protein_g\",\"carbs_g\",\"fat_g\",\"method\"?}\n"
        "- Tally totals. Use realistic macronutrient breakdowns (kcal ≈ 4*protein + 4*carbs + 9*fat, allow small drift).\n"
        "- If unsure, choose conservative mid-range values rather than extremes.\n"
        "- Include a brief global 'notes' explaining any oil assumptions.\n\n"
        f"Dish context: {dish_hint or '(unknown)'}\n"
        f"Items (name + grams): {items_text}\n\n"
        "Return ONLY the JSON with keys: items,total_kcal,total_protein_g,total_carbs_g,total_fat_g,confidence,notes"
    )

    # Pass 1: free JSON (deterministic)
    cfg1 = types.GenerateContentConfig(
        temperature=0.0,
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

    # Pass 2: schema-enforced JSON if needed
    if not data or any(k not in data for k in NEEDED):
        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "items": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "name":      types.Schema(type=types.Type.STRING),
                            "kcal":      types.Schema(type=types.Type.NUMBER),
                            "protein_g": types.Schema(type=types.Type.NUMBER),
                            "carbs_g":   types.Schema(type=types.Type.NUMBER),
                            "fat_g":     types.Schema(type=types.Type.NUMBER),
                            "method":    types.Schema(type=types.Type.STRING),
                        },
                        required=["name","kcal","protein_g","carbs_g","fat_g"]
                    )
                ),
                "total_kcal":      types.Schema(type=types.Type.NUMBER),
                "total_protein_g": types.Schema(type=types.Type.NUMBER),
                "total_carbs_g":   types.Schema(type=types.Type.NUMBER),
                "total_fat_g":     types.Schema(type=types.Type.NUMBER),
                "confidence":      types.Schema(type=types.Type.NUMBER),
                "notes":           types.Schema(type=types.Type.STRING),
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
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=cfg2,
        )
        raw2 = extract_text_from_response(resp2) or getattr(resp2, "text", "")
        data = first_json_block(raw2) or {}
        if any(k not in data for k in NEEDED):
            return {"error": "calories_failed", "raw": raw2 or raw1}

    # Normalize items list (keep order & names) with robust numbers
    out_items = []
    for src in items:
        src_name = str(src.get("name") or "").strip()
        match = None
        for it in (data.get("items") or []):
            if str(it.get("name","")).strip().lower() == src_name.lower():
                match = it
                break
        if not match:
            out_items.append({"name": src_name, "kcal": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0})
            continue
        out_items.append({
            "name": src_name,
            "kcal": fnum(match.get("kcal")),
            "protein_g": fnum(match.get("protein_g")),
            "carbs_g": fnum(match.get("carbs_g")),
            "fat_g": fnum(match.get("fat_g")),
            **({"method": match["method"]} if match.get("method") else {})
        })

    return {
        "items": out_items,
        "total_kcal": fnum(data.get("total_kcal")),
        "total_protein_g": fnum(data.get("total_protein_g")),
        "total_carbs_g": fnum(data.get("total_carbs_g")),
        "total_fat_g": fnum(data.get("total_fat_g")),
        "confidence": fnum(data.get("confidence"), 0.6),
        "notes": data.get("notes"),
    }
