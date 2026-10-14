"""
Authentication Routes
Login, register, logout endpoints
"""
from flask import Blueprint, request, jsonify
import sys
from pathlib import Path
import uuid

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from auth.jwt_handler import JWTHandler
from database.user_repository import UserRepository
from auth.password_utils import PasswordUtils

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        data = request.get_json()
        
        if not data:
            return {'error': 'Request body is required'}, 400
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not all([username, email, password]):
            return {'error': 'Username, email, and password are required'}, 400
        
        user_repo = UserRepository()
        user_id = user_repo.create_user(username, email, password)
        
        return {
            'message': 'User registered successfully',
            'user_id': user_id,
            'username': username,
            'email': email
        }, 201
        
    except ValueError as e:
        return {'error': str(e)}, 400
    except Exception as e:
        return {'error': f'Registration failed: {str(e)}'}, 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user and return JWT token."""
    try:
        data = request.get_json()
        
        if not data:
            print("❌ Login failed: No request body")
            return {'error': 'Request body is required'}, 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        print(f"🔍 Login attempt for username: '{username}'")
        
        if not username or not password:
            print(f"❌ Login failed: Empty username or password")
            return {'error': 'Username and password are required'}, 400
        
        user_repo = UserRepository()
        user_data = user_repo.authenticate(username, password)
        
        if not user_data:
            print(f"❌ Authentication failed for user: '{username}'")
            # Check if user exists
            user = user_repo.find_by_username(username)
            if not user:
                user = user_repo.find_by_email(username)
                if not user:
                    print(f"   → User not found in database")
                else:
                    print(f"   → User found by email, password incorrect")
            else:
                print(f"   → User found by username, password incorrect")
            return {'error': 'Invalid username or password'}, 401
        
        # Generate JWT token
        token = JWTHandler.generate_token(
            user_id=user_data['user_id'],
            username=user_data['username'],
            email=user_data['email']
        )
        
        # Create session ID
        session_id = str(uuid.uuid4())
        
        print(f"✅ Login successful for user: '{username}'")
        
        return {
            'message': 'Login successful',
            'token': token,
            'user_id': user_data['user_id'],
            'username': user_data['username'],
            'email': user_data['email'],
            'session_id': session_id
        }, 200
        
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': f'Login failed: {str(e)}'}, 500


@auth_bp.route('/verify', methods=['POST'])
def verify_token():
    """Verify JWT token validity."""
    try:
        data = request.get_json()
        
        if not data or 'token' not in data:
            return {'error': 'Token is required'}, 400
        
        token = data.get('token')
        
        if JWTHandler.verify_token(token):
            user_info = JWTHandler.get_user_from_token(token)
            return {
                'message': 'Token is valid',
                'user': user_info
            }, 200
        else:
            return {'error': 'Token is invalid or expired'}, 401
            
    except Exception as e:
        return {'error': f'Token verification failed: {str(e)}'}, 500


@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change user password (requires authentication)."""
    try:
        # Extract token from header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return {'error': 'Authorization token required'}, 401
        
        user_info = JWTHandler.get_user_from_token(token)
        if not user_info:
            return {'error': 'Invalid or expired token'}, 401
        
        data = request.get_json()
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        
        if not old_password or not new_password:
            return {'error': 'Old and new passwords are required'}, 400
        
        user_repo = UserRepository()
        
        # Verify old password
        user = user_repo.find_by_id(user_info['user_id'])
        if not user or not PasswordUtils.verify_password(old_password, user.password_hash):
            return {'error': 'Current password is incorrect'}, 401
        
        # Update password
        if user_repo.update_password(user_info['user_id'], new_password):
            return {'message': 'Password changed successfully'}, 200
        else:
            return {'error': 'Failed to update password'}, 500
            
    except Exception as e:
        return {'error': f'Password change failed: {str(e)}'}, 500


@auth_bp.route('/user-info', methods=['GET'])
def get_user_info():
    """Get current user information."""
    try:
        # Extract token from header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return {'error': 'Authorization token required'}, 401
        
        user_info = JWTHandler.get_user_from_token(token)
        if not user_info:
            return {'error': 'Invalid or expired token'}, 401
        
        return {
            'user': user_info
        }, 200
        
    except Exception as e:
        return {'error': f'Failed to fetch user info: {str(e)}'}, 500
