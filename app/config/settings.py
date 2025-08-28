import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# Also load .env from mmfood-rag directory
load_dotenv('./mmfood-rag/.env')

class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25MB per request
    
    # Upload settings
    UPLOAD_DIR = os.path.abspath(os.getenv("UPLOAD_DIR", "./uploads"))
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    
    # Google Cloud settings
    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
    GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
    
    # Model settings
    DEFAULT_MODEL = "gemini-2.5-pro"
    
    # RAG settings
    RAG_ARTIFACTS_DIR = "./mmfood-rag/artifacts"
    
    @staticmethod
    def init_app(app):
        """Initialize app with configuration"""
        # Create upload directory if it doesn't exist
        os.makedirs(Config.UPLOAD_DIR, exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    UPLOAD_DIR = "./test_uploads"

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
