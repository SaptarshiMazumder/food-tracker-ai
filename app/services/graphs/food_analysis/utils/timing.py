import time
from typing import Dict, Any

def calculate_ms(t0: float) -> float:
    """Calculate milliseconds elapsed since t0."""
    return round((time.perf_counter() - t0) * 1000.0, 2)

def print_node_summary(node_name: str, success: bool, timing_ms: float, **kwargs):
    """Print a standardized node execution summary."""
    status = "✅" if success else "❌"
    details = " ".join([f"{k}={v}" for k, v in kwargs.items()])
    print(f"[{node_name}] {status} {details} took {timing_ms} ms")

def print_pipeline_summary(timings: Dict[str, float], total_ms: float):
    """Print a summary of the entire pipeline execution."""
    timing_details = ", ".join([
        f"{node} {timings.get(node, '?')} ms" 
        for node in ["recognize", "ing_quant", "calories"]
    ])
    print(f"[pipeline] ⏱ total {total_ms} ms ({timing_details})")
