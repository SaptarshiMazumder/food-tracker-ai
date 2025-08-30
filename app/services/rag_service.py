import os
from typing import List, Dict, Any
from flask import current_app

# Import RAG components
import sys
sys.path.append('./mmfood-rag')
try:
    from retriever import RecipeIndex
    from schema import DishHit, QueryResult
except ImportError:
    print("Warning: mmfood-rag components not available. RAG query functionality will be disabled.")
    RecipeIndex = None
    DishHit = None
    QueryResult = None

class RAGService:
    """Service for handling RAG (Recipe) operations"""
    
    def __init__(self):
        self.artifacts_dir = current_app.config['RAG_ARTIFACTS_DIR']
        self.google_api_key = current_app.config['GOOGLE_API_KEY']
        self.google_cse_id = current_app.config['GOOGLE_CSE_ID']
    
    def is_available(self) -> bool:
        """Check if RAG components are available"""
        return RecipeIndex is not None
    
    def search_recipes(self, ingredients: List[str], top: int = 5, mode: str = "flexible") -> Dict[str, Any]:
        """Search for recipes based on ingredients"""
        if not self.is_available():
            return {"error": "rag_not_available", "msg": "RAG components not available"}
        
        try:
            # Initialize recipe index with correct path
            idx = RecipeIndex(out_dir=self.artifacts_dir)
            df = idx.search(ingredients, k=max(25, top*5), dedupe=True).head(top)
            
            # Build hits with additional deduplication
            hits = []
            seen_dish_names = set()
            
            for _, r in df.iterrows():
                dish_name = r.get("dish_name", "").strip().lower()
                
                # Skip if we've already seen this dish name (case-insensitive deduplication)
                if dish_name in seen_dish_names:
                    continue
                    
                seen_dish_names.add(dish_name)
                
                hits.append(DishHit(
                    dish_name=r.get("dish_name", ""),
                    ingredients=list(r.get("ingredients", [])),
                    cooking_method=str(r.get("cooking_method", "")),
                    cuisine=str(r.get("cuisine", "")),
                    image_url=str(r.get("image_url", "")),
                    source_datasets=list(r.get("source_datasets", [])),
                    cluster_id=str(r.get("cluster_id", "")),
                    score=float(r.get("score", 0.0)),
                    directions=list(r.get("directions", [])),
                ))
            
            # Get Google search sources for each dish (only in flexible mode)
            sources = {}
            if mode == "flexible":
                sources = self._get_enhanced_sources(hits)
            else:
                # In strict mode, initialize empty sources
                sources = {h.dish_name: [] for h in hits}
            
            return {
                "query_ingredients": ingredients,
                "hits": [hit.model_dump() for hit in hits],
                "sources": sources
            }
            
        except Exception as e:
            return {"error": "query_failed", "msg": str(e)}
    
    def get_recipe_details(self, dish_name: str, ingredients: List[str]) -> Dict[str, Any]:
        """Get detailed recipe information for a specific dish"""
        if not self.is_available():
            return {"error": "rag_not_available", "msg": "RAG components not available"}
        
        try:
            # Get Google search sources for the specific dish
            sources = self._get_sources_for_dish(dish_name, ingredients)
            
            return {
                "dish_name": dish_name,
                "ingredients": ingredients,
                "sources": sources
            }
            
        except Exception as e:
            return {"error": "details_failed", "msg": str(e)}
    
    def _get_enhanced_sources(self, hits: List[DishHit]) -> Dict[str, List[Dict[str, Any]]]:
        """Get enhanced sources for multiple dishes"""
        sources = {}
        
        if not self.google_api_key or not self.google_cse_id:
            print("Warning: Google API keys not configured. Enhanced recipe extraction disabled.")
            print("To enable enhanced recipe extraction, set GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables.")
            return {h.dish_name: [] for h in hits}
        
        try:
            from source_finder import SourceFinder
            from recipe_extractor import RecipeExtractor
            
            sf = SourceFinder()
            re = RecipeExtractor()
            
            for h in hits:
                try:
                    # Use enhanced search with fallback (reduced to 2 sources for speed)
                    srcs = sf.search_with_fallback(h.dish_name, h.ingredients, num=2)
                    
                    # Process sources with recipe extractor
                    enhanced_srcs = re.process_recipe_sources(srcs, h.dish_name, h.ingredients)
                    
                    sources[h.dish_name] = [{
                        "title": s.get("title", ""), 
                        "link": s.get("link", ""), 
                        "snippet": s.get("snippet", ""), 
                        "displayLink": s.get("displayLink", ""),
                        "directions": s.get("directions", []),
                        "content_preview": s.get("content_preview", ""),
                        "extraction_method": s.get("extraction_method", ""),
                        "recipe_info": s.get("recipe_info", {})
                    } for s in enhanced_srcs]
                    
                except Exception as e:
                    print(f"Warning: Failed to get sources for {h.dish_name}: {e}")
                    sources[h.dish_name] = []
                    
        except Exception as e:
            print(f"Warning: SourceFinder or RecipeExtractor not available: {e}")
            sources = {h.dish_name: [] for h in hits}
        
        return sources
    
    def _get_sources_for_dish(self, dish_name: str, ingredients: List[str]) -> List[Dict[str, Any]]:
        """Get sources for a specific dish"""
        if not self.google_api_key or not self.google_cse_id:
            return []
        
        try:
            from source_finder import SourceFinder
            from recipe_extractor import RecipeExtractor
            
            sf = SourceFinder()
            re = RecipeExtractor()
            
            # Use enhanced search with fallback
            srcs = sf.search_with_fallback(dish_name, ingredients, num=3)
            
            # Process sources with recipe extractor
            enhanced_srcs = re.process_recipe_sources(srcs, dish_name, ingredients)
            
            return [{
                "title": s.get("title", ""), 
                "link": s.get("link", ""), 
                "snippet": s.get("snippet", ""), 
                "displayLink": s.get("displayLink", ""),
                "directions": s.get("directions", []),
                "content_preview": s.get("content_preview", ""),
                "extraction_method": s.get("extraction_method", ""),
                "recipe_info": s.get("recipe_info", {})
            } for s in enhanced_srcs]
            
        except Exception as e:
            print(f"Warning: Failed to get sources for {dish_name}: {e}")
            return []
