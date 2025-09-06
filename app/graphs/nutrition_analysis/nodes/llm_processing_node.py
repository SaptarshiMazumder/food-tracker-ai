import time
from typing import Dict, Any
from ..services.gemini.gemini_nutrition import llm_nutrition_breakdown
from ..state.nutrition_analysis_state import NutritionAnalysisState

def process_nutrition_breakdown(state: NutritionAnalysisState) -> NutritionAnalysisState:
    """
    Process nutrition breakdown using LLM.
    
    Args:
        state: Current state containing validated input data
        
    Returns:
        Updated state with LLM processing results
    """
    t0 = time.perf_counter()
    
    try:
        # Check if validation passed
        if not state.get("validation_passed"):
            raise Exception("Input validation failed, cannot proceed with LLM processing")
        
        # Prepare input for LLM service
        input_data = {
            "hint": state["hint"],
            "context": state.get("context", {})
        }
        
        # Call LLM service
        result = llm_nutrition_breakdown(input_data)
        
        # Store result
        state["result"] = result
        state["llm_error"] = None
        
        # Debug: Log the structure for troubleshooting
        state["debug"]["llm_result_keys"] = list(result.keys()) if isinstance(result, dict) else "Not a dict"
        if isinstance(result, dict) and "items_nutrition" in result:
            state["debug"]["items_nutrition_count"] = len(result["items_nutrition"])
            if result["items_nutrition"]:
                state["debug"]["first_item_keys"] = list(result["items_nutrition"][0].keys())
                state["debug"]["first_item_data"] = result["items_nutrition"][0]
        
        # Log a sample of the LLM response for debugging
        if isinstance(result, dict):
            state["debug"]["sample_response"] = {
                "total_keys": len(result),
                "has_items_nutrition": "items_nutrition" in result,
                "has_items_kcal": "items_kcal" in result,
                "has_items_grams": "items_grams" in result,
                "items_nutrition_sample": result.get("items_nutrition", [])[:2] if result.get("items_nutrition") else None
            }
        
        # Normalize field names to handle common variations
        result = _normalize_field_names(result)
        
        # Validate output structure
        _validate_output_structure(result)
        
    except Exception as e:
        state["llm_error"] = str(e)
        state["error"] = f"LLM processing failed: {str(e)}"
        state["result"] = None
        
        # Add debug info to help troubleshoot
        if "result" in locals():
            state["debug"]["error_context"] = {
                "result_type": type(result).__name__,
                "result_keys": list(result.keys()) if isinstance(result, dict) else "Not a dict",
                "error_type": type(e).__name__,
                "error_msg": str(e)
            }
    
    # Record timing
    state["timings"]["llm_processing"] = round((time.perf_counter() - t0) * 1000.0, 2)
    
    return state

def _normalize_field_names(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize field names to handle common variations from the LLM.
    
    Args:
        result: LLM result to normalize
        
    Returns:
        Normalized result with consistent field names
    """
    # Field name mappings for common variations
    field_mappings = {
        "protein": "protein_g",
        "proteinG": "protein_g", 
        "proteinGrams": "protein_g",
        "protein_grams": "protein_g",
        "carbs": "carbs_g",
        "carbsG": "carbs_g",
        "carbohydrates": "carbs_g",
        "carbohydrates_g": "carbs_g",
        "fat": "fat_g",
        "fatG": "fat_g",
        "fats": "fat_g",
        "fats_g": "fat_g",
        "calories": "kcal",
        "cal": "kcal",
        "energy": "kcal",
        "energy_kcal": "kcal"
    }
    
    # Normalize items_nutrition
    if "items_nutrition" in result and isinstance(result["items_nutrition"], list):
        for item in result["items_nutrition"]:
            if isinstance(item, dict):
                for old_name, new_name in field_mappings.items():
                    if old_name in item:
                        item[new_name] = item.pop(old_name)
    
    # Normalize items_kcal
    if "items_kcal" in result and isinstance(result["items_kcal"], list):
        for item in result["items_kcal"]:
            if isinstance(item, dict):
                for old_name, new_name in field_mappings.items():
                    if old_name in item:
                        item[new_name] = item.pop(old_name)
    
    return result

def _validate_output_structure(result: Dict[str, Any]) -> None:
    """
    Validate the structure of LLM output.
    
    Args:
        result: LLM output to validate
        
    Raises:
        ValueError: If output structure is invalid
    """
    # Check required top-level keys
    required_keys = [
        "angles_used", "dish", "dish_confidence", "grams_confidence", "ingredients_detected",
        "items_density", "items_grams", "items_kcal", "items_nutrition", "kcal_confidence",
        "notes", "timings", "total_carbs_g", "total_fat_g", "total_grams",
        "total_kcal", "total_ms", "total_protein_g"
    ]
    
    missing_keys = [key for key in required_keys if key not in result]
    if missing_keys:
        raise ValueError(f"Nutrition schema missing keys: {missing_keys}")
    
    # Validate numeric totals match item sums (with tolerance for rounding)
    _validate_nutrition_totals(result)

def _validate_nutrition_totals(result: Dict[str, Any]) -> None:
    """
    Validate that nutrition totals match the sum of individual items.
    
    Args:
        result: LLM output to validate
        
    Raises:
        ValueError: If totals don't match item sums
    """
    def close(a: float, b: float, tolerance: float = 2.0) -> bool:
        """Check if two numbers are close within tolerance"""
        return abs(a - b) <= tolerance
    
    # Validate that required arrays exist and have items
    if not result.get("items_nutrition") or not isinstance(result["items_nutrition"], list):
        raise ValueError("items_nutrition must be a non-empty list")
    
    if not result.get("items_kcal") or not isinstance(result["items_kcal"], list):
        raise ValueError("items_kcal must be a non-empty list")
    
    if not result.get("items_grams") or not isinstance(result["items_grams"], list):
        raise ValueError("items_grams must be a non-empty list")
    
    # Validate individual item structures
    for i, item in enumerate(result["items_nutrition"]):
        required_fields = ["carbs_g", "fat_g", "protein_g", "kcal", "name"]
        missing_fields = [field for field in required_fields if field not in item]
        if missing_fields:
            # Try to find similar field names (case-insensitive)
            available_fields = list(item.keys())
            suggestions = []
            for field in missing_fields:
                for available in available_fields:
                    if field.lower() in available.lower() or available.lower() in field.lower():
                        suggestions.append(f"'{field}' might be '{available}'")
            
            # Check for common field name variations
            field_variations = {
                "protein_g": ["protein", "protein_g", "proteinG", "proteinGrams", "protein_grams"],
                "carbs_g": ["carbs", "carbs_g", "carbsG", "carbohydrates", "carbohydrates_g"],
                "fat_g": ["fat", "fat_g", "fatG", "fats", "fats_g"],
                "kcal": ["calories", "cal", "energy", "energy_kcal"]
            }
            
            for missing_field in missing_fields:
                if missing_field in field_variations:
                    for variation in field_variations[missing_field]:
                        if variation in available_fields:
                            suggestions.append(f"'{missing_field}' found as '{variation}'")
            
            error_msg = f"items_nutrition[{i}] missing fields: {missing_fields}"
            if suggestions:
                error_msg += f". Suggestions: {', '.join(suggestions)}"
            
            # Add the actual item data for debugging
            error_msg += f". Item data: {item}"
            raise ValueError(error_msg)
    
    for i, item in enumerate(result["items_kcal"]):
        required_fields = ["kcal", "name"]
        missing_fields = [field for field in required_fields if field not in item]
        if missing_fields:
            raise ValueError(f"items_kcal[{i}] missing fields: {missing_fields}")
    
    for i, item in enumerate(result["items_grams"]):
        required_fields = ["grams", "name"]
        missing_fields = [field for field in required_fields if field not in item]
        if missing_fields:
            raise ValueError(f"items_grams[{i}] missing fields: {missing_fields}")
    
    # Calculate totals from items
    calculated_totals = {
        "kcal": sum(item["kcal"] for item in result["items_kcal"]),
        "carbs_g": sum(item["carbs_g"] for item in result["items_nutrition"]),
        "fat_g": sum(item["fat_g"] for item in result["items_nutrition"]),
        "protein_g": sum(item["protein_g"] for item in result["items_nutrition"]),
        "grams": sum(item["grams"] for item in result["items_grams"]),
    }
    
    # Compare with reported totals
    if not close(result["total_kcal"], calculated_totals["kcal"]):
        raise ValueError(f"total_kcal mismatch: reported {result['total_kcal']}, calculated {calculated_totals['kcal']}")
    
    if not close(result["total_carbs_g"], calculated_totals["carbs_g"]):
        raise ValueError(f"total_carbs_g mismatch: reported {result['total_carbs_g']}, calculated {calculated_totals['carbs_g']}")
    
    if not close(result["total_fat_g"], calculated_totals["fat_g"]):
        raise ValueError(f"total_fat_g mismatch: reported {result['total_fat_g']}, calculated {calculated_totals['fat_g']}")
    
    if not close(result["total_protein_g"], calculated_totals["protein_g"]):
        raise ValueError(f"total_protein_g mismatch: reported {result['total_protein_g']}, calculated {calculated_totals['protein_g']}")
    
    if not close(result["total_grams"], calculated_totals["grams"], tolerance=5.0):
        raise ValueError(f"total_grams mismatch: reported {result['total_grams']}, calculated {calculated_totals['grams']}")
