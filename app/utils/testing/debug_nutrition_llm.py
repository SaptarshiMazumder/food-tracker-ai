#!/usr/bin/env python3
"""
Debug script to test the LLM nutrition service directly.
This helps identify what structure the LLM is actually returning.
"""

import sys
import os
import json

def test_llm_service():
    """Test the LLM service directly to see the actual response structure"""
    try:
        from app.graphs.nutrition_analysis.services.gemini.gemini_nutrition import llm_nutrition_breakdown
        
        print("Testing LLM service directly...")
        print("=" * 50)
        
        # Test with a simple food hint
        test_input = {"hint": "chicken salad"}
        
        print(f"Input: {test_input}")
        print("Calling LLM service...")
        
        result = llm_nutrition_breakdown(test_input)
        
        print("✅ LLM service call successful!")
        print(f"Result type: {type(result)}")
        print(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        if isinstance(result, dict):
            # Check the structure of items_nutrition
            if "items_nutrition" in result:
                items = result["items_nutrition"]
                print(f"items_nutrition count: {len(items)}")
                if items:
                    print(f"First item keys: {list(items[0].keys())}")
                    print(f"First item: {json.dumps(items[0], indent=2)}")
                else:
                    print("items_nutrition is empty!")
            else:
                print("❌ items_nutrition key missing!")
            
            # Check the structure of items_kcal
            if "items_kcal" in result:
                items = result["items_kcal"]
                print(f"items_kcal count: {len(items)}")
                if items:
                    print(f"First item keys: {list(items[0].keys())}")
                    print(f"First item: {json.dumps(items[0], indent=2)}")
                else:
                    print("items_kcal is empty!")
            else:
                print("❌ items_kcal key missing!")
            
            # Check the structure of items_grams
            if "items_grams" in result:
                items = result["items_grams"]
                print(f"items_grams count: {len(items)}")
                if items:
                    print(f"First item keys: {list(items[0].keys())}")
                    print(f"First item: {json.dumps(items[0], indent=2)}")
                else:
                    print("items_grams is empty!")
            else:
                print("❌ items_grams key missing!")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print("Debug Nutrition LLM Service")
    print("=" * 50)
    
    success = test_llm_service()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Debug test completed successfully")
    else:
        print("❌ Debug test failed")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
