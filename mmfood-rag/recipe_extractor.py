import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional, Tuple
import time
from urllib.parse import urlparse
import json
import logging

# For LLM integration
import os
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from google.genai import types
    from gemini_client import make_client, extract_text_from_response, first_json_block
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Gemini client not available. Recipe extraction will be limited.")

class RecipeExtractor:
    def __init__(self, project: Optional[str] = None, location: str = "us-central1", model: str = "gemini-2.0-flash-exp"):
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location
        self.model = model
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def fetch_recipe_content(self, url: str) -> Optional[Tuple[str, Dict]]:
        """Fetch and extract recipe content from a URL with enhanced parsing"""
        try:
            logger.info(f"Fetching content from: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                element.decompose()
            
            # Extract recipe content using multiple strategies
            recipe_data = self._extract_recipe_structured(soup)
            if recipe_data:
                return recipe_data
            
            # Fallback to content extraction
            content = self._extract_recipe_content_fallback(soup)
            return content, {}
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _extract_recipe_structured(self, soup: BeautifulSoup) -> Optional[Tuple[str, Dict]]:
        """Extract recipe content using structured data and common recipe patterns"""
        
        # Try JSON-LD structured data first
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            try:
                data = json.loads(json_ld.string)
                if isinstance(data, dict) and data.get('@type') in ['Recipe', 'HowTo']:
                    return self._parse_structured_recipe(data)
            except:
                pass
        
        # Try microdata
        recipe_item = soup.find(itemtype='http://schema.org/Recipe')
        if recipe_item:
            return self._parse_microdata_recipe(recipe_item)
        
        # Try common recipe selectors
        recipe_content = self._extract_by_selectors(soup)
        if recipe_content:
            return recipe_content, {}
        
        return None
    
    def _parse_structured_recipe(self, data: Dict) -> Tuple[str, Dict]:
        """Parse JSON-LD structured recipe data"""
        recipe_info = {}
        content_parts = []
        
        # Extract basic info
        if 'name' in data:
            recipe_info['title'] = data['name']
            content_parts.append(f"Recipe: {data['name']}")
        
        if 'description' in data:
            recipe_info['description'] = data['description']
            content_parts.append(f"Description: {data['description']}")
        
        # Extract ingredients
        ingredients = []
        if 'recipeIngredient' in data:
            ingredients = data['recipeIngredient'] if isinstance(data['recipeIngredient'], list) else [data['recipeIngredient']]
        elif 'ingredients' in data:
            ingredients = data['ingredients'] if isinstance(data['ingredients'], list) else [data['ingredients']]
        
        if ingredients:
            recipe_info['ingredients'] = ingredients
            content_parts.append("Ingredients:")
            content_parts.extend([f"- {ing}" for ing in ingredients])
        
        # Extract instructions
        instructions = []
        if 'recipeInstructions' in data:
            instructions = self._extract_instructions_from_structured(data['recipeInstructions'])
        elif 'instructions' in data:
            instructions = self._extract_instructions_from_structured(data['instructions'])
        
        if instructions:
            recipe_info['instructions'] = instructions
            content_parts.append("Instructions:")
            content_parts.extend([f"{i+1}. {step}" for i, step in enumerate(instructions)])
        
        # Extract cooking time, prep time, etc.
        if 'cookTime' in data:
            recipe_info['cook_time'] = data['cookTime']
        if 'prepTime' in data:
            recipe_info['prep_time'] = data['prepTime']
        if 'totalTime' in data:
            recipe_info['total_time'] = data['totalTime']
        
        return '\n\n'.join(content_parts), recipe_info
    
    def _extract_instructions_from_structured(self, instructions_data) -> List[str]:
        """Extract instructions from structured data"""
        instructions = []
        
        if isinstance(instructions_data, list):
            for item in instructions_data:
                if isinstance(item, dict):
                    if 'text' in item:
                        instructions.append(item['text'])
                    elif 'name' in item:
                        instructions.append(item['name'])
                elif isinstance(item, str):
                    instructions.append(item)
        elif isinstance(instructions_data, str):
            # Split by common delimiters
            for step in re.split(r'[.!?]\s+', instructions_data):
                if step.strip():
                    instructions.append(step.strip())
        
        return instructions
    
    def _parse_microdata_recipe(self, recipe_item) -> Tuple[str, Dict]:
        """Parse microdata recipe markup"""
        content_parts = []
        recipe_info = {}
        
        # Extract title
        title_elem = recipe_item.find(itemprop='name')
        if title_elem:
            recipe_info['title'] = title_elem.get_text().strip()
            content_parts.append(f"Recipe: {recipe_info['title']}")
        
        # Extract description
        desc_elem = recipe_item.find(itemprop='description')
        if desc_elem:
            recipe_info['description'] = desc_elem.get_text().strip()
            content_parts.append(f"Description: {recipe_info['description']}")
        
        # Extract ingredients
        ingredients = []
        for ing_elem in recipe_item.find_all(itemprop='recipeIngredient'):
            ingredients.append(ing_elem.get_text().strip())
        
        if ingredients:
            recipe_info['ingredients'] = ingredients
            content_parts.append("Ingredients:")
            content_parts.extend([f"- {ing}" for ing in ingredients])
        
        # Extract instructions
        instructions = []
        for inst_elem in recipe_item.find_all(itemprop='recipeInstructions'):
            instructions.append(inst_elem.get_text().strip())
        
        if instructions:
            recipe_info['instructions'] = instructions
            content_parts.append("Instructions:")
            content_parts.extend([f"{i+1}. {step}" for i, step in enumerate(instructions)])
        
        return '\n\n'.join(content_parts), recipe_info
    
    def _extract_by_selectors(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract recipe content using common CSS selectors"""
        recipe_selectors = [
            # Recipe-specific containers
            '[class*="recipe"]',
            '[class*="ingredient"]',
            '[class*="instruction"]',
            '[class*="direction"]',
            '[class*="step"]',
            '[class*="method"]',
            '[class*="preparation"]',
            '[class*="cooking"]',
            '[id*="recipe"]',
            '[id*="ingredient"]',
            '[id*="instruction"]',
            
            # Common recipe sites
            '.recipe-content',
            '.recipe-ingredients',
            '.recipe-instructions',
            '.recipe-directions',
            '.recipe-steps',
            '.ingredients-list',
            '.instructions-list',
            '.directions-list',
            '.steps-list',
            
            # Generic content areas
            'article',
            'main',
            '.content',
            '#content',
            '.post-content',
            '.entry-content'
        ]
        
        recipe_texts = []
        
        for selector in recipe_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text().strip()
                if len(text) > 100 and self._is_recipe_content(text):
                    recipe_texts.append(text)
        
        if recipe_texts:
            return '\n\n'.join(recipe_texts[:3])  # Use first 3 sections
        
        return None
    
    def _is_recipe_content(self, text: str) -> bool:
        """Check if text contains recipe-related content"""
        recipe_keywords = [
            'ingredient', 'instruction', 'direction', 'step', 'method',
            'preheat', 'oven', 'cook', 'bake', 'mix', 'stir', 'add',
            'cup', 'tablespoon', 'teaspoon', 'gram', 'ounce', 'pound',
            'minute', 'hour', 'temperature', 'degrees'
        ]
        
        text_lower = text.lower()
        keyword_count = sum(1 for keyword in recipe_keywords if keyword in text_lower)
        return keyword_count >= 3
    
    def _extract_recipe_content_fallback(self, soup: BeautifulSoup) -> str:
        """Fallback content extraction when structured data is not available"""
        # Remove navigation, ads, and other non-content elements
        for element in soup(['nav', 'header', 'footer', 'aside', 'script', 'style', 'iframe', 'form']):
            element.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text[:8000]  # Limit content length
    
    def extract_directions_with_llm(self, content: str, dish_name: str, ingredients: List[str], recipe_info: Dict = None) -> List[str]:
        """Use LLM to extract cooking directions from recipe content with enhanced prompting"""
        if not GEMINI_AVAILABLE:
            return []
        
        try:
            client = make_client(self.project, self.location)
            
            # Enhanced prompt with more context and better structure
            prompt = f"""
You are an expert recipe direction extractor. Extract cooking directions from the provided recipe content.

RECIPE CONTEXT:
- Dish Name: {dish_name}
- Ingredients: {', '.join(ingredients[:10])}  # Limit to first 10 ingredients
- Recipe Info: {json.dumps(recipe_info, indent=2) if recipe_info else 'None'}

RECIPE CONTENT:
{content[:8000]}

TASK: Extract ONLY the cooking directions/preparation steps as a numbered list.

REQUIREMENTS:
1. Return ONLY the directions in JSON format
2. Number each step sequentially (1, 2, 3, etc.)
3. Keep each step concise but complete
4. Include all essential cooking/preparation steps
5. Exclude ingredient lists, nutrition info, serving suggestions, or other non-direction content
6. If no clear directions found, return empty array

EXPECTED JSON FORMAT:
{{
  "directions": [
    "Step 1: [description]",
    "Step 2: [description]",
    "Step 3: [description]",
    ...
  ]
}}

EXAMPLES OF GOOD DIRECTIONS:
- "Preheat oven to 350°F (175°C)"
- "Mix flour, sugar, and salt in a large bowl"
- "Add eggs and milk, stir until combined"
- "Pour batter into greased pan"
- "Bake for 25-30 minutes until golden brown"

EXAMPLES OF WHAT TO EXCLUDE:
- Ingredient lists
- Nutrition information
- Serving suggestions
- Cooking tips (unless they're actual steps)
- Equipment lists
"""

            cfg = types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2048,
            )
            
            response = client.models.generate_content(
                model=self.model,
                contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
                config=cfg
            )
            
            raw_text = extract_text_from_response(response) or getattr(response, "text", "")
            data = first_json_block(raw_text)
            
            if data and "directions" in data:
                directions = data["directions"]
                # Clean up directions
                cleaned_directions = []
                for direction in directions:
                    # Remove step numbers if they're redundant
                    cleaned = re.sub(r'^Step \d+:\s*', '', direction.strip())
                    if cleaned:
                        cleaned_directions.append(cleaned)
                return cleaned_directions
            
            return []
            
        except Exception as e:
            logger.error(f"Error extracting directions with LLM: {e}")
            return []
    
    def extract_directions_simple(self, content: str) -> List[str]:
        """Enhanced simple regex-based direction extraction as fallback"""
        directions = []
        
        # Look for numbered steps with various patterns
        step_patterns = [
            r'\d+\.\s*([^.!?]+[.!?])',
            r'step\s+\d+[:\s]+([^.!?]+[.!?])',
            r'^\d+[:\s]+([^.!?]+[.!?])',
            r'\((\d+)\)\s*([^.!?]+[.!?])',
            r'(\d+)\)\s*([^.!?]+[.!?])',
        ]
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            for pattern in step_patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                if matches:
                    # Handle different match group structures
                    if isinstance(matches[0], tuple):
                        directions.extend([m[1] if len(m) > 1 else m[0] for m in matches])
                    else:
                        directions.extend(matches)
                    break
        
        # If no numbered steps found, look for bullet points
        if not directions:
            bullet_pattern = r'[•\-\*]\s*([^.!?]+[.!?])'
            for line in lines:
                matches = re.findall(bullet_pattern, line)
                if matches:
                    directions.extend(matches)
        
        # If still no directions, look for sentences that contain cooking verbs
        if not directions:
            cooking_verbs = [
                'preheat', 'bake', 'cook', 'mix', 'stir', 'add', 'combine', 'pour',
                'heat', 'boil', 'simmer', 'fry', 'saute', 'grill', 'roast', 'chop',
                'dice', 'mince', 'grate', 'whisk', 'beat', 'fold', 'knead', 'roll'
            ]
            
            sentences = re.split(r'[.!?]+', content)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20 and any(verb in sentence.lower() for verb in cooking_verbs):
                    directions.append(sentence)
        
        return directions[:15]  # Limit to 15 steps
    
    def process_recipe_sources(self, sources: List[Dict], dish_name: str, ingredients: List[str]) -> List[Dict]:
        """Process recipe sources and extract directions with enhanced error handling"""
        enhanced_sources = []
        
        for i, source in enumerate(sources[:1]):  # Process only top 1 source for speed
            url = source.get("link", "")
            if not url:
                continue
            
            logger.info(f"Processing recipe source {i+1}/1: {url}")
            
            try:
                # Fetch content
                content_result = self.fetch_recipe_content(url)
                if not content_result:
                    continue
                
                content, recipe_info = content_result
                
                # Extract directions using LLM first
                directions = []
                if GEMINI_AVAILABLE:
                    directions = self.extract_directions_with_llm(content, dish_name, ingredients, recipe_info)
                
                # Fallback to simple extraction
                if not directions:
                    directions = self.extract_directions_simple(content)
                
                enhanced_source = {
                    **source,
                    "directions": directions,
                    "content_preview": content[:300] + "..." if len(content) > 300 else content,
                    "recipe_info": recipe_info,
                    "extraction_method": "llm" if GEMINI_AVAILABLE and directions else "simple"
                }
                
                enhanced_sources.append(enhanced_source)
                
            except Exception as e:
                logger.error(f"Error processing source {url}: {e}")
                # Add source with error info
                enhanced_sources.append({
                    **source,
                    "directions": [],
                    "content_preview": f"Error extracting content: {str(e)}",
                    "recipe_info": {},
                    "extraction_method": "error"
                })
            
            # Rate limiting
            time.sleep(1)
        
        return enhanced_sources
