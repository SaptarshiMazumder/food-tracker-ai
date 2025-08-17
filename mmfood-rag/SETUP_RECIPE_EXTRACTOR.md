# Recipe Extractor Setup Guide

This guide explains how to set up the enhanced recipe extraction feature that fetches recipe content from websites and extracts cooking directions using LLM.

## Features

- **Web Scraping**: Fetches recipe content from Google search results
- **LLM Extraction**: Uses Gemini to extract cooking directions from recipe content
- **Fallback Extraction**: Simple regex-based extraction when LLM is not available
- **Rate Limiting**: Built-in delays to respect website policies

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google API Setup (Optional but Recommended)

For LLM-based direction extraction, you need Google Cloud credentials:

1. Set up Google Cloud Project
2. Enable Gemini API
3. Set environment variables:
   ```bash
   export GOOGLE_CLOUD_PROJECT="your-project-id"
   ```

### 3. Google Custom Search Setup (Required)

For web search functionality:

1. Get Google API Key: https://console.cloud.google.com/apis/credentials
2. Create Custom Search Engine: https://cse.google.com/cse/
3. Set environment variables:
   ```bash
   export GOOGLE_API_KEY="your-api-key"
   export GOOGLE_CSE_ID="your-cse-id"
   ```

## Usage

### Command Line

```bash
# Basic query without recipe extraction
python query.py -i "chicken, rice, onion"

# Query with recipe extraction (requires Google APIs)
python query.py -i "chicken, rice, onion" --extract_recipes
```

### API Endpoint

The Flask API automatically includes recipe extraction when available.

### Testing

```bash
# Test the extractor with a sample URL
python test_extractor.py
```

## How It Works

1. **Search**: Uses Google Custom Search to find recipe websites
2. **Fetch**: Scrapes recipe content from top results
3. **Extract**: Uses LLM to extract cooking directions
4. **Fallback**: Uses regex patterns if LLM extraction fails
5. **Display**: Shows extracted directions in the UI

## Configuration

### Rate Limiting

The extractor includes 1-second delays between requests to respect website policies.

### Content Limits

- Content is limited to 8000 characters for processing
- LLM prompts are limited to 6000 characters
- Maximum 10 directions per recipe

### Error Handling

- Graceful fallback when APIs are unavailable
- Timeout handling for slow websites
- Content validation before processing

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all dependencies are installed
2. **API Errors**: Check Google API credentials and quotas
3. **Scraping Errors**: Some websites may block automated requests
4. **LLM Errors**: Verify Gemini API is enabled and configured

### Debug Mode

Enable debug logging by setting:

```bash
export DEBUG=1
```

## Performance

- Processing time: ~2-3 seconds per recipe source
- Memory usage: Minimal (content is processed in chunks)
- Network usage: ~50-200KB per recipe source

