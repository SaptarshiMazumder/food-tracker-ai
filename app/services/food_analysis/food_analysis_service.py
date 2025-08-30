from typing import List, Dict, Any, Generator

from .food_analysis_config import FoodAnalysisConfig
from .food_analysis_formatter import FoodAnalysisFormatter
from .food_analysis_processor import FoodAnalysisProcessor
from .food_analysis_streamer import FoodAnalysisStreamer


class FoodAnalysisService:
    """Main service for handling food analysis operations - follows SRP by delegating to specialized classes"""
    
    def __init__(self):
        self.config = FoodAnalysisConfig()
        self.processor = FoodAnalysisProcessor(self.config)
        self.streamer = FoodAnalysisStreamer(self.config)
    
    def run_food_analysis(self, image_paths: List[str], model: str) -> Dict[str, Any]:
        """Run complete food analysis workflow"""
        return self.processor.run_food_analysis(image_paths, model)
    
    def finalize_payload(self, res: Dict[str, Any], save_paths: List[str]) -> Dict[str, Any]:
        """Convert raw analysis result to final API payload"""
        return FoodAnalysisFormatter.create_final_payload(res, save_paths)
    
    def stream_analysis(self, image_paths: List[str], model: str) -> Generator[str, None, None]:
        """Stream analysis results via SSE"""
        yield from self.streamer.stream_analysis(image_paths, model)
