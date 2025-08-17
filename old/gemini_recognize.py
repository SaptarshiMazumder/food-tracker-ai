# gemini_recognize.py
from typing import Dict
from google.genai import types
from gemini_client import make_client, prepare_image_part, extract_text_from_response, first_json_block, recognize_schema

def gemini_recognize_dish(project: str, location: str, model: str, image_path: str) -> Dict:
    client = make_client(project, location)
    img_part = prepare_image_part(client, image_path)
    sys_prompt = (
        "You are a precise food recognizer. Return STRICT JSON ONLY:\n"
        "{"
        "\"dish\":\"<short canonical dish>\","
        "\"ingredients\":[\"<3-12 likely ingredients, lowercase>\"],"
        "\"container\":\"plate|bowl|tray|cup|none\","
        "\"confidence\":<0..1>"
        "}"
    )

    # Attempt 1: plain (no tools), free-form JSON
    cfg1 = types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=512,
        thinking_config=types.ThinkingConfig(thinking_budget=128),
    )
    resp1 = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=sys_prompt), img_part])],
        config=cfg1
    )
    raw1 = extract_text_from_response(resp1) or getattr(resp1, "text", "")
    data = first_json_block(raw1)

    # Attempt 2: structured JSON with schema
    if not data or "dish" not in data:
        cfg2 = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=recognize_schema(),
            max_output_tokens=1024,
            thinking_config=types.ThinkingConfig(thinking_budget=128),
        )
        resp2 = client.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=sys_prompt), img_part])],
            config=cfg2
        )
        raw2 = extract_text_from_response(resp2) or getattr(resp2, "text", "")
        data = first_json_block(raw2)

        if not data or "dish" not in data:
            return {"error": "recognition_failed", "raw": raw1 or raw2}

    data["dish"] = (data.get("dish") or "").lower().strip()
    data["ingredients"] = [str(x).lower().strip() for x in (data.get("ingredients") or [])][:12]
    data["container"] = (data.get("container") or "none").lower().strip()
    data["confidence"] = float(data.get("confidence", 0.0))
    return data
