# Centralized Prompts

This directory contains all prompts used across the application, organized by functionality to eliminate code duplication and improve maintainability.

## Structure

```
prompts/
├── food_analysis/
│   └── ingredients_prompt.py    # Ingredient quantification prompt (used by both Gemini and OpenAI)
├── health_score_prompt.py       # Health score calculation prompt
└── README.md                    # This file
```

## Benefits

- **No Code Duplication**: Prompts are defined once and reused across different providers
- **Easy Maintenance**: Changes to prompts only need to be made in one place
- **Consistency**: Ensures all providers use the exact same prompts
- **Better Organization**: Clear separation of concerns

## Usage

### Ingredients Prompt

Used by both Gemini and OpenAI for ingredient quantification:

```python
from prompts.food_analysis.ingredients_prompt import build_ingredients_prompt

# Build prompt with context
prompt = build_ingredients_prompt(dish_hint="chicken stir fry", ing_hint=["chicken", "vegetables"])
```

### Health Score Prompt

Used for health score calculations:

```python
from prompts.health_score_prompt import HEALTH_SCORE_PROMPT

# Use the prompt directly
prompt = HEALTH_SCORE_PROMPT
```

## Adding New Prompts

1. Create a new file in the appropriate subdirectory (or root if it's general)
2. Define the prompt as a constant or function
3. Import and use in the relevant services
4. Update this README

## Migration Notes

- **Before**: Prompts were duplicated in `gemini_ingredients.py` and `openai_ingredients.py`
- **After**: Single source of truth in `prompts/food_analysis/ingredients_prompt.py`
- **Before**: Health score prompt was in `app/config/health_score_prompt.md`
- **After**: Centralized in `prompts/health_score_prompt.py`
