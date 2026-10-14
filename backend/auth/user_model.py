"""
User Model
Define user data structure
"""
from datetime import datetime
from typing import Optional, Dict


class UserModel:
    """User data model."""
    
    def __init__(
        self,
        username: str,
        email: str,
        password_hash: str,
        _id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        last_login: Optional[datetime] = None,
        is_active: bool = True
    ):
        self._id = _id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at or datetime.utcnow()
        self.last_login = last_login
        self.is_active = is_active
    
    def to_dict(self) -> Dict:
        """Convert user to dictionary."""
        data = {
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'is_active': self.is_active,
        }
        if self._id:
            data['_id'] = self._id
        return data
    
    @staticmethod
    def from_dict(data: Dict) -> 'UserModel':
        """Create user from dictionary."""
        return UserModel(
            _id=str(data.get('_id', '')),
            username=data.get('username', ''),
            email=data.get('email', ''),
            password_hash=data.get('password_hash', ''),
            created_at=data.get('created_at'),
            last_login=data.get('last_login'),
            is_active=data.get('is_active', True),
        )
    
    def __repr__(self):
        return f"<User {self.username} ({self.email})>"
