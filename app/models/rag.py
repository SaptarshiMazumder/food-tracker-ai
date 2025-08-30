from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class DishHit:
    """Model for RAG dish hit"""
    dish_name: str
    ingredients: List[str]
    cooking_method: str
    cuisine: str
    image_url: str
    source_datasets: List[str]
    cluster_id: str
    score: float
    directions: List[str]

@dataclass
class RAGQueryRequest:
    """RAG query request model"""
    ingredients: List[str]
    top: int = 5
    mode: str = "flexible"  # "flexible" or "strict"

@dataclass
class RAGQueryResponse:
    """RAG query response model"""
    query_ingredients: List[str]
    hits: List[DishHit]
    sources: Dict[str, List[Dict[str, Any]]]

@dataclass
class RecipeDetailsRequest:
    """Recipe details request model"""
    dish_name: str
    ingredients: List[str]

@dataclass
class RecipeDetailsResponse:
    """Recipe details response model"""
    dish_name: str
    ingredients: List[str]
    sources: List[Dict[str, Any]]
