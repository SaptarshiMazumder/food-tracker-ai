# recognize_prompt.py
"""
Centralized prompt for dish recognition.
Used by both Gemini and OpenAI implementations.
"""

UTENSIL_SCALE = (
    "If a standard fork or spoon is visible, use it as a scale reference:\n"
    "- Typical dinner fork total length ~18–20 cm; head width ~2.5–3 cm.\n"
    "- Typical tablespoon bowl width ~3.5–4.2 cm.\n"
    "Leverage this to judge portion sizes realistically.\n"
    "If multiple angles are provided, reconcile them and infer a single best description.\n"
)

def build_recognize_prompt() -> str:
    """
    Build the complete dish recognition prompt.
    
    Returns:
        Complete prompt string
    """
    prompt = (
        "You are a precise food recognizer. Return STRICT JSON ONLY:\n"
        "{"
        "\"dish\":\"<short canonical dish>\","
        "\"ingredients\":[\"<3-12 likely ingredients, lowercase; include typical cooking fats/oils if implied (e.g., sesame oil for fried rice, olive oil for sautéed veg)>\"],"
        "\"container\":\"plate|bowl|tray|cup|none\","
        "\"confidence\":<0..1>"
        "}\n\n"
        + UTENSIL_SCALE
    )
    
    return prompt
