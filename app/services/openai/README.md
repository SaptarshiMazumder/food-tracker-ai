# OpenAI Ingredients Service

This service provides ingredient quantification functionality using OpenAI GPT models, as an alternative to the Google Gemini service.

## Features

- **Same Interface**: Uses the exact same function signature as `gemini_ingredients.py`
- **Environment Variable Control**: Switch between providers using `INGREDIENTS_PROVIDER` environment variable
- **Same Output Format**: Returns identical JSON structure as Gemini version
- **Same Prompt**: Uses the exact same prompt and rules as the Gemini version

## Setup

1. **Install Dependencies**:

   ```bash
   pip install openai>=1.0
   ```

2. **Set Environment Variables**:

   ```bash
   # Required for OpenAI
   export OPENAI_API_KEY="your-openai-api-key"

   # Optional: Choose provider (defaults to "gemini")
   export INGREDIENTS_PROVIDER="openai"  # or "gemini"

   # Optional: Set OpenAI model (defaults to "gpt-4o")
   export DEFAULT_OPENAI_MODEL="gpt-4o"
   ```

## Usage

### Direct Usage

```python
from app.services.openai.openai_ingredients import ingredients_from_image

result = ingredients_from_image(
    project=None,  # Not used by OpenAI
    location="global",  # Not used by OpenAI
    model="gpt-4o",
    image_paths=["path/to/image.jpg"],
    dish_hint="chicken stir fry",
    ing_hint=["chicken", "vegetables", "rice"]
)
```

### Through Food Analysis Service

The food analysis service automatically uses the configured provider:

```python
from app.services.food_analysis.food_analysis_ingredient_quantifier_factory import FoodAnalysisIngredientQuantifierFactory

quantifier = FoodAnalysisIngredientQuantifierFactory.create_quantifier('openai')
result = quantifier.quantify_ingredients(
    project="your-project",
    location="global",
    model="gpt-4o",
    image_paths=["path/to/image.jpg"],
    dish_hint="chicken stir fry",
    ing_hint=["chicken", "vegetables", "rice"]
)
```

## Environment Variables

| Variable               | Default  | Description                           |
| ---------------------- | -------- | ------------------------------------- |
| `OPENAI_API_KEY`       | Required | Your OpenAI API key                   |
| `INGREDIENTS_PROVIDER` | "gemini" | Choose provider: "gemini" or "openai" |
| `DEFAULT_OPENAI_MODEL` | "gpt-4o" | Default OpenAI model to use           |

## Testing

Run the test script to verify functionality:

```bash
cd app/services/openai
python test_openai_ingredients.py path/to/test/image.jpg
```

## Output Format

Returns the same JSON structure as Gemini:

```json
{
  "items": [
    {
      "name": "chicken",
      "grams": 150,
      "note": "cooked chicken breast"
    },
    {
      "name": "cooking oil",
      "grams": 12,
      "note": "stir-fry oil"
    }
  ],
  "total_grams": 162,
  "confidence": 0.85,
  "notes": "Estimated for single serving"
}
```

## Error Handling

The function returns error information in the same format as Gemini:

```json
{
  "error": "openai_api_error: Invalid API key",
  "raw": "Raw error response from OpenAI"
}
```

## Integration with LangGraph

The service integrates seamlessly with the existing food analysis LangGraph by using the strategy pattern. The graph nodes automatically use the configured provider based on the `INGREDIENTS_PROVIDER` environment variable.
