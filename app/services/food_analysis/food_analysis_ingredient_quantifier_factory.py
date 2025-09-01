# food_analysis_ingredient_quantifier_factory.py
"""
Factory for creating ingredient quantifier strategy instances.
"""

import os
from typing import Optional
from .strategies.ingredient_quantifier_strategy import IngredientQuantifierStrategy


class FoodAnalysisIngredientQuantifierFactory:
    """
    Factory for creating ingredient quantifier strategy instances based on provider configuration.
    """
    
    @staticmethod
    def create_quantifier(provider: str = None) -> IngredientQuantifierStrategy:
        """
        Create an ingredient quantifier strategy instance for the specified provider.
        
        Args:
            provider: Provider name ("gemini", "openai", etc.). 
                     If None, reads from INGREDIENTS_PROVIDER environment variable.
        
        Returns:
            IngredientQuantifierStrategy instance for the specified provider
            
        Raises:
            ValueError: If provider is not supported
        """
        if provider is None:
            provider = os.getenv("INGREDIENTS_PROVIDER", "gemini").lower()
        
        if provider == "gemini":
            from .strategies.gemini_quantifier_strategy import GeminiQuantifierStrategy
            return GeminiQuantifierStrategy()
        elif provider == "openai":
            from .strategies.openai_quantifier_strategy import OpenAIQuantifierStrategy
            return OpenAIQuantifierStrategy()
        else:
            raise ValueError(f"Unsupported provider: {provider}")
