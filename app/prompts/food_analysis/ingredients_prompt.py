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
You estimate ingredient portions (grams) for a SINGLE-PLATE serving from one or more photos of the SAME dish, taken from multiple angles.

Input: Up to N photos of the same plate (multiple angles).
Goal: Use all angles to improve portion-size accuracy.

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
- Use ALL angles. Reconcile discrepancies to produce ONE consolidated estimate for a single serving.

Multi-angle reasoning (REQUIRED):
1) Identify the primary plate/bowl across images. Ignore extra plates, duplicates, backgrounds.
2) Use cross-angle cues for scale: utensil size, hand size, plate diameter, container depth, cut thickness, piece counts.
3) Resolve occlusions: if an item is hidden in one angle but visible in another, include it once (no double counting).
4) Reconcile conflicts:
   - If two angles suggest different volumes, prefer the angle with better scale references (utensils/edge-to-edge view).
   - If still uncertain, choose the LOWER plausible estimate consistent with all angles and note the uncertainty.
5) Count pieces consistently across angles (e.g., 6 nuggets seen in one angle + breading clues in others).
6) Merge duplicates (e.g., "rice" seen in top view + side view is the same portion).
7) If any angle strongly indicates a preparation method (e.g., deep-fried crust, glossy oil sheen), apply that method globally.

Utensil scaling:
- If a spoon or fork is present in any photo, use it as a reference to judge portion size.
- Assume a standard dinner spoon/fork length of 19 cm (190 mm).
- If chopsticks are present, assume 24 cm length.
- Prefer utensil scaling over guesswork when plate depth/size is unclear.

**VERY IMPORTANT –** Subtle accuracy guidance for typical single-plate portions:
- Breads/flatbreads/buns/tortillas/wraps: prefer conservative weights for single pieces; avoid inflating a single slice/piece.
- Cooked rice/pasta/noodles: anchor to realistic single-plate volumes; down-weight visual puffing, clumping, or plate curvature illusions.
- When utensil or plate scale suggests smaller volumes, prefer the lower plausible grams consistent with the image context.
- If uncertain between two plausible grams, choose the LOWER value.
- You often tend to overestimate portions of bread and rice like food, do not overestimate them.

**VERY IMPORTANT –** realistic oil bounds for ONE serving:
- Stir-fry / fried rice: 8–20 g typical (prefer 10–15 g if unsure).
- Sauté / pan-sear: 5–15 g typical.
- Oil-based dressing: 10–25 g oil within the dressing.
- Deep-fried items (karaage/tempura/schnitzel): 15–35 g absorbed oil.
- Boiled/steamed/baked with no visible gloss: 0–5 g.
- Never exceed 40 g oil unless there is clear evidence of pooling or multiple servings. Never output 100 g.

**VERY IMPORTANT –** ALWAYS estimate the size and portions of the food based on the size and depth of the dish/ bowl/ background/ any other visual cues.
Before answering, sanity-check your oil estimate:
- If not deep-fried and oil > 25 g, reduce to a plausible value in the ranges above.
- If uncertain, choose the LOW end of the relevant range.

Edge cases:
- Mixed bowls (e.g., curry over rice): split into separate items (e.g., "cooked rice", "curry sauce", "chicken").
- Composite items (e.g., sandwiches, burgers): list main components (bun/bread, patty/meat, cheese, sauces, veggies).
- Sauces: include if visible or clearly implied (e.g., mayonnaise, ketchup, curry sauce). If quantity is small but present, 5–20 g typical.
- Bones/inedible shells: exclude their weight.
- Multiple plates in frame: choose the single most centered/consistently shown plate; note if others were ignored.

Confidence:
- 0–1, reflecting overall certainty after reconciling all angles (consider scale cues, occlusions, visibility, method).

"notes" field:
- Briefly explain the multi-angle cues that affected the estimate (e.g., "used spoon length for scale; 6 nuggets confirmed from side angle; curry gloss suggests ~18 g oil").
- If anything was excluded (extra plate, decoration), say so.

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
