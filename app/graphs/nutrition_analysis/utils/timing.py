from typing import Dict, Any

def print_pipeline_summary(timings: Dict[str, float], total_ms: float = None) -> None:
    """
    Print a summary of the nutrition analysis pipeline timings.
    
    Args:
        timings: Dictionary of timing data for each step
        total_ms: Total execution time in milliseconds
    """
    print("\n" + "="*50)
    print("NUTRITION ANALYSIS PIPELINE SUMMARY")
    print("="*50)
    
    # Print individual step timings
    for step, time_ms in timings.items():
        step_name = step.replace("_", " ").title()
        print(f"{step_name:20}: {time_ms:8.2f} ms")
    
    # Print total time if provided
    if total_ms is not None:
        print("-" * 50)
        print(f"{'Total Time':20}: {total_ms:8.2f} ms")
    
    print("="*50)
