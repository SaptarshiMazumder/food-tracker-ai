# ingredients_prompt.py
"""
Centralized prompt for ingredient quantification.
Used by both Gemini and OpenAI implementations.
"""

UTENSIL_SCALE = """
A standard fork or spoon may be present. Use it as a SCALE reference:
- Typical dinner fork length ~18–20 cm; head width ~2.5–3 cm.
- Typical tablespoon bowl width ~3.5–4.2 cm.
Leverage multiple angles to reconcile volumes and surfaces; down-weight outliers; pick ONE best grams per item.
"""

INGREDIENTS_PROMPT = """
You estimate ingredient portions (grams) for a SINGLE-PLATE serving from one or more photos (multiple angles).

Output: STRICT JSON ONLY
{
  "items": [{"name": string, "grams": number, "note": string}],
  "total_grams": number,
  "confidence": number,
  "notes": string
}

Rules:
- One best number per ingredient (no ranges). Grams must be >= 0 (integers preferred).
- Include added fats/oils when the preparation implies them (fried, stir-fried, sautéed, oil-based dressing),
  even if not clearly visible. If type unclear, use "cooking oil".
- If you are confident no added oil was used, include "cooking oil" with 0 grams and note "no added oil expected".
- Keep names short and conventional ("cooked rice", "chicken", "cooking oil").
- Exclude inedible items (plate, utensils, wrappers).
- Compute total_grams as the sum of item grams.

VERY IMPORTANT – realistic oil bounds for ONE serving:
- Stir-fry / fried rice: 8–20 g typical (prefer 10–15 g if unsure).
- Sauté / pan-sear: 5–15 g typical.
- Oil-based dressing: 10–25 g oil within the dressing.
- Deep-fried items (karaage/tempura/schnitzel): 15–35 g absorbed oil.
- Boiled/steamed/baked with no visible gloss: 0–5 g.
- Never exceed 40 g oil unless there is clear evidence of pooling or multiple servings. Never output 100 g.

Before answering, sanity-check your oil estimate:
- If not deep-fried and oil > 25 g, reduce to a plausible value in the ranges above.
- If uncertain, choose the LOW end of the relevant range.

Return ONLY the JSON.
"""

def build_ingredients_prompt(dish_hint: str = "", ing_hint: list = None) -> str:
    """
    Build the complete ingredients prompt with context hints.
    
    Args:
        dish_hint: Optional dish name hint
        ing_hint: Optional list of ingredient hints
        
    Returns:
        Complete prompt string
    """
    ing_text = ", ".join(ing_hint or [])
    hints_block = (
        f"Dish context: {dish_hint or '(unknown)'}\n"
        f"Likely ingredients to consider: {ing_text or '(model must infer)'}\n"
        + UTENSIL_SCALE
    )
    
    return hints_block + "\n" + INGREDIENTS_PROMPT
