# Health Score Graph

This module provides a LangGraph-based workflow for calculating health scores from nutritional data. The workflow follows Single Responsibility Principle (SRP) with clear separation of concerns across validation, scoring, and output validation.

## Architecture

The graph follows LangGraph best practices with a clear separation of concerns:

```
graphs/
├── __init__.py                 # Main graphs module exports
└── health_score/               # Health score graph
    ├── __init__.py             # Health score module exports
    ├── health_score_graph.py   # Graph builder and main execution
    ├── state/                  # State definitions
    │   ├── __init__.py
    │   └── health_score_state.py  # TypedDict state definition
    ├── nodes/                  # Individual graph nodes
    │   ├── __init__.py
    │   ├── validation_node.py      # Input validation
    │   ├── scoring_node.py         # LLM health scoring
    │   └── output_validation_node.py  # Output validation
    ├── utils/                  # Utility functions
    │   ├── __init__.py
    │   └── timing.py               # Performance tracking utilities
    └── README.md               # This file
```

## Workflow Stages

### 1. Validation Node (`validate_input`)

- **Purpose**: Validates input data using Pydantic models
- **Input**: Health score input data (calories, macros, ingredients)
- **Output**: Validation status and any validation errors
- **Error Handling**: Captures and reports validation failures

### 2. Scoring Node (`score_health`)

- **Purpose**: Calculates health score using Gemini LLM
- **Input**: Validated health score input data
- **Output**: Health score result with component scores, drivers, and classification
- **Error Handling**: Captures and reports LLM scoring failures

### 3. Output Validation Node (`output_validate`)

- **Purpose**: Validates output data using Pydantic models
- **Input**: LLM health score results
- **Output**: Validation status and any output validation errors
- **Error Handling**: Ensures output meets expected schema

## Usage

```python
from app.graphs.health_score import run_health_score

# Prepare input data
payload = {
    "total_kcal": 450,
    "total_grams": 300,
    "total_fat_g": 15,
    "total_protein_g": 25,
    "items_grams": [
        {"name": "chicken breast", "grams": 150},
        {"name": "brown rice", "grams": 100},
        {"name": "broccoli", "grams": 50}
    ],
    "kcal_confidence": 0.95,
    "use_confidence_dampen": False
}

# Run health score workflow
result = run_health_score(payload)
print(f"Health Score: {result['health_score']}/10")
```

## State Management

The graph uses a typed state (`HealthScoreState`) that tracks:

- **Input data**: Original health score input
- **Validation results**: Input and output validation status
- **LLM results**: Health score calculation results
- **Performance metrics**: Timing information for each node
- **Error handling**: Comprehensive error tracking and reporting

## Performance Monitoring

The graph includes built-in performance monitoring:

- Individual node timing
- Total pipeline execution time
- Success/failure status for each stage
- Detailed error reporting

## Error Handling

The graph implements comprehensive error handling:

- Input validation errors
- LLM scoring failures
- Output validation errors
- Graceful degradation with detailed error messages
