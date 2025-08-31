import time
from typing import List, Optional

from langgraph.graph import StateGraph, END

from .state.food_analysis_state import FoodAnalysisState
from .nodes.recognition_node import recognize_dish
from .nodes.ingredient_quantification_node import quantify_ingredients
from .nodes.calories_node import calculate_calories
from .utils.timing import print_pipeline_summary

def build_food_analysis_graph():
    """
    Build the food analysis graph with three main nodes:
    1. recognize_dish - Identifies dishes and ingredients from images
    2. quantify_ingredients - Quantifies ingredients with weights
    3. calculate_calories - Computes nutritional information
    
    Returns:
        Compiled LangGraph workflow
    """
    # Create the state graph
    workflow = StateGraph(FoodAnalysisState)
    
    # Add nodes
    workflow.add_node("recognize", recognize_dish)
    workflow.add_node("ing_quant", quantify_ingredients)
    workflow.add_node("calories", calculate_calories)
    
    # Define the workflow
    workflow.set_entry_point("recognize")
    workflow.add_edge("recognize", "ing_quant")
    workflow.add_edge("ing_quant", "calories")
    workflow.add_edge("calories", END)
    
    return workflow.compile()

def run_food_analysis(
    image_paths: List[str], 
    project: Optional[str], 
    location: str, 
    model: str
) -> FoodAnalysisState:
    """
    Run the complete food analysis workflow.
    
    Args:
        image_paths: List of paths to food images
        project: Google Cloud project ID
        location: Google Cloud location
        model: Gemini model name
        
    Returns:
        Complete analysis results with recognition, quantification, and nutrition data
    """
    # Initialize state
    initial_state: FoodAnalysisState = {
        "image_paths": image_paths,
        "project": project,
        "location": location,
        "model": model,
        
        # Recognition results
        "dish": "",
        "ingredients": [],
        "gemini_conf": 0.0,
        
        # Ingredient quantification results
        "items": [],
        "total_grams": None,
        "ing_conf": None,
        "ing_notes": None,
        
        # Nutritional analysis results
        "nutr_items": [],
        "total_kcal": None,
        "total_protein_g": None,
        "total_carbs_g": None,
        "total_fat_g": None,
        "kcal_conf": None,
        "kcal_notes": None,
        
        # Performance tracking
        "timings": {},
        "total_ms": None,
        
        # Debug and error handling
        "debug": {},
        "error": None
    }

    # Execute the workflow
    t0_total = time.perf_counter()
    graph = build_food_analysis_graph()
    result = graph.invoke(initial_state)
    result["total_ms"] = round((time.perf_counter() - t0_total) * 1000.0, 2)

    # Print final summary
    print_pipeline_summary(result["timings"], result["total_ms"])

    return result
