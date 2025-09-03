import time
from typing import Dict, Any

from langgraph.graph import StateGraph, END

from .state.nutrition_analysis_state import NutritionAnalysisState
from .nodes.validation_node import validate_input
from .nodes.llm_processing_node import process_nutrition_breakdown
from .nodes.output_validation_node import validate_output
from .utils.timing import print_pipeline_summary

def build_nutrition_analysis_graph():
    """
    Build the nutrition analysis graph with three main nodes:
    1. validate_input - Validates input data
    2. process_nutrition_breakdown - Processes nutrition breakdown using LLM
    3. validate_output - Performs final output validation
    
    Returns:
        Compiled LangGraph workflow
    """
    # Create the state graph
    workflow = StateGraph(NutritionAnalysisState)
    
    # Add nodes
    workflow.add_node("validate", validate_input)
    workflow.add_node("process", process_nutrition_breakdown)
    workflow.add_node("output_validate", validate_output)
    
    # Define the workflow
    workflow.set_entry_point("validate")
    workflow.add_edge("validate", "process")
    workflow.add_edge("process", "output_validate")
    workflow.add_edge("output_validate", END)
    
    return workflow.compile()

def run_nutrition_analysis(hint: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Run the nutrition analysis workflow with the given hint.
    
    Args:
        hint: Food description hint (e.g., 'karaage curry bento')
        context: Optional context data
        
    Returns:
        Nutrition analysis result data
        
    Raises:
        Exception: If the workflow fails
    """
    t0 = time.perf_counter()
    
    # Initialize state
    initial_state: NutritionAnalysisState = {
        "hint": hint,
        "context": context or {},
        "validation_passed": None,
        "validation_error": None,
        "result": None,
        "llm_error": None,
        "timings": {},
        "total_ms": None,
        "debug": {},
        "error": None
    }
    
    # Execute the workflow
    graph = build_nutrition_analysis_graph()
    final_state = graph.invoke(initial_state)
    
    # Calculate total time
    total_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    final_state["total_ms"] = total_ms
    
    # Print pipeline summary
    print_pipeline_summary(final_state["timings"], total_ms)
    
    # Check for errors
    if final_state.get("error"):
        # Include debug information in the error message if available
        error_msg = final_state["error"]
        if final_state.get("debug"):
            debug_info = final_state["debug"]
            if "error_context" in debug_info:
                context = debug_info["error_context"]
                error_msg += f" (Context: {context})"
            elif "llm_result_keys" in debug_info:
                error_msg += f" (Result keys: {debug_info['llm_result_keys']})"
        
        raise Exception(error_msg)
    
    # Return result
    return final_state["result"]
