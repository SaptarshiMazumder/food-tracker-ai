from typing import List, Dict, Optional
import os, requests
from urllib.parse import urlencode
from dotenv import load_dotenv
import logging

load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

class SourceFinder:
    def __init__(self, api_key: Optional[str] = None, cse_id: Optional[str] = None):
        self.api_key = api_key or GOOGLE_API_KEY
        self.cse_id = cse_id or GOOGLE_CSE_ID
        if not self.api_key or not self.cse_id:
            raise RuntimeError("Google API key / CSE ID missing. Set GOOGLE_API_KEY and GOOGLE_CSE_ID.")

    def search(self, dish_name: str, ingredients: List[str], num: int = 5) -> List[Dict]:
        """Enhanced search with better recipe targeting"""
        
        # Create multiple search queries for better results
        queries = self._generate_search_queries(dish_name, ingredients)
        
        all_results = []
        
        for query in queries[:3]:  # Use top 3 queries
            try:
                results = self._execute_search(query, min(num, 3))
                all_results.extend(results)
                logger.info(f"Search query '{query}' returned {len(results)} results")
            except Exception as e:
                logger.error(f"Error executing search for query '{query}': {e}")
        
        # Deduplicate and rank results
        unique_results = self._deduplicate_results(all_results)
        
        # Sort by relevance (prioritize recipe sites)
        ranked_results = self._rank_results(unique_results, dish_name, ingredients)
        
        return ranked_results[:num]
    
    def _generate_search_queries(self, dish_name: str, ingredients: List[str]) -> List[str]:
        """Generate multiple search queries for better coverage"""
        queries = []
        
        # Clean dish name
        clean_dish = dish_name.lower().replace('recipe', '').replace('how to', '').strip()
        
        # Get top ingredients (limit to 3-4 most important ones)
        top_ingredients = ingredients[:4] if ingredients else []
        
        # Query 1: Basic recipe search
        if top_ingredients:
            ingredient_str = " ".join(top_ingredients[:3])
            queries.append(f'"{clean_dish}" recipe {ingredient_str}')
        else:
            queries.append(f'"{clean_dish}" recipe')
        
        # Query 2: How to make
        if top_ingredients:
            queries.append(f'how to make {clean_dish} with {ingredient_str}')
        else:
            queries.append(f'how to make {clean_dish}')
        
        # Query 3: Specific recipe sites
        recipe_sites = [
            'site:allrecipes.com',
            'site:foodnetwork.com', 
            'site:epicurious.com',
            'site:bonappetit.com',
            'site:seriouseats.com',
            'site:kingarthurbaking.com',
            'site:smittenkitchen.com',
            'site:thepioneerwoman.com',
            'site:simplyrecipes.com',
            'site:101cookbooks.com'
        ]
        
        for site in recipe_sites[:3]:  # Use top 3 sites
            if top_ingredients:
                queries.append(f'{site} "{clean_dish}" {ingredient_str}')
            else:
                queries.append(f'{site} "{clean_dish}"')
        
        # Query 4: Traditional cooking methods
        cooking_methods = ['baked', 'fried', 'grilled', 'roasted', 'steamed', 'braised']
        for method in cooking_methods[:2]:
            if top_ingredients:
                queries.append(f'{method} {clean_dish} recipe {ingredient_str}')
            else:
                queries.append(f'{method} {clean_dish} recipe')
        
        return queries
    
    def _execute_search(self, query: str, num: int) -> List[Dict]:
        """Execute a single Google search query"""
        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "num": min(num, 10),
            "safe": "active"
        }
        
        url = "https://www.googleapis.com/customsearch/v1?" + urlencode(params)
        
        logger.info(f"Making Google search request: {url}")
        
        try:
            resp = requests.get(url, timeout=15)
            logger.info(f"Google search response status: {resp.status_code}")
            
            if resp.status_code != 200:
                logger.error(f"Google search error: {resp.text}")
                return []
                
            resp.raise_for_status()
            data = resp.json()
            
            logger.info(f"Google search response: {data}")
            
            results = []
            for item in data.get("items", []):
                # Extract enhanced metadata
                metatags = item.get("pagemap", {}).get("metatags", [{}])[0] if item.get("pagemap", {}).get("metatags") else {}
                
                result = {
                    "title": item.get("title") or metatags.get("og:title", ""),
                    "link": item.get("link"),
                    "snippet": item.get("snippet") or metatags.get("og:description", ""),
                    "displayLink": item.get("displayLink"),
                    "query": query,  # Track which query found this result
                }
                
                # Only add if we have essential fields
                if result["title"] and result["link"]:
                    results.append(result)
            
            logger.info(f"Processed {len(results)} results from Google search")
            return results
            
        except Exception as e:
            logger.error(f"Search API error for query '{query}': {e}")
            return []
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate results based on URL"""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            url = result.get("link", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        return unique_results
    
    def _rank_results(self, results: List[Dict], dish_name: str, ingredients: List[str]) -> List[Dict]:
        """Rank results by relevance to recipe content"""
        
        def calculate_score(result: Dict) -> float:
            score = 0.0
            title = result.get("title", "").lower()
            snippet = result.get("snippet", "").lower()
            display_link = result.get("displayLink", "").lower()
            
            # Boost recipe-focused sites
            recipe_domains = [
                'allrecipes.com', 'foodnetwork.com', 'epicurious.com', 'bonappetit.com',
                'seriouseats.com', 'kingarthurbaking.com', 'smittenkitchen.com',
                'thepioneerwoman.com', 'simplyrecipes.com', '101cookbooks.com',
                'tasteofhome.com', 'bettycrocker.com', 'pillsbury.com', 'kraftrecipes.com'
            ]
            
            for domain in recipe_domains:
                if domain in display_link:
                    score += 10.0
                    break
            
            # Boost content that mentions recipe-related terms
            recipe_terms = ['recipe', 'ingredient', 'instruction', 'direction', 'step', 'method', 'preparation']
            for term in recipe_terms:
                if term in title:
                    score += 2.0
                if term in snippet:
                    score += 1.0
            
            # Boost content that mentions the dish name
            clean_dish = dish_name.lower()
            if clean_dish in title:
                score += 5.0
            if clean_dish in snippet:
                score += 3.0
            
            # Boost content that mentions ingredients
            for ingredient in ingredients[:5]:  # Check top 5 ingredients
                clean_ingredient = ingredient.lower()
                if clean_ingredient in title:
                    score += 1.0
                if clean_ingredient in snippet:
                    score += 0.5
            
            # Penalize very short snippets (likely not recipe content)
            if len(snippet) < 50:
                score -= 5.0
            
            # Penalize sites that are likely not recipe-focused
            non_recipe_domains = [
                'youtube.com', 'facebook.com', 'twitter.com', 'instagram.com',
                'pinterest.com', 'reddit.com', 'quora.com', 'wikipedia.org'
            ]
            
            for domain in non_recipe_domains:
                if domain in display_link:
                    score -= 5.0
                    break
            
            return score
        
        # Calculate scores and sort
        scored_results = [(result, calculate_score(result)) for result in results]
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        # Return results without scores
        return [result for result, score in scored_results]
    
    def search_with_fallback(self, dish_name: str, ingredients: List[str], num: int = 5) -> List[Dict]:
        """Search with fallback to broader queries if initial search fails"""
        results = self.search(dish_name, ingredients, num)
        
        # If we don't have enough results, try broader searches
        if len(results) < 2:
            logger.info(f"Initial search returned only {len(results)} results, trying broader search")
            
            # Try broader search without ingredients
            broader_results = self._execute_search(f'"{dish_name}" recipe', num)
            broader_results = self._deduplicate_results(broader_results)
            broader_results = self._rank_results(broader_results, dish_name, [])
            
            # Combine and deduplicate
            all_results = results + broader_results
            combined_results = self._deduplicate_results(all_results)
            combined_results = self._rank_results(combined_results, dish_name, ingredients)
            
            return combined_results[:num]
        
        return results