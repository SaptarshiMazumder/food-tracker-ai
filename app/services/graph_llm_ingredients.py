"""
Compatibility layer for the old graph_llm_ingredients.py interface.

This module provides backward compatibility while using the new refactored graph structure.
"""

from typing import List, Optional

from .graphs import run_food_analysis, FoodAnalysisState

# Re-export the main function with the old name for backward compatibility
def run_pipeline(image_paths: List[str], project: Optional[str], location: str, model: str) -> FoodAnalysisState:
    """
    Backward compatibility function that maintains the old interface.
    
    Args:
        image_paths: List of paths to food images
        project: Google Cloud project ID  
        location: Google Cloud location
        model: Gemini model name
        
    Returns:
        Complete analysis results
    """
    return run_food_analysis(image_paths, project, location, model)

# Re-export the state type for backward compatibility
S = FoodAnalysisState

# Re-export the build function for backward compatibility  
def build_graph():
    """Backward compatibility function for building the graph."""
    from .graphs import build_food_analysis_graph
    return build_food_analysis_graph()

# Re-export node functions for backward compatibility
def node_recognize(state: S) -> S:
    """Backward compatibility wrapper for the recognition node."""
    from .graphs.food_analysis.nodes import recognize_dish
    return recognize_dish(state)

def node_ing_quant(state: S) -> S:
    """Backward compatibility wrapper for the ingredient quantification node."""
    from .graphs.food_analysis.nodes import quantify_ingredients
    return quantify_ingredients(state)

def node_calories(state: S) -> S:
    """Backward compatibility wrapper for the calories calculation node."""
    from .graphs.food_analysis.nodes import calculate_calories
    return calculate_calories(state)
