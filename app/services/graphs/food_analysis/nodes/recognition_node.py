import time
from typing import List, Optional

from ....gemini.gemini_recognize import gemini_recognize_dish
from ..state.food_analysis_state import FoodAnalysisState
from ..utils.timing import calculate_ms, print_node_summary

def recognize_dish(state: FoodAnalysisState) -> FoodAnalysisState:
    """
    Node that recognizes dishes and ingredients from food images using Gemini Vision.
    
    Args:
        state: Current graph state containing image paths and configuration
        
    Returns:
        Updated state with dish name, ingredients list, and confidence score
    """
    t0 = time.perf_counter()
    
    # Call Gemini Vision API for dish recognition
    data = gemini_recognize_dish(
        state["project"], 
        state["location"], 
        state["model"], 
        state["image_paths"]
    )
    
    timing_ms = calculate_ms(t0)
    state["timings"]["recognize_ms"] = timing_ms

    # Handle errors
    if "error" in data:
        state["error"] = f"recognition_failed: {data.get('error')}"
        state["debug"]["rec_raw"] = data.get("raw")
        print_node_summary("recognize", False, timing_ms)
        return state

    # Update state with recognition results
    state["dish"] = data.get("dish", "")
    state["ingredients"] = [str(x) for x in (data.get("ingredients") or [])]
    state["gemini_conf"] = float(data.get("confidence", 0.0))

    # Print compact summary
    ing_preview = ", ".join(state["ingredients"][:6])
    ellipsis = "…" if len(state["ingredients"]) > 6 else ""
    
    print_node_summary(
        "recognize", 
        True, 
        timing_ms,
        dish=f"'{state['dish']}'",
        conf=f"{state['gemini_conf']:.2f}",
        ingredients=f"[{ing_preview}{ellipsis}]"
    )
    
    return state
