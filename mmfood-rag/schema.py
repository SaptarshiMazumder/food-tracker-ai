from pydantic import BaseModel, Field
from typing import List, Dict

class DishHit(BaseModel):
    dish_name: str
    ingredients: List[str]
    cooking_method: str = ""
    cuisine: str = ""
    image_url: str = ""
    source_datasets: List[str] = Field(default_factory=list)
    cluster_id: str
    score: float
    directions: List[str] = Field(default_factory=list)  # Add directions field

class WebSource(BaseModel):
    title: str
    link: str
    snippet: str
    displayLink: str
    directions: List[str] = Field(default_factory=list)  # Add extracted directions
    content_preview: str = ""  # Add content preview

class QueryResult(BaseModel):
    query_ingredients: List[str]
    hits: List[DishHit]
    sources: Dict[str, List[WebSource]]  # key = dish_name