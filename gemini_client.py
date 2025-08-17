# gemini_client.py
import os, json, re
from typing import List, Dict
from google import genai
from google.genai import types
import base64

def make_client(project: str, location: str) -> genai.Client:
    api_key = os.getenv("GOOGLE_API_KEY")
    if project:
        try:
            return genai.Client(vertexai=True, project=project, location=location)
        except Exception:
            if api_key:
                return genai.Client(api_key=api_key)
            raise
    if not api_key:
        raise RuntimeError("Provide GOOGLE_CLOUD_PROJECT (Vertex) or GOOGLE_API_KEY.")
    return genai.Client(api_key=api_key)

def prepare_image_part(client: genai.Client, path: str):
    """
    Prefer File API; fallback to inline bytes.
    """
    try:
        return client.files.upload(file=path)
    except Exception:
        with open(path, "rb") as f:
            data = f.read()
        ext = os.path.splitext(path)[1].lower()
        mime = "image/jpeg" if ext in [".jpg",".jpeg"] else ("image/png" if ext==".png" else "image/webp")
        return types.Part.from_bytes(data=data, mime_type=mime)

def prepare_image_parts(client: genai.Client, paths: List[str]):
    parts = []
    for p in paths:
        parts.append(prepare_image_part(client, p))
    return parts

def encode_image_to_part(path: str) -> types.Part:
    with open(path, "rb") as f:
        data = f.read()
    ext = os.path.splitext(path)[1].lower()
    mime = "image/jpeg" if ext in [".jpg",".jpeg"] else ("image/png" if ext==".png" else "image/webp")
    return types.Part.from_bytes(data=data, mime_type=mime)

def extract_text_from_response(resp) -> str:
    """Return JSON/text from parts; also decode inline_data if needed."""
    try:
        for cand in (getattr(resp, "candidates", []) or []):
            content = getattr(cand, "content", None)
            if not content: continue
            for part in (getattr(content, "parts", []) or []):
                t = getattr(part, "text", None)
                if isinstance(t, str) and t.strip():
                    return t
                inline = getattr(part, "inline_data", None)
                if inline:
                    data = getattr(inline, "data", None)
                    if isinstance(data, (bytes, bytearray)):
                        return data.decode("utf-8", "ignore")
                    if isinstance(data, str):
                        try:
                            return base64.b64decode(data).decode("utf-8", "ignore")
                        except Exception:
                            return data
        top = getattr(resp, "text", None)
        return top if isinstance(top, str) else ""
    except Exception:
        return ""

def first_json_block(text) -> Dict:
    """Accept dict/str/bytes/None. Return {} on failure."""
    if isinstance(text, dict):
        return text
    if isinstance(text, (bytes, bytearray)):
        try: text = text.decode("utf-8", "ignore")
        except Exception: return {}
    if not isinstance(text, str) or not text.strip():
        return {}
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, flags=re.S)
        if m:
            try: return json.loads(m.group(0))
            except Exception: pass
        return {}

def missing_keys(d: dict, keys: list[str]) -> list[str]:
    return [k for k in keys if k not in (d or {})]

def heightdens_schema() -> types.Schema:
    return types.Schema(
        type=types.Type.OBJECT,
        properties={
            "height_cm_low": types.Schema(type=types.Type.NUMBER),
            "height_cm_high": types.Schema(type=types.Type.NUMBER),
            "density_low": types.Schema(type=types.Type.NUMBER),
            "density_high": types.Schema(type=types.Type.NUMBER),
            "confidence": types.Schema(type=types.Type.NUMBER),
            "notes": types.Schema(type=types.Type.STRING),
        },
        required=["height_cm_low","height_cm_high","density_low","density_high","confidence"]
    )

def recognize_schema() -> types.Schema:
    return types.Schema(
        type=types.Type.OBJECT,
        properties={
            "dish": types.Schema(type=types.Type.STRING),
            "ingredients": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
            "container": types.Schema(type=types.Type.STRING),
            "confidence": types.Schema(type=types.Type.NUMBER),
        },
        required=["dish","ingredients","container","confidence"]
    )
