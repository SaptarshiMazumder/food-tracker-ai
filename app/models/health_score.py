# app/models/health_score.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict

class ItemGram(BaseModel):
    name: str
    grams: float

class HealthScoreInput(BaseModel):
    total_kcal: float
    total_grams: float
    total_fat_g: float
    total_protein_g: float
    items_grams: List[ItemGram] = Field(..., min_length=1)
    kcal_confidence: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    use_confidence_dampen: Optional[bool] = False

class ComponentScores(BaseModel):
    energy_density: float
    protein_density: float
    fat_balance: float
    carb_quality: float
    sodium_proxy: float
    whole_foods: float

class HealthScoreOutput(BaseModel):
    health_score: float = Field(..., ge=1.0, le=10.0)
    component_scores: ComponentScores
    weights: Dict[str, float]
    drivers_positive: List[str] = []
    drivers_negative: List[str] = []
    debug: Dict[str, float] = {}
    classification: List[Dict[str, str]] = []  # [{name, category}] – LLM-labeled categories
