# food_analysis_ingredients.py
import os
from typing import Dict, List, Optional

def ingredients_from_image_wrapper(project: Optional[str], location: str, model: str,
                                  image_paths: List[str], dish_hint: str = "", 
                                  ing_hint: Optional[List[str]] = None) -> Dict:
    """
    Wrapper function that routes to either Gemini or OpenAI ingredients provider
    based on the INGREDIENTS_PROVIDER environment variable.
    
    Args:
        project: Google Cloud project (for Gemini)
        location: Google Cloud location (for Gemini)
        model: Model name (will be overridden for OpenAI if needed)
        image_paths: List of image file paths
        dish_hint: Optional dish name hint
        ing_hint: Optional list of ingredient hints
        
    Returns:
        Dict with ingredients analysis results
    """
    # Get provider from environment variable directly to avoid Flask context issues
    provider = os.getenv("INGREDIENTS_PROVIDER", "gemini").lower()
    
    if provider == "openai":
        # Import OpenAI ingredients function
        from ..openai.openai_ingredients import ingredients_from_image as openai_ingredients
        # Use OpenAI model from environment variable
        openai_model = os.getenv("DEFAULT_OPENAI_MODEL", "gpt-4o")
        return openai_ingredients(
            project=project,
            location=location,  # Not used by OpenAI but kept for compatibility
            model=openai_model,
            image_paths=image_paths,
            dish_hint=dish_hint,
            ing_hint=ing_hint
        )
    else:
        # Default to Gemini
        from ..gemini.gemini_ingredients import ingredients_from_image as gemini_ingredients
        return gemini_ingredients(
            project=project,
            location=location,
            model=model,
            image_paths=image_paths,
            dish_hint=dish_hint,
            ing_hint=ing_hint
        )
