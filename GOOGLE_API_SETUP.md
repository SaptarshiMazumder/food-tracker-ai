# Google API Setup for Enhanced Recipe Extraction

To enable the enhanced recipe extraction (Google search + LLM direction extraction), you need to set up Google API keys.

## Required APIs

1. **Google Custom Search API** - for searching recipe websites
2. **Google Gemini API** - for extracting cooking directions from web content

## Setup Steps

### 1. Google Custom Search API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the **Custom Search API**
4. Create credentials (API Key)
5. Create a **Custom Search Engine**:
   - Go to [Custom Search Engine](https://cse.google.com/cse/)
   - Create a new search engine
   - Set it to search the entire web
   - Get your Search Engine ID

### 2. Google Gemini API

1. In Google Cloud Console, enable the **Generative AI API**
2. Create a service account and download the JSON key file
3. Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable

## Environment Variables

Create a `.env` file in your project root:

```bash
# Google Custom Search API
GOOGLE_API_KEY=your_custom_search_api_key_here
GOOGLE_CSE_ID=your_custom_search_engine_id_here

# Google Cloud Project
GOOGLE_CLOUD_PROJECT=your_project_id_here

# Optional: Service account credentials
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
```

## Quick Test

After setting up the environment variables, test the enhanced extraction:

```bash
cd mmfood-rag
python ../test_extraction_quick.py
```

## What You'll Get

With the APIs configured, you'll see:

- **Google search results** from recipe websites
- **AI-extracted cooking directions** from web content
- **Recipe metadata** (cooking times, etc.)
- **Extraction method indicators** (AI vs Pattern matching)

## Troubleshooting

- **Empty sources**: Check if API keys are set correctly
- **Timeout errors**: Increase timeout in frontend (already set to 30s)
- **Import errors**: Make sure all dependencies are installed

## Alternative: Manual Setup

If you don't want to set up the APIs right now, the system will still work with basic RAG functionality, just without the enhanced web search and direction extraction.
