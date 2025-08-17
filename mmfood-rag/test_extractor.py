#!/usr/bin/env python3
"""
Test script for the RecipeExtractor
"""

import sys
import os
sys.path.append('..')

from recipe_extractor import RecipeExtractor

def test_extractor():
    """Test the recipe extractor with a sample recipe URL"""
    
    # Sample recipe URL (you can replace with any recipe URL)
    test_url = "https://www.allrecipes.com/recipe/24074/alysias-basic-meat-lasagna/"
    
    print("Testing RecipeExtractor...")
    print(f"URL: {test_url}")
    
    try:
        extractor = RecipeExtractor()
        
        # Fetch content
        print("\n1. Fetching content...")
        content = extractor.fetch_recipe_content(test_url)
        
        if content:
            print(f"✓ Content fetched successfully ({len(content)} characters)")
            print(f"Preview: {content[:200]}...")
            
            # Test direction extraction
            print("\n2. Extracting directions...")
            directions = extractor.extract_directions_simple(content)
            
            if directions:
                print(f"✓ Found {len(directions)} directions:")
                for i, direction in enumerate(directions[:5], 1):
                    print(f"  {i}. {direction}")
            else:
                print("✗ No directions found with simple extraction")
                
            # Test LLM extraction if available
            if hasattr(extractor, 'extract_directions_with_llm'):
                print("\n3. Testing LLM extraction...")
                llm_directions = extractor.extract_directions_with_llm(
                    content, "Basic Meat Lasagna", ["ground beef", "lasagna noodles", "cheese"]
                )
                
                if llm_directions:
                    print(f"✓ LLM extracted {len(llm_directions)} directions:")
                    for i, direction in enumerate(llm_directions[:5], 1):
                        print(f"  {i}. {direction}")
                else:
                    print("✗ No directions found with LLM extraction")
        else:
            print("✗ Failed to fetch content")
            
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_extractor()

