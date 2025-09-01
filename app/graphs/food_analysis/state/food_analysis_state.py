from typing import TypedDict, Optional, Dict, Any, List

class FoodAnalysisState(TypedDict):
    """State for the food analysis graph workflow."""
    
    # Input parameters
    image_paths: List[str]
    project: Optional[str]
    location: str
    model: str

    # Recognition results
    dish: str
    ingredients: List[str]
    gemini_conf: float

    # Ingredient quantification results
    items: List[Dict[str, Any]]  # [{name, grams, note?}]
    total_grams: Optional[float]
    ing_conf: Optional[float]
    ing_notes: Optional[str]

    # Nutritional analysis results
    nutr_items: List[Dict[str, Any]]   # [{name,kcal,protein_g,carbs_g,fat_g,method?}]
    total_kcal: Optional[float]
    total_protein_g: Optional[float]
    total_carbs_g: Optional[float]
    total_fat_g: Optional[float]
    kcal_conf: Optional[float]
    kcal_notes: Optional[str]

    # Performance tracking
    timings: Dict[str, float]   # per-node ms
    total_ms: Optional[float]   # total workflow ms

    # Debug and error handling
    debug: Dict[str, Any]
    error: Optional[str]
