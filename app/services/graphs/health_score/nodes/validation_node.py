import time
from pydantic import ValidationError

from app.models.health_score import HealthScoreInput
from ..state.health_score_state import HealthScoreState
from ..utils.timing import calculate_ms, print_node_summary

def validate_input(state: HealthScoreState) -> HealthScoreState:
    """
    Node that validates the health score input data.
    
    Args:
        state: Current graph state containing input data
        
    Returns:
        Updated state with validation results
    """
    t0 = time.perf_counter()
    
    try:
        # Validate input using Pydantic model
        HealthScoreInput(**state["input"])
        state["validation_passed"] = True
        state["validation_error"] = None
        
        timing_ms = calculate_ms(t0)
        state["timings"]["validate_ms"] = timing_ms
        
        # Print success summary
        print_node_summary("validate", True, timing_ms)
        
    except ValidationError as e:
        # Handle validation errors
        state["validation_passed"] = False
        state["validation_error"] = str(e)
        state["error"] = f"validation_failed: {str(e)}"
        
        timing_ms = calculate_ms(t0)
        state["timings"]["validate_ms"] = timing_ms
        
        # Print error summary
        print_node_summary("validate", False, timing_ms, error=str(e))
        
    return state
