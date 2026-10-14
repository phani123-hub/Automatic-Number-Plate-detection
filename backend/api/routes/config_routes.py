"""
Configuration Routes
Get and update detection configuration
"""
from flask import Blueprint, request, jsonify
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from auth.jwt_handler import JWTHandler
from api.services.config_service import ConfigService

config_bp = Blueprint('config', __name__)
config_service = ConfigService()


def get_user_from_request():
    """Extract and validate user from request token."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return None, {'error': 'Authorization token required'}, 401
    
    user_info = JWTHandler.get_user_from_token(token)
    if not user_info:
        return None, {'error': 'Invalid or expired token'}, 401
    
    return user_info, None, None


@config_bp.route('/default', methods=['GET'])
def get_default_config():
    """Get default detection configuration."""
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        default_config = config_service.get_default_config()
        
        return {
            'message': 'Default configuration retrieved',
            'config': default_config
        }, 200
        
    except Exception as e:
        return {'error': f'Failed to fetch config: {str(e)}'}, 500


@config_bp.route('/validate', methods=['POST'])
def validate_config():
    """Validate detection configuration."""
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        data = request.get_json()
        if not data:
            return {'error': 'Configuration is required'}, 400
        
        is_valid, errors = config_service.validate_config(data)
        
        return {
            'message': 'Configuration validated',
            'is_valid': is_valid,
            'errors': errors
        }, 200
        
    except Exception as e:
        return {'error': f'Validation failed: {str(e)}'}, 500


@config_bp.route('/model-info', methods=['GET'])
def get_model_info():
    """Get information about available models."""
    try:
        user_info, error, status = get_user_from_request()
        if error:
            return error, status
        
        model_info = config_service.get_model_info()
        
        return {
            'message': 'Model information retrieved',
            'models': model_info
        }, 200
        
    except Exception as e:
        return {'error': f'Failed to fetch model info: {str(e)}'}, 500
