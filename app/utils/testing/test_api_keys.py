#!/usr/bin/env python3
"""
Test Google API keys
"""

import os
import sys
sys.path.append('./mmfood-rag')

from dotenv import load_dotenv

# Load environment variables
load_dotenv('./mmfood-rag/.env')

def test_api_keys():
    print("Testing Google API keys...")
    
    # Check if keys are loaded
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    
    print(f"GOOGLE_API_KEY: {'✓ Found' if api_key else '✗ Missing'}")
    print(f"GOOGLE_CSE_ID: {'✓ Found' if cse_id else '✗ Missing'}")
    print(f"GOOGLE_CLOUD_PROJECT: {'✓ Found' if project else '✗ Missing'}")
    
    if api_key and cse_id:
        print("\nTesting Google Custom Search API...")
        try:
            from source_finder import SourceFinder
            sf = SourceFinder()
            
            # Test a simple search
            results = sf.search("apple bread recipe", ["apple", "bread"], num=1)
            print(f"Search results: {len(results)}")
            
            if results:
                print(f"First result: {results[0].get('title', 'No title')}")
                print("✓ Google Custom Search API is working!")
            else:
                print("✗ No search results returned")
                
                # Let's test the raw API call
                print("\nTesting raw API call...")
                import requests
                from urllib.parse import urlencode
                
                params = {
                    "key": api_key,
                    "cx": cse_id,
                    "q": "apple bread recipe",
                    "num": 1
                }
                
                url = "https://www.googleapis.com/customsearch/v1?" + urlencode(params)
                print(f"API URL: {url}")
                
                resp = requests.get(url, timeout=15)
                print(f"Response status: {resp.status_code}")
                print(f"Response: {resp.text}")
                
                # Parse the JSON response
                data = resp.json()
                print(f"\nParsed response keys: {list(data.keys())}")
                if 'items' in data:
                    print(f"Number of items: {len(data['items'])}")
                    if data['items']:
                        print(f"First item: {data['items'][0]}")
                else:
                    print("No 'items' key in response")
                
        except Exception as e:
            print(f"✗ Error testing Google Custom Search: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n✗ Cannot test API without keys")

if __name__ == "__main__":
    test_api_keys()
