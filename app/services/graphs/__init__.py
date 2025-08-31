"""
Graphs Module

This module contains multiple LangGraph workflows for different analysis tasks.
Each graph is organized in its own subdirectory for better maintainability.
"""

# Import the food analysis graph
from .food_analysis import run_food_analysis, build_food_analysis_graph, FoodAnalysisState

# Import the health score graph
from .health_score import run_health_score, build_health_score_graph, HealthScoreState

__all__ = [
    # Food Analysis Graph
    "run_food_analysis",
    "build_food_analysis_graph", 
    "FoodAnalysisState",
    
    # Health Score Graph
    "run_health_score",
    "build_health_score_graph",
    "HealthScoreState"
]
