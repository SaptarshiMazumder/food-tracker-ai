import time
from typing import List, Optional

from ..services.gemini.gemini_calories import calories_from_ingredients
from ..state.food_analysis_state import FoodAnalysisState
from ..utils.timing import calculate_ms, print_node_summary

def calculate_calories(state: FoodAnalysisState) -> FoodAnalysisState:
    """
    Node that calculates nutritional information from quantified ingredients.
    
    Args:
        state: Current graph state containing quantified ingredients
        
    Returns:
        Updated state with nutritional breakdown and total calories
    """
    t0 = time.perf_counter()
    
    # Validate that we have ingredients to analyze
    if not state.get("items"):
        state["error"] = "No ingredient items."
        timing_ms = calculate_ms(t0)
        state["timings"]["calories_ms"] = timing_ms
        print_node_summary("calories", False, timing_ms, reason="no items")
        return state

    # Call Gemini for calorie calculation
    res = calories_from_ingredients(
        state["project"], 
        state["location"], 
        state["model"],
        state.get("dish", ""), 
        state["items"]
    )
    
    timing_ms = calculate_ms(t0)
    state["timings"]["calories_ms"] = timing_ms

    # Handle errors
    if "error" in res:
        state["error"] = f"calories_failed: {res['error']}"
        state["debug"]["calories_raw"] = res.get("raw")
        print_node_summary("calories", False, timing_ms)
        return state

    # Update state with nutritional results
    state["nutr_items"] = res.get("items", [])
    state["total_kcal"] = float(res.get("total_kcal", 0.0))
    state["total_protein_g"] = float(res.get("total_protein_g", 0.0))
    state["total_carbs_g"] = float(res.get("total_carbs_g", 0.0))
    state["total_fat_g"] = float(res.get("total_fat_g", 0.0))
    state["kcal_conf"] = float(res.get("confidence", 0.0))
    state["kcal_notes"] = res.get("notes")

    print_node_summary(
        "calories", 
        True, 
        timing_ms,
        total=f"{state['total_kcal']:.0f} kcal",
        protein=f"P={state['total_protein_g']:.1f}g",
        carbs=f"C={state['total_carbs_g']:.1f}g",
        fat=f"F={state['total_fat_g']:.1f}g",
        conf=f"{state['kcal_conf']:.2f}"
    )
    
    return state
