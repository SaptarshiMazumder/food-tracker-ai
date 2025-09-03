import time
from typing import Dict, Any
from ..state.nutrition_analysis_state import NutritionAnalysisState

def validate_output(state: NutritionAnalysisState) -> NutritionAnalysisState:
    """
    Perform final output validation and error handling.
    
    Args:
        state: Current state containing processing results
        
    Returns:
        Updated state with final validation results
    """
    t0 = time.perf_counter()
    
    try:
        # Check if LLM processing was successful
        if state.get("llm_error"):
            raise Exception(f"LLM processing failed: {state['llm_error']}")
        
        if not state.get("result"):
            raise Exception("No result data available for validation")
        
        # Check if validation passed
        if not state.get("validation_passed"):
            raise Exception("Input validation failed")
        
        # Final validation checks
        result = state["result"]
        
        # Debug: Log confidence values for troubleshooting
        state["debug"]["confidence_values"] = {
            "dish_confidence": result.get("dish_confidence"),
            "grams_confidence": result.get("grams_confidence"), 
            "kcal_confidence": result.get("kcal_confidence")
        }
        
        # Ensure all required fields are present and valid
        _validate_final_output(result)
        
        # Mark as successful
        state["error"] = None
        
    except Exception as e:
        state["error"] = str(e)
        
        # Add debug context for validation errors
        if "result" in locals():
            state["debug"]["validation_error_context"] = {
                "error_type": type(e).__name__,
                "error_msg": str(e),
                "result_keys": list(result.keys()) if isinstance(result, dict) else "Not a dict",
                "confidence_values": {
                    "dish_confidence": result.get("dish_confidence") if isinstance(result, dict) else None,
                    "grams_confidence": result.get("grams_confidence") if isinstance(result, dict) else None,
                    "kcal_confidence": result.get("kcal_confidence") if isinstance(result, dict) else None
                } if isinstance(result, dict) else None
            }
    
    # Record timing
    state["timings"]["output_validation"] = round((time.perf_counter() - t0) * 1000.0, 2)
    
    return state

def _validate_final_output(result: Dict[str, Any]) -> None:
    """
    Perform final validation on the output data.
    
    Args:
        result: Final result to validate
        
    Raises:
        ValueError: If final validation fails
    """
    # Check that numeric values are reasonable
    if result.get("total_kcal", 0) <= 0:
        raise ValueError("total_kcal must be positive")
    
    if result.get("total_grams", 0) <= 0:
        raise ValueError("total_grams must be positive")
    
    # Check confidence scores are within valid range according to schema
    confidence_ranges = {
        "dish_confidence": (0, 1),      # 0..1
        "grams_confidence": (1, 5),     # 1..5 (integer-ish scale)
        "kcal_confidence": (0, 1)       # 0..1
    }
    
    for field, (min_val, max_val) in confidence_ranges.items():
        if field in result:
            confidence = result[field]
            
            # Handle string representations of numbers
            if isinstance(confidence, str):
                try:
                    confidence = float(confidence)
                except ValueError:
                    raise ValueError(f"{field} must be a valid number, got: '{confidence}'")
            
            if not isinstance(confidence, (int, float)):
                raise ValueError(f"{field} must be a number, got: {type(confidence).__name__} with value: {confidence}")
            
            if confidence < min_val or confidence > max_val:
                if field == "grams_confidence":
                    raise ValueError(f"{field} must be a number between {min_val} and {max_val} (1=low, 5=high), got: {confidence}")
                else:
                    raise ValueError(f"{field} must be a number between {min_val} and {max_val}, got: {confidence}")
    
    # Check that lists are not empty
    list_fields = ["items_grams", "items_kcal", "items_nutrition"]
    for field in list_fields:
        if field in result and not isinstance(result[field], list):
            raise ValueError(f"{field} must be a list")
        if field in result and len(result[field]) == 0:
            raise ValueError(f"{field} cannot be empty")
