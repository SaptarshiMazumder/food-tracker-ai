# app/services/gemini/gemini_nutrition.py
import json
from pathlib import Path
from typing import Dict, Any
from app.services.shared.gemini.gemini_client import make_client, extract_text_from_response, first_json_block
from google.genai import types

PROMPT_PATH = Path(__file__).resolve().parents[4] / "prompts" / "nutrition_breakdown.md"

def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")

def llm_nutrition_breakdown(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    input_data: { "hint": str } or { "hint": str, "context": {...optional fields you want echoed} }
    Returns: dict exactly matching the required nutrition schema.
    """
    system = _load_prompt()
    user = json.dumps(input_data, ensure_ascii=False)

    client = make_client(project="", location="")
    cfg = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=2048,
    )
    resp = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=[
            types.Content(role="user", parts=[types.Part.from_text(text=system)]),
            types.Content(role="user", parts=[types.Part.from_text(text=f"INPUT:\n{user}")])
        ],
        config=cfg,
    )

    text = extract_text_from_response(resp) or getattr(resp, "text", "")
    data = first_json_block(text)

    # minimal sanity checks to fail early if LLM drifts
    required_top = [
        "angles_used","dish","dish_confidence","grams_confidence","ingredients_detected",
        "items_density","items_grams","items_kcal","items_nutrition","kcal_confidence",
        "notes","timings","total_carbs_g","total_fat_g","total_grams",
        "total_kcal","total_ms","total_protein_g"
    ]
    for k in required_top:
        if k not in data:
            raise ValueError(f"nutrition schema missing key: {k}")

    return data
