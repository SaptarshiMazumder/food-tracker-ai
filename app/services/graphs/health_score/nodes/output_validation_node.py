import time
from pydantic import ValidationError

from app.models.health_score import HealthScoreOutput
from ..state.health_score_state import HealthScoreState
from ..utils.timing import calculate_ms, print_node_summary

def validate_output(state: HealthScoreState) -> HealthScoreState:
    """
    Node that validates the health score output data.
    
    Args:
        state: Current graph state containing LLM results
        
    Returns:
        Updated state with output validation results
    """
    t0 = time.perf_counter()
    
    try:
        # Validate output using Pydantic model
        HealthScoreOutput(**state["result"])
        
        timing_ms = calculate_ms(t0)
        state["timings"]["output_validate_ms"] = timing_ms
        
        # Print success summary
        print_node_summary("output_validate", True, timing_ms)
        
    except ValidationError as e:
        # Handle validation errors
        state["error"] = f"output_validation_failed: {str(e)}"
        
        timing_ms = calculate_ms(t0)
        state["timings"]["output_validate_ms"] = timing_ms
        
        # Print error summary
        print_node_summary("output_validate", False, timing_ms, error=str(e))
        
    return state
