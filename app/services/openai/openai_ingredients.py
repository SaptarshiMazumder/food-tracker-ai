# openai_ingredients.py
import re
import base64
import os
from typing import Dict, List, Optional
from openai import OpenAI

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



def make_client() -> OpenAI:
    """
    Create OpenAI client using environment variables.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    return OpenAI(api_key=api_key)

def prepare_image_parts(image_paths: List[str]) -> List[Dict]:
    """
    Prepare image parts for OpenAI API from file paths.
    """
    image_parts = []
    for image_path in image_paths:
        if not os.path.exists(image_path):
            continue
        
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Determine file extension for mime type
            ext = os.path.splitext(image_path)[1].lower()
            mime_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.webp': 'image/webp',
                '.gif': 'image/gif'
            }
            mime_type = mime_type_map.get(ext, 'image/jpeg')
            
            image_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{base64_image}"
                }
            })
    
    return image_parts

def extract_text_from_response(response) -> str:
    """
    Extract text from OpenAI response.
    """
    if hasattr(response, 'choices') and response.choices:
        return response.choices[0].message.content or ""
    return ""

def first_json_block(text: str) -> Optional[Dict]:
    """
    Extract the first JSON block from text.
    """
    if not text:
        return None
    
    # Look for JSON blocks
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, text, re.DOTALL)
    
    for match in matches:
        try:
            import json
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return None

def ingredients_from_image(project: Optional[str], location: str, model: str,
                           image_paths: List[str], dish_hint: str = "", ing_hint: Optional[List[str]] = None) -> Dict:
    """
    Ask OpenAI GPT to list EDIBLE components and return a SINGLE BEST estimate in grams for each item (no ranges).
    Returns:
      { items:[{name, grams, note?}], total_grams, confidence, notes? }
      or { "error": "...", "raw": "..." }
    """
    client = make_client()
    img_parts = prepare_image_parts(image_paths)

    # Use centralized prompt
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    from prompts.food_analysis.ingredients_prompt import build_ingredients_prompt
    prompt_block = build_ingredients_prompt(dish_hint, ing_hint)

    # Combine all parts for the message
    content_parts = [
        {"type": "text", "text": prompt_block}
    ] + img_parts

    # Pass 1: free JSON (deterministic)
    try:
        resp1 = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": content_parts
                }
            ],
            temperature=0.0,
            max_tokens=2048,
            response_format={"type": "json_object"}
        )
        raw1 = extract_text_from_response(resp1)
        data = first_json_block(raw1) if raw1 else None

        # If JSON parsing failed, try without response_format
        if not data:
            resp1_fallback = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": content_parts
                    }
                ],
                temperature=0.0,
                max_tokens=2048
            )
            raw1 = extract_text_from_response(resp1_fallback)
            data = first_json_block(raw1)

    except Exception as e:
        return {"error": f"openai_api_error: {str(e)}", "raw": ""}

    # Pass 2: force schema if needed
    if not data or any(k not in data for k in NEEDED):
        # For OpenAI, we'll try with a more explicit prompt
        schema_prompt = prompt_block + "\n\nIMPORTANT: You must return valid JSON with exactly these fields: items (array), total_grams (number), confidence (number), notes (string). Each item in items must have name (string) and grams (number)."
        
        try:
            resp2 = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": schema_prompt}
                        ] + img_parts
                    }
                ],
                temperature=0.0,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            raw2 = extract_text_from_response(resp2)
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
        except Exception as e:
            return {"error": f"openai_schema_error: {str(e)}", "raw": raw1 or ""}

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
