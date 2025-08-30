# Food Analysis Graph

This module provides a LangGraph-based workflow for analyzing food images. The workflow consists of three main stages that process food images to extract dish information, quantify ingredients, and calculate nutritional content.

## Architecture

The graph follows LangGraph best practices with a clear separation of concerns:

```
graphs/
├── __init__.py                 # Main graphs module exports
└── food_analysis/              # Food analysis graph
    ├── __init__.py             # Food analysis module exports
    ├── food_analysis_graph.py  # Graph builder and main execution
    ├── state/                  # State definitions
    │   ├── __init__.py
    │   └── food_analysis_state.py  # TypedDict state definition
    ├── nodes/                  # Individual graph nodes
    │   ├── __init__.py
    │   ├── recognition_node.py     # Dish and ingredient recognition
    │   ├── ingredient_quantification_node.py  # Ingredient quantification
    │   └── calories_node.py        # Nutritional analysis
    ├── utils/                  # Utility functions
    │   ├── __init__.py
    │   └── timing.py               # Performance tracking utilities
    └── README.md               # This file
```

This structure allows for easy addition of new graphs in the future:

```
graphs/
├── food_analysis/              # Food analysis workflow
├── recipe_generation/          # Future: Recipe generation workflow
├── meal_planning/              # Future: Meal planning workflow
└── nutrition_tracking/         # Future: Nutrition tracking workflow
```

## Workflow Stages

### 1. Recognition Node (`recognize_dish`)

- **Purpose**: Identifies dishes and ingredients from food images using Gemini Vision
- **Input**: Image paths, project config, model settings
- **Output**: Dish name, ingredients list, confidence score
- **Dependencies**: `gemini_recognize_dish`

### 2. Ingredient Quantification Node (`quantify_ingredients`)

- **Purpose**: Quantifies ingredients with weights and measurements
- **Input**: Image paths, dish hints, ingredient hints
- **Output**: Quantified ingredients, total grams, confidence
- **Dependencies**: `gemini_ingredients`

### 3. Calories Node (`calculate_calories`)

- **Purpose**: Calculates nutritional information from quantified ingredients
- **Input**: Quantified ingredients, dish name
- **Output**: Nutritional breakdown (calories, protein, carbs, fat)
- **Dependencies**: `gemini_calories`

## Usage

### Basic Usage

```python
from app.services.graphs import run_food_analysis

# Run the complete workflow
result = run_food_analysis(
    image_paths=["path/to/food.jpg"],
    project="your-gcp-project",
    location="us-central1",
    model="gemini-1.5-flash"
)

# Access results
print(f"Dish: {result['dish']}")
print(f"Total calories: {result['total_kcal']}")
print(f"Total grams: {result['total_grams']}")
```

### Direct Import (if needed)

```python
from app.services.graphs.food_analysis import run_food_analysis, FoodAnalysisState

# Direct access to the food analysis graph
result = run_food_analysis(...)
```

### Backward Compatibility

The old interface is maintained for backward compatibility:

```python
from app.services.graph_llm_ingredients import run_pipeline

# Old interface still works
result = run_pipeline(
    image_paths=["path/to/food.jpg"],
    project="your-gcp-project",
    location="us-central1",
    model="gemini-1.5-flash"
)
```

## State Schema

The `FoodAnalysisState` TypedDict defines the complete state structure:

- **Input parameters**: `image_paths`, `project`, `location`, `model`
- **Recognition results**: `dish`, `ingredients`, `gemini_conf`
- **Quantification results**: `items`, `total_grams`, `ing_conf`, `ing_notes`
- **Nutritional results**: `nutr_items`, `total_kcal`, `total_protein_g`, etc.
- **Performance tracking**: `timings`, `total_ms`
- **Debug/Error handling**: `debug`, `error`

## Performance Monitoring

The graph includes built-in performance monitoring:

- Individual node timing
- Total workflow timing
- Standardized logging output
- Error tracking and debugging information

## Error Handling

Each node includes comprehensive error handling:

- API failures are captured and logged
- Debug information is preserved in state
- Graceful degradation when possible
- Clear error messages for troubleshooting

## Best Practices

This refactoring follows LangGraph industry standards:

1. **Separation of Concerns**: Each node has a single responsibility
2. **Type Safety**: Full TypedDict state definition
3. **Modularity**: Nodes can be tested and developed independently
4. **Observability**: Built-in timing and logging
5. **Backward Compatibility**: Old interfaces maintained
6. **Clear Documentation**: Each component is well-documented
7. **Scalability**: Structure supports multiple graph workflows

## Adding New Graphs

To add a new graph workflow:

1. Create a new subdirectory in `graphs/` (e.g., `graphs/recipe_generation/`)
2. Follow the same structure as `food_analysis/`
3. Create state, nodes, and utils subdirectories
4. Add the new graph to the main `graphs/__init__.py` exports
5. Update this README with the new graph documentation
