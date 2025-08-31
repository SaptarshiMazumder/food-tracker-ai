#!/usr/bin/env python3
"""
Test script for OpenAI ingredients function.
Usage: python test_openai_ingredients.py <image_path>
"""

import sys
import os
from openai_ingredients import ingredients_from_image

def test_openai_ingredients(image_path: str):
    """Test the OpenAI ingredients function with a single image."""
    
    if not os.path.exists(image_path):
        print(f"Error: Image file {image_path} does not exist")
        return
    
    print(f"Testing OpenAI ingredients with image: {image_path}")
    print("=" * 50)
    
    try:
        # Test with OpenAI
        result = ingredients_from_image(
            project=None,  # Not used by OpenAI
            location="global",  # Not used by OpenAI
            model="gpt-4o",  # OpenAI model
            image_paths=[image_path],
            dish_hint="",
            ing_hint=None
        )
        
        if "error" in result:
            print(f"Error: {result['error']}")
            if "raw" in result:
                print(f"Raw response: {result['raw']}")
        else:
            print("Success!")
            print(f"Items: {result.get('items', [])}")
            print(f"Total grams: {result.get('total_grams', 0)}")
            print(f"Confidence: {result.get('confidence', 0)}")
            print(f"Notes: {result.get('notes', '')}")
            
    except Exception as e:
        print(f"Exception occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_openai_ingredients.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    test_openai_ingredients(image_path)
