#!/usr/bin/env python3
"""
Quick test for enhanced recipe extraction
"""

import sys
import os
sys.path.append('./mmfood-rag')

def test_extraction():
    try:
        from source_finder import SourceFinder
        from recipe_extractor import RecipeExtractor
        
        print("Testing enhanced recipe extraction...")
        
        # Test with simple ingredients
        sf = SourceFinder()
        re = RecipeExtractor()
        
        # Test search
        print("Testing search...")
        results = sf.search_with_fallback("chocolate bread", ["chocolate", "bread"], num=2)
        print(f"Search results: {len(results)}")
        
        if results:
            print(f"First result: {results[0].get('title', 'No title')}")
            
            # Test extraction
            print("Testing extraction...")
            enhanced = re.process_recipe_sources([results[0]], "chocolate bread", ["chocolate", "bread"])
            print(f"Enhanced results: {len(enhanced)}")
            
            if enhanced:
                source = enhanced[0]
                print(f"Directions found: {len(source.get('directions', []))}")
                print(f"Extraction method: {source.get('extraction_method', 'unknown')}")
                print(f"Recipe info: {bool(source.get('recipe_info', {}))}")
        
        print("Test completed!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_extraction()
