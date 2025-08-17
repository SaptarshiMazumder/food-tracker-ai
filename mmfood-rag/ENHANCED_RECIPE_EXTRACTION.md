# Enhanced Recipe Extraction System

This document describes the enhanced recipe extraction functionality that improves the Google search aspect and extracts cooking directions from recipe websites using LLM processing.

## Overview

The enhanced system provides:

- **Improved Google Search**: Better targeting of recipe websites with multiple search strategies
- **Advanced Web Scraping**: Robust content extraction from recipe websites
- **LLM-Powered Direction Extraction**: AI-powered extraction of cooking directions
- **Fallback Mechanisms**: Multiple extraction methods for reliability
- **Structured Data Support**: Parsing of JSON-LD and microdata recipe markup

## Components

### 1. Enhanced SourceFinder (`source_finder.py`)

**Features:**

- Multiple search query generation for better coverage
- Targeting of specific recipe websites (AllRecipes, Food Network, etc.)
- Result ranking and deduplication
- Fallback search strategies

**Search Strategies:**

1. **Basic Recipe Search**: `"dish name" recipe ingredients`
2. **How-to Queries**: `how to make dish name with ingredients`
3. **Site-Specific Searches**: Targeting trusted recipe domains
4. **Cooking Method Queries**: `baked/fried/grilled dish name recipe`

**Result Ranking:**

- Boosts recipe-focused websites
- Prioritizes content with recipe-related terms
- Penalizes non-recipe content (social media, etc.)

### 2. Enhanced RecipeExtractor (`recipe_extractor.py`)

**Content Extraction Methods:**

1. **Structured Data Parsing**: JSON-LD and microdata
2. **CSS Selector Targeting**: Common recipe site patterns
3. **Fallback Content Extraction**: General text extraction

**Direction Extraction:**

1. **LLM-Powered Extraction**: Uses Gemini to extract directions
2. **Pattern Matching**: Regex-based fallback extraction
3. **Cooking Verb Detection**: Identifies cooking-related sentences

**Enhanced Features:**

- Better error handling and logging
- Content validation and filtering
- Rate limiting and timeout management
- Extraction method tracking

## Usage

### Basic Usage

```python
from source_finder import SourceFinder
from recipe_extractor import RecipeExtractor

# Initialize components
sf = SourceFinder()
re = RecipeExtractor()

# Search for recipes
sources = sf.search_with_fallback("chicken curry", ["chicken", "onion", "garlic"], num=5)

# Extract directions from sources
enhanced_sources = re.process_recipe_sources(sources, "chicken curry", ["chicken", "onion", "garlic"])
```

### API Integration

The enhanced functionality is integrated into the `/query` endpoint:

```bash
GET /query?i=chicken,onion,garlic&top=5
```

**Response includes:**

- Recipe hits from the RAG index
- Enhanced web sources with extracted directions
- Extraction method information
- Recipe metadata (cooking times, etc.)

### Frontend Display

The frontend displays:

- **Extraction Method Indicator**: Shows whether directions were extracted via LLM or pattern matching
- **Recipe Metadata**: Cooking times, prep times, etc.
- **Content Previews**: Snippets of extracted content
- **Enhanced Source Information**: Better organized source display

## Configuration

### Environment Variables

```bash
# Required for Google Search
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_custom_search_engine_id

# Required for LLM extraction
GOOGLE_CLOUD_PROJECT=your_gcp_project
```

### LLM Configuration

The system uses Gemini 2.0 Flash for direction extraction:

```python
# Default configuration
model = "gemini-2.0-flash-exp"
temperature = 0.1
max_output_tokens = 2048
```

## Testing

Run the test script to verify functionality:

```bash
cd mmfood-rag
python test_enhanced_extraction.py
```

The test script will:

1. Test search functionality
2. Test recipe extraction
3. Test specific URL extraction
4. Validate environment configuration

## Error Handling

The system includes comprehensive error handling:

- **Search Failures**: Fallback to broader queries
- **Extraction Failures**: Multiple extraction methods
- **Network Issues**: Timeout and retry logic
- **Content Issues**: Validation and filtering

## Performance Considerations

- **Rate Limiting**: 1-second delays between requests
- **Content Limits**: 8000 character content limits
- **Result Limits**: Maximum 15 directions per recipe
- **Concurrent Processing**: Sequential processing for reliability

## Future Enhancements

Potential improvements:

1. **Caching**: Cache extracted directions to reduce API calls
2. **Parallel Processing**: Process multiple sources concurrently
3. **More LLM Models**: Support for additional AI models
4. **Recipe Validation**: Validate extracted recipes for completeness
5. **User Feedback**: Allow users to rate extraction quality

## Troubleshooting

### Common Issues

1. **No Search Results**

   - Check Google API key and CSE ID
   - Verify search query format
   - Check API quotas

2. **No Directions Extracted**

   - Verify Gemini API access
   - Check content quality
   - Review extraction logs

3. **Poor Extraction Quality**
   - Adjust LLM prompts
   - Improve content filtering
   - Add more recipe site patterns

### Logging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

The system logs:

- Search queries and results
- Content extraction attempts
- LLM API calls
- Error conditions
