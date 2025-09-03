import time

from ..services.gemini.gemini_healthscore import score_with_gemini
from ..state.health_score_state import HealthScoreState
from ..utils.timing import calculate_ms, print_node_summary

def score_health(state: HealthScoreState) -> HealthScoreState:
    """
    Node that calculates health score using Gemini LLM.
    
    Args:
        state: Current graph state containing validated input data
        
    Returns:
        Updated state with health score results
    """
    t0 = time.perf_counter()
    
    try:
        # Call Gemini for health scoring
        result = score_with_gemini(state["input"])
        state["result"] = result
        state["llm_error"] = None
        
        timing_ms = calculate_ms(t0)
        state["timings"]["score_ms"] = timing_ms
        
        # Print success summary with health score
        health_score = result.get("health_score", 0)
        print_node_summary("score", True, timing_ms, score=f"{health_score}/10")
        
    except Exception as e:
        # Handle LLM scoring errors
        state["result"] = None
        state["llm_error"] = str(e)
        state["error"] = f"scoring_failed: {str(e)}"
        
        timing_ms = calculate_ms(t0)
        state["timings"]["score_ms"] = timing_ms
        
        # Print error summary
        print_node_summary("score", False, timing_ms, error=str(e))
        
    return state
