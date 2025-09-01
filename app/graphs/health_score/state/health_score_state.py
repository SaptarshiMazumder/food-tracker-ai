from typing import TypedDict, Optional, Dict, Any, List

class HealthScoreState(TypedDict):
    """State for the health score graph workflow."""
    
    # Input parameters
    input: Dict[str, Any]  # HealthScoreInput data
    
    # Validation results
    validation_passed: Optional[bool]
    validation_error: Optional[str]
    
    # LLM scoring results
    result: Optional[Dict[str, Any]]  # HealthScoreOutput data
    llm_error: Optional[str]
    
    # Performance tracking
    timings: Dict[str, float]   # per-node ms
    total_ms: Optional[float]   # total workflow ms
    
    # Debug and error handling
    debug: Dict[str, Any]
    error: Optional[str]
