from flask import Flask
from flask_cors import CORS
from .config.settings import Config

def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    CORS(app)
    
    # Initialize the app (this will create the upload directory)
    config_class.init_app(app)
    
    # Register blueprints
    from .routes.analysis import analysis_bp
    from .routes.rag import rag_bp
    from .routes.health import health_bp
    
    app.register_blueprint(analysis_bp)
    app.register_blueprint(rag_bp)
    app.register_blueprint(health_bp)
    
    return app
