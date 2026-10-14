"""
MongoDB Client
Manages MongoDB connection and database access
"""
from pymongo import MongoClient
from pymongo.errors import (
    ConnectionFailure,
    ServerSelectionTimeoutError,
    ConfigurationError,
)
from typing import Optional, Tuple
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config


class MongoDBClient:
    """MongoDB client singleton."""
    
    _instance: Optional['MongoDBClient'] = None
    _client: Optional[MongoClient] = None
    _db = None

    _CONNECT_EXCEPTIONS: Tuple[type, ...] = (
        ConnectionFailure,
        ServerSelectionTimeoutError,
        ConfigurationError,
    )
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize MongoDB connection (lazy - only connects when needed)."""
        # Don't connect immediately - let it connect on first use
        pass
    
    def _connect(self):
        """Establish MongoDB connection with fallback strategies."""
        if self._client is not None:
            return  # Already connected

        if Config.MONGODB_FORCE_MOCK:
            self._use_mock(reason="forced by configuration")
            return

        errors = []

        try:
            self._connect_with_uri(Config.MONGODB_URI, label="primary")
            return
        except self._CONNECT_EXCEPTIONS as exc:
            errors.append(f"Primary URI failed: {exc}")

        if (
            Config.MONGODB_ENABLE_FALLBACK
            and Config.MONGODB_FALLBACK_URI
            and Config.MONGODB_FALLBACK_URI != Config.MONGODB_URI
        ):
            try:
                self._connect_with_uri(Config.MONGODB_FALLBACK_URI, label="fallback")
                print("⚠️  Using fallback MongoDB URI")
                return
            except self._CONNECT_EXCEPTIONS as exc:
                errors.append(f"Fallback URI failed: {exc}")

        if Config.MONGODB_USE_MOCK_ON_FAILURE:
            try:
                self._use_mock(reason="connection fallback")
                return
            except ImportError as exc:
                errors.append(
                    "Mongomock fallback requested but module not installed. "
                    "Add 'mongomock' to requirements."
                )
                errors.append(str(exc))

        self._client = None
        self._db = None
        error_message = "\n - ".join(errors) if errors else "no diagnostics"
        raise RuntimeError(
            "Unable to connect to MongoDB. Errors encountered:\n - " + error_message
        )

    def _connect_with_uri(self, uri: str, label: str) -> None:
        """Connect to MongoDB using provided URI."""
        self._client = MongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
        )
        self._client.admin.command('ping')
        self._db = self._client[Config.MONGODB_DB_NAME]
        print(f"✓ Connected to MongoDB ({label}): {Config.MONGODB_DB_NAME}")

    def _use_mock(self, reason: str) -> None:
        """Use in-memory mongomock client when MongoDB is unavailable."""
        try:
            import mongomock
        except ImportError:
            raise

        self._client = mongomock.MongoClient()
        self._db = self._client[Config.MONGODB_DB_NAME]
        print(f"⚠️  Using in-memory MongoDB via mongomock ({reason}).")
    
    @property
    def db(self):
        """Get database instance."""
        if self._db is None:
            self._connect()
        return self._db
    
    @property
    def users(self):
        """Get users collection."""
        return self.db[Config.USERS_COLLECTION]
    
    @property
    def detections(self):
        """Get detections collection."""
        return self.db[Config.DETECTIONS_COLLECTION]
    
    def close(self):
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            print("✓ MongoDB connection closed")
    
    def test_connection(self) -> bool:
        """Test MongoDB connection."""
        try:
            self._client.admin.command('ping')
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def create_indexes(self):
        """Create database indexes for optimization."""
        try:
            # User indexes
            self.users.create_index('username', unique=True)
            self.users.create_index('email', unique=True)
            
            # Detection indexes
            self.detections.create_index('user_id')
            self.detections.create_index('timestamp')
            self.detections.create_index([('user_id', 1), ('timestamp', -1)])
            
            print("✓ Database indexes created")
        except Exception as e:
            print(f"Error creating indexes: {e}")


# Global instance getter function (lazy initialization)
_mongodb_client_instance: Optional[MongoDBClient] = None

def get_mongodb_client() -> MongoDBClient:
    """Get MongoDB client instance (lazy initialization)."""
    global _mongodb_client_instance
    if _mongodb_client_instance is None:
        _mongodb_client_instance = MongoDBClient()
    return _mongodb_client_instance


# Backward compatibility - but this won't connect until actually used
mongodb_client = get_mongodb_client()
