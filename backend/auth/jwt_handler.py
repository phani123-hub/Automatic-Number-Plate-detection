"""
JWT Token Handler
Generate and validate JWT tokens for authentication
"""
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config


class JWTHandler:
    """Handle JWT token generation and validation."""
    
    @staticmethod
    def generate_token(user_id: str, username: str, email: str) -> str:
        """
        Generate JWT token for authenticated user.
        
        Args:
            user_id: User's MongoDB ObjectId as string
            username: Username
            email: User email
            
        Returns:
            JWT token string
        """
        expiration = datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS)
        
        payload = {
            'user_id': user_id,
            'username': username,
            'email': email,
            'exp': expiration,
            'iat': datetime.utcnow(),
        }
        
        token = jwt.encode(
            payload,
            Config.JWT_SECRET_KEY,
            algorithm=Config.JWT_ALGORITHM
        )
        
        return token
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict]:
        """
        Decode and validate JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded payload dict if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                Config.JWT_SECRET_KEY,
                algorithms=[Config.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            print("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            print(f"Invalid token: {e}")
            return None
    
    @staticmethod
    def verify_token(token: str) -> bool:
        """
        Verify if token is valid.
        
        Args:
            token: JWT token string
            
        Returns:
            True if valid, False otherwise
        """
        payload = JWTHandler.decode_token(token)
        return payload is not None
    
    @staticmethod
    def get_user_from_token(token: str) -> Optional[Dict]:
        """
        Extract user information from token.
        
        Args:
            token: JWT token string
            
        Returns:
            User info dict or None
        """
        payload = JWTHandler.decode_token(token)
        if payload:
            return {
                'user_id': payload.get('user_id'),
                'username': payload.get('username'),
                'email': payload.get('email'),
            }
        return None
