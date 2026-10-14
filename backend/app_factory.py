"""
Flask Application Factory
Initialize and configure Flask app with blueprints
"""
from flask import Flask
from flask_cors import CORS
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from database.mongodb_client import mongodb_client


def create_app(config_class=Config):
    """Create and configure Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Enable CORS for React frontend
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://localhost:5000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })
    
    # Initialize MongoDB connection
    try:
        mongodb_client.create_indexes()
        app.logger.info("✓ MongoDB connected and indexes created")
    except Exception as e:
        app.logger.error(f"✗ MongoDB connection failed: {e}")
    
    # Register blueprints
    from api.routes.auth_routes import auth_bp
    from api.routes.detection_routes import detection_bp
    from api.routes.config_routes import config_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(detection_bp, url_prefix='/api/detection')
    app.register_blueprint(config_bp, url_prefix='/api/config')
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health():
        return {
            'status': 'healthy',
            'app': Config.APP_NAME,
            'version': Config.APP_VERSION
        }, 200
    
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Endpoint not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
