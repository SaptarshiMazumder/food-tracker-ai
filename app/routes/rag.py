from flask import Blueprint, request, jsonify

from ..services.rag_service import RAGService

rag_bp = Blueprint('rag', __name__)

@rag_bp.get("/query")
def query():
    """RAG query endpoint for recipe search"""
    service = RAGService()
    
    ingredients = request.args.get("i", "")
    top = int(request.args.get("top", 5))
    mode = request.args.get("mode", "flexible")  # Default to flexible mode
    
    if not ingredients:
        return jsonify({"error": "missing_ingredients", "msg": "parameter 'i' required"}), 400
    
    try:
        # Parse ingredients
        ings = [s.strip() for s in ingredients.split(",") if s.strip()]
        
        result = service.search_recipes(ings, top, mode)
        
        if "error" in result:
            return jsonify(result), 503 if result["error"] == "rag_not_available" else 500
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": "query_failed", "msg": str(e)}), 500

@rag_bp.get("/recipe_details")
def recipe_details():
    """Recipe details endpoint for strict mode"""
    service = RAGService()
    
    dish_name = request.args.get("dish_name", "")
    ingredients = request.args.get("ingredients", "")
    
    if not dish_name:
        return jsonify({"error": "missing_dish_name", "msg": "parameter 'dish_name' required"}), 400
    
    try:
        # Parse ingredients
        ings = [s.strip() for s in ingredients.split(",") if s.strip()] if ingredients else []
        
        result = service.get_recipe_details(dish_name, ings)
        
        if "error" in result:
            return jsonify(result), 503 if result["error"] == "rag_not_available" else 500
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": "details_failed", "msg": str(e)}), 500
