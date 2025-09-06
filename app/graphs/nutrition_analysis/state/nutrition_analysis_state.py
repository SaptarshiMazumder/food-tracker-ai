from typing import Dict, Any, List, Optional, TypedDict

class NutritionAnalysisState(TypedDict):
    """State for nutrition analysis workflow"""
    
    # Input data
    hint: str
    context: Dict[str, Any]
    
    # Validation results
    validation_passed: Optional[bool]
    validation_error: Optional[str]
    
    # LLM processing results
    result: Optional[Dict[str, Any]]
    llm_error: Optional[str]
    
    # Performance tracking
    timings: Dict[str, float]
    total_ms: Optional[float]
    
    # Debug and error handling
    debug: Dict[str, Any]
    error: Optional[str]
