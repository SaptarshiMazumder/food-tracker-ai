# Nutrition Analysis Graph

This module provides a LangGraph workflow for analyzing nutrition information from food descriptions using LLM processing.

## Structure

The nutrition analysis graph follows the Single Responsibility Principle (SRP) with clear separation of concerns:

```
nutrition_analysis/
├── __init__.py                 # Package exports
├── nutrition_analysis_graph.py # Main graph definition and runner
├── state/
│   └── nutrition_analysis_state.py  # State schema definition
├── nodes/
│   ├── validation_node.py           # Input validation logic
│   ├── llm_processing_node.py       # LLM nutrition breakdown processing
│   └── output_validation_node.py    # Output validation and error handling
└── utils/
    └── timing.py                    # Performance timing utilities
```

## Workflow

The graph consists of three main nodes:

1. **Validation Node** (`validate_input`)

   - Validates input data (hint, context)
   - Ensures required fields are present and valid
   - Records validation timing

2. **LLM Processing Node** (`process_nutrition_breakdown`)

   - Calls Gemini LLM service for nutrition breakdown
   - Validates output structure and nutrition totals
   - Records processing timing

3. **Output Validation Node** (`validate_output`)
   - Performs final validation on processed results
   - Checks data integrity and reasonableness
   - Records validation timing

## Usage

### Basic Usage

```python
from app.graphs.nutrition_analysis import run_nutrition_analysis

# Run nutrition analysis
result = run_nutrition_analysis("karaage curry bento")
print(result)
```

### With Context

```python
context = {"user_preferences": "low_carb", "dietary_restrictions": ["gluten"]}
result = run_nutrition_analysis("chicken salad", context)
```

### Building the Graph

```python
from app.graphs.nutrition_analysis import build_nutrition_analysis_graph

# Build and use the graph directly
graph = build_nutrition_analysis_graph()
# ... custom usage
```

## State Schema

The `NutritionAnalysisState` includes:

- **Input**: `hint`, `context`
- **Validation**: `validation_passed`, `validation_error`
- **Processing**: `result`, `llm_error`
- **Performance**: `timings`, `total_ms`
- **Debug**: `debug`, `error`

## Error Handling

The graph provides comprehensive error handling:

- Input validation errors are caught and stored
- LLM processing errors are captured with details
- Output validation ensures data integrity
- All errors are propagated to the final state

## Performance Monitoring

Each node records its execution time, and the main runner provides:

- Individual step timings
- Total execution time
- Pipeline summary output

## Dependencies

- `langgraph`: For graph workflow management
- `app.services.gemini.gemini_nutrition`: For LLM nutrition processing
- Standard Python libraries: `time`, `typing`
