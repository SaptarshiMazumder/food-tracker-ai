# calories_prompt.py
"""
Centralized prompt for calories and macronutrient analysis.
Used by both Gemini and OpenAI implementations.
"""

def build_calories_prompt(dish_hint: str, items_text: str, oil_g: float) -> str:
    """
    Build the complete calories prompt with context hints.
    
    Args:
        dish_hint: Optional dish name hint
        items_text: JSON string of items with names and grams
        oil_g: Detected cooking oil grams
        
    Returns:
        Complete prompt string
    """
    
    oil_policy = (
        "OIL ACCOUNTING RULE:\n"
        "- If 'cooking oil' grams > 0, treat ALL other items as cooked WITHOUT added oil; "
        "keep only their intrinsic fat. Do not allocate frying/stir-fry oil to those items. "
        "All added oil kcal/macros must be in the 'cooking oil' item only.\n"
        "- If 'cooking oil' grams == 0, you may include typical absorbed oil in fried items.\n"
        f"- Detected cooking oil grams in this request: {oil_g:.1f} g.\n"
    )
    
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
    
    return prompt
