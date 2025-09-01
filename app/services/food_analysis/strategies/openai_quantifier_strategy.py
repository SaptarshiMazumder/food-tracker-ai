# openai_quantifier_strategy.py
"""
OpenAI implementation of the IngredientQuantifierStrategy.
"""

from typing import Dict, List, Optional
import os
from .ingredient_quantifier_strategy import IngredientQuantifierStrategy


class OpenAIQuantifierStrategy(IngredientQuantifierStrategy):
    """
    OpenAI-based ingredient quantification strategy.
    """
    
    def quantify_ingredients(self, 
                           project: Optional[str], 
                           location: str, 
                           model: str,
                           image_paths: List[str], 
                           dish_hint: str = "", 
                           ing_hint: Optional[List[str]] = None) -> Dict:
        """
        Quantify ingredients using OpenAI model.
        """
        from ...openai.openai_ingredients import ingredients_from_image
        
        # Use OpenAI model from environment variable if not specified
        if not model or model.startswith("gemini"):
            model = os.getenv("DEFAULT_OPENAI_MODEL", "gpt-4o")
        
        return ingredients_from_image(
            project=project,
            location=location,  # Not used by OpenAI but kept for compatibility
            model=model,
            image_paths=image_paths,
            dish_hint=dish_hint,
            ing_hint=ing_hint
        )
