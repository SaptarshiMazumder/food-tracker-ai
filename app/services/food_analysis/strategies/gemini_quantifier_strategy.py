# gemini_quantifier_strategy.py
"""
Gemini implementation of the IngredientQuantifierStrategy.
"""

from typing import Dict, List, Optional
from .ingredient_quantifier_strategy import IngredientQuantifierStrategy


class GeminiQuantifierStrategy(IngredientQuantifierStrategy):
    """
    Gemini-based ingredient quantification strategy.
    """
    
    def quantify_ingredients(self, 
                           project: Optional[str], 
                           location: str, 
                           model: str,
                           image_paths: List[str], 
                           dish_hint: str = "", 
                           ing_hint: Optional[List[str]] = None) -> Dict:
        """
        Quantify ingredients using Gemini model.
        """
        from ...gemini.gemini_ingredients import ingredients_from_image
        
        return ingredients_from_image(
            project=project,
            location=location,
            model=model,
            image_paths=image_paths,
            dish_hint=dish_hint,
            ing_hint=ing_hint
        )
