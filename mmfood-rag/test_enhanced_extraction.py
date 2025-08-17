#!/usr/bin/env python3
"""
Test script for enhanced recipe extraction functionality
"""

import os
import sys
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def test_enhanced_extraction():
    """Test the enhanced recipe extraction functionality"""
    
    try:
        from source_finder import SourceFinder
        from recipe_extractor import RecipeExtractor
        
        print("🚀 Testing Enhanced Recipe Extraction")
        print("=" * 50)
        
        # Test dish and ingredients
        test_dish = "chicken curry"
        test_ingredients = ["chicken", "onion", "garlic", "ginger", "turmeric", "coconut milk"]
        
        print(f"📋 Testing with dish: {test_dish}")
        print(f"🥘 Ingredients: {', '.join(test_ingredients)}")
        print()
        
        # Initialize components
        print("🔧 Initializing components...")
        sf = SourceFinder()
        re = RecipeExtractor()
        print("✅ Components initialized successfully")
        print()
        
        # Test search functionality
        print("🔍 Testing enhanced search...")
        search_results = sf.search_with_fallback(test_dish, test_ingredients, num=3)
        
        if not search_results:
            print("❌ No search results found")
            return
        
        print(f"✅ Found {len(search_results)} search results")
        for i, result in enumerate(search_results, 1):
            print(f"  {i}. {result.get('title', 'No title')}")
            print(f"     URL: {result.get('link', 'No URL')}")
            print(f"     Domain: {result.get('displayLink', 'Unknown')}")
            print()
        
        # Test recipe extraction on first result
        if search_results:
            print("📄 Testing recipe extraction...")
            first_result = search_results[0]
            
            enhanced_sources = re.process_recipe_sources([first_result], test_dish, test_ingredients)
            
            if enhanced_sources:
                enhanced_source = enhanced_sources[0]
                directions = enhanced_source.get('directions', [])
                extraction_method = enhanced_source.get('extraction_method', 'unknown')
                
                print(f"✅ Recipe extraction completed using: {extraction_method}")
                print(f"📝 Found {len(directions)} directions")
                
                if directions:
                    print("\n📋 Extracted Directions:")
                    for i, direction in enumerate(directions[:5], 1):  # Show first 5
                        print(f"  {i}. {direction}")
                    
                    if len(directions) > 5:
                        print(f"  ... and {len(directions) - 5} more")
                else:
                    print("❌ No directions extracted")
                
                # Show content preview
                content_preview = enhanced_source.get('content_preview', '')
                if content_preview:
                    print(f"\n📄 Content Preview: {content_preview[:200]}...")
                
                # Show recipe info if available
                recipe_info = enhanced_source.get('recipe_info', {})
                if recipe_info:
                    print(f"\n📊 Recipe Info:")
                    for key, value in recipe_info.items():
                        if isinstance(value, list):
                            print(f"  {key}: {len(value)} items")
                        else:
                            print(f"  {key}: {value}")
            else:
                print("❌ Recipe extraction failed")
        
        print("\n🎉 Test completed successfully!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all required dependencies are installed")
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

def test_specific_url():
    """Test extraction from a specific recipe URL"""
    
    try:
        from recipe_extractor import RecipeExtractor
        
        print("\n🔗 Testing Specific URL Extraction")
        print("=" * 50)
        
        # Test with a specific recipe URL (you can change this)
        test_url = "https://www.allrecipes.com/recipe/212721/indian-chicken-curry-murgh-kari/"
        
        print(f"📄 Testing URL: {test_url}")
        
        re = RecipeExtractor()
        
        # Fetch and extract content
        content_result = re.fetch_recipe_content(test_url)
        
        if content_result:
            content, recipe_info = content_result
            print(f"✅ Content fetched successfully")
            print(f"📄 Content length: {len(content)} characters")
            
            # Extract directions
            test_ingredients = ["chicken", "onion", "garlic", "ginger", "turmeric"]
            directions = re.extract_directions_with_llm(content, "chicken curry", test_ingredients, recipe_info)
            
            if directions:
                print(f"✅ Extracted {len(directions)} directions using LLM")
                print("\n📋 Directions:")
                for i, direction in enumerate(directions[:5], 1):
                    print(f"  {i}. {direction}")
            else:
                print("❌ No directions extracted with LLM")
                
                # Try simple extraction
                simple_directions = re.extract_directions_simple(content)
                if simple_directions:
                    print(f"✅ Extracted {len(simple_directions)} directions using simple method")
                    for i, direction in enumerate(simple_directions[:3], 1):
                        print(f"  {i}. {direction}")
                else:
                    print("❌ No directions extracted with simple method either")
        else:
            print("❌ Failed to fetch content from URL")
            
    except Exception as e:
        print(f"❌ Error testing specific URL: {e}")

if __name__ == "__main__":
    # Check if required environment variables are set
    required_vars = ["GOOGLE_API_KEY", "GOOGLE_CSE_ID", "GOOGLE_CLOUD_PROJECT"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("⚠️  Missing environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables in your .env file")
        print("The test will continue but some features may not work properly.")
        print()
    
    # Run tests
    test_enhanced_extraction()
    test_specific_url()
