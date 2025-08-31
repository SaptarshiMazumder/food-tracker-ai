from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class AnalyzeItemGrams:
    """Model for ingredient grams data"""
    name: str
    grams: float
    note: Optional[str] = None

@dataclass
class AnalyzeItemKcal:
    """Model for ingredient calories data"""
    name: str
    kcal: float
    method: Optional[str] = None

@dataclass
class AnalyzeNutritionItem:
    """Model for nutrition data"""
    name: str
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    method: Optional[str] = None

@dataclass
class AnalyzeItemDensity:
    """Model for ingredient density data"""
    name: str
    kcal_per_g: float
    protein_per_g: float
    carbs_per_g: float
    fat_per_g: float

@dataclass
class AnalysisResponse:
    """Complete analysis response model"""
    # Recognition
    dish: str
    dish_confidence: float
    ingredients_detected: List[str]
    
    # Grams estimation
    items_grams: List[AnalyzeItemGrams]
    total_grams: float
    grams_confidence: float
    
    # Nutrition
    items_nutrition: List[AnalyzeNutritionItem]
    items_kcal: List[AnalyzeItemKcal]
    items_density: List[AnalyzeItemDensity]
    total_kcal: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    kcal_confidence: float
    
    # Misc
    notes: Optional[str] = None
    overlay_url: Optional[str] = None
    image_url: Optional[str] = None
    total_ms: Optional[float] = None
    angles_used: Optional[int] = None
    timings: Optional[Dict[str, float]] = None

@dataclass
class AnalysisRequest:
    """Analysis request model"""
    model: str = "gemini-2.5-pro"
    enable_ab_test: bool = False
    enable_fallback: bool = False

