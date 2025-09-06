import time
from typing import Dict, Any
from ..state.nutrition_analysis_state import NutritionAnalysisState

def validate_input(state: NutritionAnalysisState) -> NutritionAnalysisState:
    """
    Validate input data for nutrition analysis.
    
    Args:
        state: Current state containing input data
        
    Returns:
        Updated state with validation results
    """
    t0 = time.perf_counter()
    
    try:
        # Validate required fields
        if "hint" not in state or not state["hint"]:
            raise ValueError("hint is required (e.g., 'karaage curry bento')")
        
        if not isinstance(state["hint"], str):
            raise ValueError("hint must be a string")
        
        if len(state["hint"].strip()) == 0:
            raise ValueError("hint cannot be empty")
        
        # Validate context (optional)
        if "context" in state and not isinstance(state["context"], dict):
            raise ValueError("context must be a dictionary")
        
        # Mark validation as passed
        state["validation_passed"] = True
        state["validation_error"] = None
        
    except Exception as e:
        state["validation_passed"] = False
        state["validation_error"] = str(e)
        state["error"] = f"Input validation failed: {str(e)}"
    
    # Record timing
    state["timings"]["validation"] = round((time.perf_counter() - t0) * 1000.0, 2)
    
    return state
