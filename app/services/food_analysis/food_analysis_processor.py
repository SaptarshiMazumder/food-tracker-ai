from typing import List, Dict, Any

from ..graphs import run_food_analysis
from .food_analysis_config import FoodAnalysisConfig


class FoodAnalysisProcessor:
    """Processes food analysis requests and coordinates the workflow"""
    
    def __init__(self, config: FoodAnalysisConfig):
        self.config = config
    
    def run_food_analysis(self, image_paths: List[str], model: str) -> Dict[str, Any]:
        """Run complete food analysis workflow"""
        try:
            res = run_food_analysis(image_paths, self.config.project, self.config.location, model)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[ERROR] Food analysis exception: {str(e)}")
            print(f"[ERROR] Full traceback: {error_details}")
            return {"error": "food_analysis_exception", "msg": str(e), "details": error_details}
        
        if res.get("error"):
            return {"error": res["error"], "dish": res.get("dish")}
        
        return res
