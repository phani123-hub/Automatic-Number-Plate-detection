"""
Configuration Management
Loads environment variables and provides configuration access
"""
import os
from pathlib import Path
from dotenv import load_dotenv


def _env_bool(name: str, default: bool = False) -> bool:
    """Return boolean value for env var with sensible defaults."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Application configuration class."""
    
    # MongoDB Configuration
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'night_plate_detection')
    MONGODB_FALLBACK_URI = os.getenv('MONGODB_FALLBACK_URI', 'mongodb://localhost:27017/')
    MONGODB_ENABLE_FALLBACK = _env_bool('MONGODB_ENABLE_FALLBACK', True)
    MONGODB_USE_MOCK_ON_FAILURE = _env_bool('MONGODB_USE_MOCK_ON_FAILURE', False)
    MONGODB_FORCE_MOCK = _env_bool('MONGODB_FORCE_MOCK', False)
    
    # Collections
    USERS_COLLECTION = 'users'
    DETECTIONS_COLLECTION = 'detections'
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 24))
    
    # Security
    PASSWORD_MIN_LENGTH = int(os.getenv('PASSWORD_MIN_LENGTH', 8))
    
    # Application
    APP_NAME = os.getenv('APP_NAME', 'Night Plate Detection')
    APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
    
    @classmethod
    def validate(cls):
        """Validate critical configuration."""
        if '<db_password>' in cls.MONGODB_URI:
            raise ValueError("Please replace <db_password> in .env with your actual MongoDB password")
        
        if cls.JWT_SECRET_KEY == 'dev-secret-key-change-in-production':
            print("⚠️  WARNING: Using default JWT secret key. Change this in production!")
        
        return True


# Validate configuration on import
Config.validate()
