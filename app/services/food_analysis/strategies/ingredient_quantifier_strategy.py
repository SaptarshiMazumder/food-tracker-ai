# ingredient_quantifier_strategy.py
"""
Strategy interface for ingredient quantification.
Defines the contract that all ingredient quantification strategies must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class IngredientQuantifierStrategy(ABC):
    """
    Strategy interface for ingredient quantification.
    Each provider (Gemini, OpenAI, etc.) implements this interface.
    """
    
    @abstractmethod
    def quantify_ingredients(self, 
                           project: Optional[str], 
                           location: str, 
                           model: str,
                           image_paths: List[str], 
                           dish_hint: str = "", 
                           ing_hint: Optional[List[str]] = None) -> Dict:
        """
        Quantify ingredients from images using the specific provider's implementation.
        
        Args:
            project: Provider-specific project identifier (e.g., Google Cloud project)
            location: Provider-specific location (e.g., Google Cloud location)
            model: Model name to use for quantification
            image_paths: List of image file paths to analyze
            dish_hint: Optional dish name hint for context
            ing_hint: Optional list of ingredient hints
            
        Returns:
            Dict with ingredients analysis results:
            {
                "items": [{"name": str, "grams": float, "note": str}],
                "total_grams": float,
                "confidence": float,
                "notes": str
            }
            or {"error": str, "raw": str} on failure
        """
        pass
