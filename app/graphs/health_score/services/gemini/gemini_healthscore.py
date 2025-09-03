# app/services/gemini/gemini_healthscore.py
import json
from typing import Dict, Any
from app.services.shared.gemini.gemini_client import make_client, extract_text_from_response, first_json_block
from app.models.health_score import HealthScoreInput, HealthScoreOutput
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from app.prompts.health_score_prompt import HEALTH_SCORE_PROMPT
from google.genai import types

def _load_prompt() -> str:
    return HEALTH_SCORE_PROMPT

def score_with_gemini(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Calls Gemini with the rubric prompt; expects strict JSON back."""
    prompt = _load_prompt()
    client = make_client(project=None, location=None)
    
    # Build a compact, LLM-friendly input object
    inp = HealthScoreInput(**payload).model_dump()
    user_json = json.dumps(inp, ensure_ascii=False)

    # Pass 1: free JSON (deterministic)
    cfg1 = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=2048,
        thinking_config=types.ThinkingConfig(thinking_budget=128),
    )
    resp1 = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=f"{prompt}\n\nINPUT:\n{user_json}")])],
        config=cfg1,
    )
    raw1 = extract_text_from_response(resp1) or getattr(resp1, "text", "")
    data = first_json_block(raw1)

    # Pass 2: force schema if needed
    if not data or "health_score" not in data:
        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "health_score": types.Schema(type=types.Type.NUMBER),
                "component_scores": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "energy_density": types.Schema(type=types.Type.NUMBER),
                        "protein_density": types.Schema(type=types.Type.NUMBER),
                        "fat_balance": types.Schema(type=types.Type.NUMBER),
                        "carb_quality": types.Schema(type=types.Type.NUMBER),
                        "sodium_proxy": types.Schema(type=types.Type.NUMBER),
                        "whole_foods": types.Schema(type=types.Type.NUMBER),
                    },
                    required=["energy_density", "protein_density", "fat_balance", "carb_quality", "sodium_proxy", "whole_foods"]
                ),
                "weights": types.Schema(type=types.Type.OBJECT),
                "drivers_positive": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "drivers_negative": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "debug": types.Schema(type=types.Type.OBJECT),
                "classification": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.OBJECT)),
            },
            required=["health_score", "component_scores", "weights"]
        )
        cfg2 = types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=schema,
            max_output_tokens=4096,
            thinking_config=types.ThinkingConfig(thinking_budget=128),
        )
        resp2 = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=f"{prompt}\n\nINPUT:\n{user_json}")])],
            config=cfg2,
        )
        raw2 = extract_text_from_response(resp2) or getattr(resp2, "text", "")
        data = first_json_block(raw2) or {}
        if "health_score" not in data:
            return {"error": "health_score_failed", "raw": raw2 or raw1}

    # Validate & coerce
    try:
        out = HealthScoreOutput(**data)
        return out.model_dump()
    except Exception as e:
        return {"error": "health_score_validation_failed", "message": str(e), "raw": raw1}
