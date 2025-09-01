import time
from typing import Dict, Any

from langgraph.graph import StateGraph, END

from .state.health_score_state import HealthScoreState
from .nodes.validation_node import validate_input
from .nodes.scoring_node import score_health
from .nodes.output_validation_node import validate_output
from .utils.timing import print_pipeline_summary

def build_health_score_graph():
    """
    Build the health score graph with three main nodes:
    1. validate_input - Validates input data using Pydantic models
    2. score_health - Calculates health score using Gemini LLM
    3. validate_output - Validates output data using Pydantic models
    
    Returns:
        Compiled LangGraph workflow
    """
    # Create the state graph
    workflow = StateGraph(HealthScoreState)
    
    # Add nodes
    workflow.add_node("validate", validate_input)
    workflow.add_node("score", score_health)
    workflow.add_node("output_validate", validate_output)
    
    # Define the workflow
    workflow.set_entry_point("validate")
    workflow.add_edge("validate", "score")
    workflow.add_edge("score", "output_validate")
    workflow.add_edge("output_validate", END)
    
    return workflow.compile()

def run_health_score(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the health score workflow with the given payload.
    
    Args:
        payload: Health score input data
        
    Returns:
        Health score result data
    """
    t0 = time.perf_counter()
    
    # Initialize state
    initial_state = {
        "input": payload,
        "validation_passed": None,
        "validation_error": None,
        "result": None,
        "llm_error": None,
        "timings": {},
        "total_ms": None,
        "debug": {},
        "error": None
    }
    
    # Run the graph
    graph = build_health_score_graph()
    final_state = graph.invoke(initial_state)
    
    # Calculate total time
    total_ms = (time.perf_counter() - t0) * 1000
    final_state["total_ms"] = total_ms
    
    # Print pipeline summary
    print_pipeline_summary(final_state)
    
    # Return result or raise error
    if final_state.get("error"):
        raise Exception(final_state["error"])
    
    return final_state["result"]
