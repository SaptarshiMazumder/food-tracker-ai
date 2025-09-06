# recognize_prompt.py
"""
Centralized prompt for dish recognition (Japan-context aware).
Used by both Gemini and OpenAI implementations.
"""

UTENSIL_SCALE = (
    "If a standard fork, spoon, or chopsticks are visible, use them as scale references:\n"
    "- Assume dinner fork length = 19 cm; head width ≈ 2.7 cm.\n"
    "- Assume tablespoon length = 19 cm; bowl width ≈ 3.8 cm.\n"
    "- Assume chopsticks length = 24 cm.\n"
    "Prefer utensil/chopstick scaling over guesswork when plate/bento depth is unclear.\n"
    "If multiple angles are provided, reconcile them and infer a single best description.\n"
)

JAPAN_CONTEXT = (
    "Context: The food is from JAPAN. Interpret appearance, packaging, and plating with Japanese norms.\n"
    "- Dishes & naming: Favor Japanese styles/variants (e.g., 'karaage', 'tonkatsu', 'gyudon', 'omurice', 'okonomiyaki', "
    "'yakisoba', 'curry rice', 'ramen', 'udon', 'soba', 'onigiri', 'katsu sando', 'hamburg steak').\n"
    "- Containers: Common are bento boxes (multi-compartment), donburi bowls, ramen bowls, curry plates with dams, "
    "plastic convenience-store trays, onigiri wrappers.\n"
    "- Oils/fats: Neutral salad oil/canola/soybean common; deep-fry absorption typical for karaage/tempura/tonkatsu; "
    "sesame oil often in stir-fries; Kewpie mayo appears on okonomiyaki, takoyaki, sandwiches, salads.\n"
    "- Sauces/seasonings: Tonkatsu sauce, chuno sauce, tare, shoyu, mirin, miso, dashi, katsuobushi, beni shoga, "
    "karashi, ponzu, yuzu kosho, furikake, curry roux (Japanese style), bulldog-style sauces.\n"
    "- Rice & noodles: Short-grain Japanese rice is default; noodles include ramen (alkaline), udon (thick wheat), "
    "soba (buckwheat), yakisoba (wheat, sauce-fried).\n"
    "- Chain cues: If branding/packaging suggests a big chain, prefer JP variants (e.g., MOS Burger rice burgers/teriyaki, "
    "McD JP teriyaki/tatsuta styles, Matsuya/Sukiya/Yoshinoya = gyudon sets, Coco Ichibanya = Japanese curry toppings). "
    "If unclear, do not hallucinate brand—stick to generic Japanese style.\n"
    "- Convenience stores: Onigiri (tuna-mayo, salmon, kombu), karaage-kun/nuggets, spaghetti napolitan bento, "
    "katsu curry, shogayaki, nikujaga, tamagoyaki.\n"
    "Apply these norms when deciding ingredients (e.g., curry uses Japanese curry roux, not Indian whole spices; "
    "yakisoba uses yakisoba sauce, cabbage, pork bits; omurice uses ketchup rice + omelet).\n"
)

def build_recognize_prompt() -> str:
    """
    Build the complete dish recognition prompt (Japan-context aware).
    
    Returns:
        Complete prompt string
    """
    prompt = (
        "You are a precise food recognizer. Return STRICT JSON ONLY:\n"
        "{"
        "\"dish\":\"<short canonical dish>\","
        "\"ingredients\":[\"<3-12 likely ingredients, lowercase; include typical cooking fats/oils if implied (e.g., sesame oil for fried rice, neutral salad oil for stir-fry, kewpie mayo for okonomiyaki)>\"],"
        "\"container\":\"plate|bowl|tray|bento|cup|none\","
        "\"confidence\":<0..1>"
        "}\n\n"
        + JAPAN_CONTEXT
        + "\n"
        + UTENSIL_SCALE
        + (
            "Multi-angle reconciliation:\n"
            "- Use all angles to resolve occlusions and confirm piece counts.\n"
            "- Prefer angles with clear scale references (utensils/chopsticks, plate edges) when estimates conflict.\n"
            "- Produce ONE consolidated description consistent with all angles.\n"
        )
    )
    return prompt


