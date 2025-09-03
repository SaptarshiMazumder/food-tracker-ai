#!/usr/bin/env python3
"""
Test script for the restructured nutrition analysis graph.
This script verifies that the new SRP-based structure works correctly.
"""

import sys
import os

def test_imports():
    """Test that all imports work correctly"""
    try:
        from app.graphs.nutrition_analysis import (
            run_nutrition_analysis, 
            build_nutrition_analysis_graph, 
            NutritionAnalysisState
        )
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_state_structure():
    """Test that the state structure is correct"""
    try:
        from app.graphs.nutrition_analysis.state import NutritionAnalysisState
        
        # Test state creation
        state = NutritionAnalysisState(
            hint="test food",
            context={},
            validation_passed=None,
            validation_error=None,
            result=None,
            llm_error=None,
            timings={},
            total_ms=None,
            debug={},
            error=None
        )
        print("✅ State structure is correct")
        return True
    except Exception as e:
        print(f"❌ State structure test failed: {e}")
        return False

def test_graph_building():
    """Test that the graph can be built"""
    try:
        from app.graphs.nutrition_analysis import build_nutrition_analysis_graph
        
        graph = build_nutrition_analysis_graph()
        print("✅ Graph building successful")
        return True
    except Exception as e:
        print(f"❌ Graph building failed: {e}")
        return False

def test_node_imports():
    """Test that all nodes can be imported"""
    try:
        from app.graphs.nutrition_analysis.nodes.validation_node import validate_input
        from app.graphs.nutrition_analysis.nodes.llm_processing_node import process_nutrition_breakdown
        from app.graphs.nutrition_analysis.nodes.output_validation_node import validate_output
        print("✅ All node imports successful")
        return True
    except ImportError as e:
        print(f"❌ Node import failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing Nutrition Analysis Graph Restructure")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_state_structure,
        test_graph_building,
        test_node_imports
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! The restructure was successful.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main())
