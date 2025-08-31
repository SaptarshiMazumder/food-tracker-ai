import time
from typing import Optional

def calculate_ms(start_time: float) -> float:
    """Calculate elapsed time in milliseconds."""
    return (time.perf_counter() - start_time) * 1000

def print_node_summary(
    node_name: str, 
    success: bool, 
    timing_ms: float,
    **kwargs
) -> None:
    """
    Print a compact summary of node execution.
    
    Args:
        node_name: Name of the executed node
        success: Whether the node executed successfully
        timing_ms: Execution time in milliseconds
        **kwargs: Additional key-value pairs to display
    """
    status = "✅" if success else "❌"
    timing_str = f"{timing_ms:.0f}ms"
    
    # Build additional info string
    extra_info = ""
    if kwargs:
        info_parts = [f"{k}={v}" for k, v in kwargs.items()]
        extra_info = f" | {' | '.join(info_parts)}"
    
    print(f"{status} {node_name} ({timing_str}){extra_info}")

def print_pipeline_summary(state: dict) -> None:
    """
    Print a summary of the entire pipeline execution.
    
    Args:
        state: The final state from the graph execution
    """
    timings = state.get("timings", {})
    total_ms = state.get("total_ms", 0)
    error = state.get("error")
    
    if error:
        print(f"❌ Pipeline failed: {error}")
        return
    
    print(f"\n📊 Health Score Pipeline Summary:")
    print(f"   Total time: {total_ms:.0f}ms")
    
    if timings:
        print("   Node breakdown:")
        for node, ms in timings.items():
            print(f"     {node}: {ms:.0f}ms")
    
    # Show health score if available
    result = state.get("result", {})
    if "health_score" in result:
        score = result["health_score"]
        print(f"   Health Score: {score}/10")
