import time
from typing import List, Optional

from ....services.food_analysis.food_analysis_ingredient_quantifier_factory import FoodAnalysisIngredientQuantifierFactory
from ..state.food_analysis_state import FoodAnalysisState
from ..utils.timing import calculate_ms, print_node_summary

def quantify_ingredients(state: FoodAnalysisState) -> FoodAnalysisState:
    """
    Node that quantifies ingredients from food images using configured provider (Gemini or OpenAI).
    
    Args:
        state: Current graph state containing image paths and recognition results
        
    Returns:
        Updated state with quantified ingredients, total grams, and confidence
    """
    t0 = time.perf_counter()

    # Use configured provider for ingredient detection and quantification
    quantifier = FoodAnalysisIngredientQuantifierFactory.create_quantifier()
    res = quantifier.quantify_ingredients(
        project=state["project"], 
        location=state["location"], 
        model=state["model"], 
        image_paths=state["image_paths"],
        dish_hint=state.get("dish", ""), 
        ing_hint=state.get("ingredients", [])
    )
    
    timing_ms = calculate_ms(t0)
    state["timings"]["ing_quant_ms"] = timing_ms

    # Handle errors
    if "error" in res:
        state["error"] = f"ingredients_failed: {res['error']}"
        state["debug"]["ingredients_raw"] = res.get("raw")
        # Get provider for logging from environment variable
        import os
        provider = os.getenv("INGREDIENTS_PROVIDER", "gemini").lower()
        print_node_summary(f"ing_quant({provider})", False, timing_ms)
        return state

    # Map results into state
    state["items"] = res.get("items", [])
    state["total_grams"] = float(res.get("total_grams") or 0.0)
    state["ing_conf"] = float(res.get("confidence") or 0.0) if res.get("confidence") is not None else None
    state["ing_notes"] = res.get("notes")

    # Optional: if LogMeal filled dish/ingredients, keep them (don't override Gemini's if present)
    if not state.get("dish"):
        state["dish"] = res.get("dish", "")
    if not state.get("ingredients"):
        state["ingredients"] = [str(x) for x in (res.get("ingredients") or [])]

    # Prepare summary details
    n_items = len(state["items"])
    oil = next((x for x in state["items"] if "oil" in (x.get("name", "")).lower()), None)
    oil_g = f"{oil.get('grams', 0)} g" if oil else "n/a"
    conf_str = f"{state['ing_conf']:.2f}" if state['ing_conf'] is not None else "n/a"
    
    # Get provider for logging from environment variable
    import os
    provider = os.getenv("INGREDIENTS_PROVIDER", "gemini").lower()
    
    print_node_summary(
        f"ing_quant({provider})", 
        True, 
        timing_ms,
        items=n_items,
        total_grams=f"{state['total_grams']:.0f} g",
        conf=conf_str,
        oil=oil_g
    )

    return state
