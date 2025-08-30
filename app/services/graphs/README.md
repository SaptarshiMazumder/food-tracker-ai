# Graphs Module

This module contains multiple LangGraph workflows for different analysis and processing tasks. Each graph is organized in its own subdirectory for better maintainability and scalability.

## Structure

```
graphs/
├── __init__.py                 # Main module exports
├── README.md                   # This file
├── food_analysis/              # Food analysis workflow
│   ├── __init__.py
│   ├── food_analysis_graph.py
│   ├── state/
│   ├── nodes/
│   ├── utils/
│   └── README.md
├── recipe_generation/          # Future: Recipe generation workflow
├── meal_planning/              # Future: Meal planning workflow
└── nutrition_tracking/         # Future: Nutrition tracking workflow
```

## Available Graphs

### 1. Food Analysis Graph (`food_analysis/`)

A comprehensive workflow for analyzing food images that includes:

- Dish and ingredient recognition
- Ingredient quantification with weights
- Nutritional analysis and calorie calculation

**Usage:**

```python
from app.services.graphs import run_food_analysis

result = run_food_analysis(
    image_paths=["path/to/food.jpg"],
    project="your-gcp-project",
    location="us-central1",
    model="gemini-1.5-flash"
)
```

**Documentation:** See [food_analysis/README.md](food_analysis/README.md) for detailed documentation.

## Design Principles

### 1. **Modularity**

Each graph is self-contained with its own state, nodes, and utilities.

### 2. **Consistency**

All graphs follow the same structure:

- `state/` - State definitions and schemas
- `nodes/` - Individual graph nodes
- `utils/` - Utility functions
- `README.md` - Documentation

### 3. **Scalability**

Easy to add new graphs without affecting existing ones.

### 4. **Backward Compatibility**

Old interfaces are maintained through compatibility layers.

## Adding New Graphs

To add a new graph workflow:

1. **Create the directory structure:**

   ```bash
   mkdir graphs/your_graph_name
   mkdir graphs/your_graph_name/state
   mkdir graphs/your_graph_name/nodes
   mkdir graphs/your_graph_name/utils
   ```

2. **Create the necessary files:**

   - `__init__.py` - Module exports
   - `your_graph_name_graph.py` - Main graph builder
   - `state/your_graph_state.py` - State definition
   - `nodes/` - Individual node files
   - `utils/` - Utility functions
   - `README.md` - Documentation

3. **Update the main exports:**
   Add your graph's exports to `graphs/__init__.py`

4. **Follow the established patterns:**
   - Use TypedDict for state definitions
   - Include timing and error handling
   - Provide comprehensive documentation

## Example: Adding a Recipe Generation Graph

```python
# graphs/recipe_generation/__init__.py
from .recipe_generation_graph import run_recipe_generation, build_recipe_graph
from .state.recipe_state import RecipeGenerationState

__all__ = [
    "run_recipe_generation",
    "build_recipe_graph",
    "RecipeGenerationState"
]

# graphs/__init__.py
from .food_analysis import run_food_analysis, build_food_analysis_graph, FoodAnalysisState
from .recipe_generation import run_recipe_generation, build_recipe_graph, RecipeGenerationState

__all__ = [
    # Food Analysis Graph
    "run_food_analysis",
    "build_food_analysis_graph",
    "FoodAnalysisState",
    # Recipe Generation Graph
    "run_recipe_generation",
    "build_recipe_graph",
    "RecipeGenerationState"
]
```

## Best Practices

1. **State Management**: Use TypedDict for clear state schemas
2. **Error Handling**: Include comprehensive error handling in each node
3. **Performance**: Include timing and performance monitoring
4. **Documentation**: Document each graph thoroughly
5. **Testing**: Make nodes testable in isolation
6. **Naming**: Use descriptive names for nodes and states
7. **Dependencies**: Keep dependencies minimal and explicit

## Migration from Old Structure

If you're migrating from the old `pipeline/` structure:

1. The old `run_pipeline()` function is still available through the compatibility layer
2. All existing imports continue to work
3. New graphs can be added without affecting existing code
4. Gradually migrate to the new structure as needed

## Future Enhancements

Potential future graphs:

- **Recipe Generation**: Generate recipes from ingredients
- **Meal Planning**: Plan meals based on nutritional goals
- **Nutrition Tracking**: Track nutrition over time
- **Diet Recommendations**: Provide dietary recommendations
- **Ingredient Substitution**: Suggest ingredient alternatives
