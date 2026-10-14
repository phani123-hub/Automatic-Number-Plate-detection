"""
User Repository
Handle user data operations with MongoDB
"""
from typing import Optional, Dict
from datetime import datetime
from bson import ObjectId
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.mongodb_client import mongodb_client
from auth.user_model import UserModel
from auth.password_utils import PasswordUtils


class UserRepository:
    """Repository for user data operations."""
    
    def __init__(self):
        self.collection = mongodb_client.users
    
    def create_user(self, username: str, email: str, password: str) -> Optional[str]:
        """
        Create a new user.
        
        Args:
            username: Username
            email: Email address
            password: Plain text password
            
        Returns:
            User ID if successful, None otherwise
        """
        # Validate inputs
        valid, msg = PasswordUtils.validate_username(username)
        if not valid:
            raise ValueError(msg)
        
        valid, msg = PasswordUtils.validate_email(email)
        if not valid:
            raise ValueError(msg)
        
        valid, msg = PasswordUtils.validate_password_strength(password)
        if not valid:
            raise ValueError(msg)
        
        # Check if user exists
        if self.find_by_username(username):
            raise ValueError("Username already exists")
        
        if self.find_by_email(email):
            raise ValueError("Email already exists")
        
        # Hash password
        password_hash = PasswordUtils.hash_password(password)
        
        # Create user
        user = UserModel(
            username=username,
            email=email,
            password_hash=password_hash,
            created_at=datetime.utcnow(),
        )
        
        try:
            result = self.collection.insert_one(user.to_dict())
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error creating user: {e}")
            raise
    
    def find_by_username(self, username: str) -> Optional[UserModel]:
        """Find user by username."""
        user_data = self.collection.find_one({'username': username})
        if user_data:
            return UserModel.from_dict(user_data)
        return None
    
    def find_by_email(self, email: str) -> Optional[UserModel]:
        """Find user by email."""
        user_data = self.collection.find_one({'email': email})
        if user_data:
            return UserModel.from_dict(user_data)
        return None
    
    def find_by_id(self, user_id: str) -> Optional[UserModel]:
        """Find user by ID."""
        try:
            user_data = self.collection.find_one({'_id': ObjectId(user_id)})
            if user_data:
                return UserModel.from_dict(user_data)
        except Exception as e:
            print(f"Error finding user by ID: {e}")
        return None
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """
        Authenticate user with username and password.
        
        Args:
            username: Username or email
            password: Plain text password
            
        Returns:
            User dict if authenticated, None otherwise
        """
        # Try username first, then email
        user = self.find_by_username(username)
        if not user:
            user = self.find_by_email(username)
        
        if not user:
            print(f"   → User '{username}' not found in database")
            return None
        
        print(f"   → User found: {user.username} (ID: {user._id})")
        print(f"   → Password hash in DB: {user.password_hash[:20]}...")
        
        # Verify password
        is_valid = PasswordUtils.verify_password(password, user.password_hash)
        print(f"   → Password verification result: {is_valid}")
        
        if not is_valid:
            return None
        
        # Update last login
        self.update_last_login(user._id)
        
        return {
            'user_id': user._id,
            'username': user.username,
            'email': user.email,
        }
    
    def update_last_login(self, user_id: str):
        """Update user's last login timestamp."""
        try:
            self.collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'last_login': datetime.utcnow()}}
            )
        except Exception as e:
            print(f"Error updating last login: {e}")
    
    def update_password(self, user_id: str, new_password: str) -> bool:
        """Update user password."""
        valid, msg = PasswordUtils.validate_password_strength(new_password)
        if not valid:
            raise ValueError(msg)
        
        password_hash = PasswordUtils.hash_password(new_password)
        
        try:
            result = self.collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'password_hash': password_hash}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating password: {e}")
            return False
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user (soft delete by setting is_active=False)."""
        try:
            result = self.collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'is_active': False}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
