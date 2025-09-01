from flask import current_app


class FoodAnalysisConfig:
    """Configuration management for food analysis services"""
    
    def __init__(self):
        self.project = current_app.config['GOOGLE_CLOUD_PROJECT']
        self.location = current_app.config['GOOGLE_CLOUD_LOCATION']
        self.default_model = current_app.config['DEFAULT_MODEL']
        self.default_openai_model = current_app.config['DEFAULT_OPENAI_MODEL']
        self.ingredients_provider = current_app.config['INGREDIENTS_PROVIDER']
