#!/usr/bin/env python3
"""
Debug timing for enhanced recipe extraction
"""

import time
import sys
import os
sys.path.append('./mmfood-rag')

from dotenv import load_dotenv
load_dotenv('./mmfood-rag/.env')

def time_operation(name, func, *args, **kwargs):
    """Time an operation and print results"""
    print(f"\n🕐 Starting: {name}")
    start = time.time()
    try:
        result = func(*args, **kwargs)
        end = time.time()
        print(f"✅ {name} completed in {end-start:.2f}s")
        return result
    except Exception as e:
        end = time.time()
        print(f"❌ {name} failed in {end-start:.2f}s: {e}")
        return None

def debug_enhanced_extraction():
    """Debug the timing of enhanced recipe extraction"""
    print("🚀 Debug: Enhanced Recipe Extraction Timing")
    print("=" * 50)
    
    # Test ingredients
    dish_name = "apple bread"
    ingredients = ["apple", "bread", "flour"]
    
    # 1. Test SourceFinder initialization
    sf = time_operation("SourceFinder initialization", lambda: __import__('source_finder').SourceFinder())
    if not sf:
        return
    
    # 2. Test search
    search_results = time_operation("Google search", sf.search, dish_name, ingredients, 2)
    if not search_results:
        print("❌ No search results, stopping here")
        return
    
    print(f"📝 Found {len(search_results)} search results")
    
    # 3. Test RecipeExtractor initialization  
    re = time_operation("RecipeExtractor initialization", lambda: __import__('recipe_extractor').RecipeExtractor())
    if not re:
        return
    
    # 4. Test web scraping (just first result)
    if search_results:
        first_url = search_results[0].get('link')
        if first_url:
            content = time_operation(f"Web scraping {first_url}", re.fetch_recipe_content, first_url)
            if content:
                content_text, recipe_info = content
                print(f"📄 Scraped {len(content_text)} characters")
                
                # 5. Test LLM extraction
                directions = time_operation("LLM direction extraction", 
                                          re.extract_directions_with_llm, 
                                          content_text, dish_name, ingredients, recipe_info)
                
                if directions:
                    print(f"📋 Extracted {len(directions)} directions")
                    for i, direction in enumerate(directions[:3], 1):
                        print(f"  {i}. {direction[:80]}...")
    
    # 6. Test full process
    print(f"\n🔄 Testing full process for {len(search_results)} sources...")
    enhanced_sources = time_operation("Full recipe extraction process", 
                                    re.process_recipe_sources, 
                                    search_results, dish_name, ingredients)
    
    if enhanced_sources:
        print(f"✅ Enhanced {len(enhanced_sources)} sources")
        for source in enhanced_sources:
            directions_count = len(source.get('directions', []))
            method = source.get('extraction_method', 'unknown')
            print(f"  - {source.get('title', 'No title')}: {directions_count} directions ({method})")

if __name__ == "__main__":
    debug_enhanced_extraction()
