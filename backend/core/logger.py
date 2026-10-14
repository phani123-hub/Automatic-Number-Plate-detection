"""
SQLite Logging Module for Detection Storage
Stores detection results with metadata for analysis
Author: AI Research Team
"""
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict
import json
from pathlib import Path
import threading
class DetectionLogger:
    """
    SQLite-based logging system for license plate detections.
    Stores detections with full metadata and supports querying.
    """
    def __init__(self, db_path: str = "data/sample_videos/logs.db"):
        """
        Initialize detection logger.
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread safety for write operations
        self._write_lock = threading.Lock()
        
        try:
            self.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            self.cursor = self.conn.cursor()
            
            # Set PRAGMA settings for better concurrency and performance
            self._set_pragma_settings()
            
            self._create_tables()
            print(f"✓ Logger initialized: {self.db_path}")
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to initialize database: {e}")
    
    def _set_pragma_settings(self):
        """Set SQLite PRAGMA settings for better concurrency and performance."""
        pragmas = [
            "PRAGMA journal_mode=WAL",  # Write-Ahead Logging for better concurrency
            "PRAGMA synchronous=NORMAL",  # Balance between safety and performance
            "PRAGMA busy_timeout=5000",  # 5 second timeout for locked database
            "PRAGMA cache_size=10000",  # Increase cache size for better performance
            "PRAGMA temp_store=MEMORY"  # Store temp tables in memory
        ]
        
        for pragma in pragmas:
            self.cursor.execute(pragma)
        self.conn.commit()
    def _create_tables(self):
        """Create database tables if they don't exist."""
        # Main detections table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            track_id INTEGER,
            plate_text TEXT,
            confidence REAL,
            is_valid_indian BOOLEAN,
            bbox_x1 INTEGER,
            bbox_y1 INTEGER,
            bbox_x2 INTEGER,
            bbox_y2 INTEGER,
            frame_number INTEGER,
            video_source TEXT,
            metadata TEXT
        )
        ''')
        # Create index on timestamp for faster queries
        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp
        ON detections(timestamp)
        ''')
        # Create index on track_id
        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_track_id
        ON detections(track_id)
        ''')
        # Create composite index for track_id + frame_number queries
        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_track_frame
        ON detections(track_id, frame_number)
        ''')
        # Create index on plate_text for GROUP BY operations
        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_plate_text
        ON detections(plate_text)
        ''')
        self.conn.commit()
        print("    Database tables and indexes ready")
    def log_detection(
        self,
        track_id: int,
        plate_text: str,
        confidence: float,
        bbox: List[int],
        frame_number: int,
        is_valid: bool = False,
        video_source: str = "",
        metadata: Optional[Dict] = None
    ):
        """
        Log a single detection to database.
        Args:
            track_id: Vehicle tracking ID
            plate_text: Detected plate text
            confidence: Detection confidence (0.0-1.0)
            bbox: Bounding box [x1, y1, x2, y2]
            frame_number: Frame number in video
            is_valid: Whether plate passes validation
            video_source: Source video file/stream
            metadata: Additional metadata dictionary
        """
        # Add input validation
        if not isinstance(track_id, int):
            raise ValueError("track_id must be an integer")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if len(bbox) != 4:
            raise ValueError("bbox must contain exactly 4 values")
        
        timestamp = datetime.now().isoformat()
        metadata_json = json.dumps(metadata, ensure_ascii=False, default=str) if metadata else "{}"
        
        # Thread-safe write operation
        with self._write_lock:
            try:
                self.cursor.execute('''
                INSERT INTO detections (
                    timestamp, track_id, plate_text, confidence,
                    is_valid_indian, bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                    frame_number, video_source, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timestamp,
                    track_id,
                    plate_text,
                    confidence,
                    is_valid,
                    bbox[0], bbox[1], bbox[2], bbox[3],
                    frame_number,
                    video_source,
                    metadata_json
                ))
                self.conn.commit()
            except Exception as e:
                print(f"Error logging detection: {e}")
                self.conn.rollback()
    def log_batch(self, detections: List[Dict]):
        """
        Log multiple detections at once (more efficient).
        Args:
            detections: List of detection dictionaries
        """
        timestamp = datetime.now().isoformat()
        data = []
        for det in detections:
            metadata_json = json.dumps(det.get('metadata', {}), ensure_ascii=False, default=str)
            bbox = det.get('bbox', [0, 0, 0, 0])
            data.append((
                timestamp,
                det.get('track_id', 0),
                det.get('plate_text', ''),
                det.get('confidence', 0.0),
                det.get('is_valid', False),
                bbox[0], bbox[1], bbox[2], bbox[3],
                det.get('frame_number', 0),
                det.get('video_source', ''),
                metadata_json
            ))
        
        # Thread-safe batch write operation
        with self._write_lock:
            try:
                self.cursor.executemany('''
                INSERT INTO detections (
                    timestamp, track_id, plate_text, confidence,
                    is_valid_indian, bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                    frame_number, video_source, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', data)
                self.conn.commit()
                print(f"Logged {len(detections)} detections")
            except Exception as e:
                print(f"Error logging batch: {e}")
                self.conn.rollback()
    def get_recent_detections(self, limit: int = 100) -> pd.DataFrame:
        """
        Get recent detections as DataFrame.
        Args:
            limit: Maximum number of records to return
        Returns:
            DataFrame with recent detections
        """
        # Validate limit parameter
        limit = max(1, min(int(limit), 10000))  # Clamp between 1 and 10000
        
        query = """
        SELECT * FROM detections
        ORDER BY id DESC
        LIMIT ?
        """
        df = pd.read_sql_query(query, self.conn, params=(limit,))
        return df
    def get_detections_by_track(self, track_id: int) -> pd.DataFrame:
        """
        Get all detections for a specific track.
        Args:
            track_id: Vehicle tracking ID
        Returns:
            DataFrame with track detections
        """
        query = """
        SELECT * FROM detections
        WHERE track_id = ?
        ORDER BY frame_number
        """
        df = pd.read_sql_query(query, self.conn, params=(track_id,))
        return df
    def get_unique_plates(self) -> pd.DataFrame:
        """
        Get unique plate texts with counts.
        Returns:
            DataFrame with unique plates and occurrence counts
        """
        query = """
        SELECT
            plate_text,
            COUNT(*) as count,
            AVG(confidence) as avg_confidence,
            MAX(timestamp) as last_seen
        FROM detections
        WHERE plate_text IS NOT NULL AND plate_text != ''
        GROUP BY plate_text
        ORDER BY count DESC
        """
        df = pd.read_sql_query(query, self.conn)
        return df
    def get_statistics(self) -> Dict:
        """
        Get overall logging statistics.
        Returns:
            Dictionary with statistics
        """
        stats = {}
        # Total detections
        self.cursor.execute("SELECT COUNT(*) FROM detections")
        stats['total_detections'] = self.cursor.fetchone()[0]
        # Unique tracks
        self.cursor.execute("SELECT COUNT(DISTINCT track_id) FROM detections")
        stats['unique_tracks'] = self.cursor.fetchone()[0]
        # Valid Indian plates
        self.cursor.execute(
            "SELECT COUNT(*) FROM detections WHERE is_valid_indian = 1"
        )
        stats['valid_indian_plates'] = self.cursor.fetchone()[0]
        # Average confidence
        self.cursor.execute("SELECT AVG(confidence) FROM detections")
        result = self.cursor.fetchone()[0]
        stats['avg_confidence'] = result if result else 0.0
        return stats
    def export_to_csv(self, csv_path: str = "data/detections.csv"):
        """
        Export all detections to CSV file.
        Args:
            csv_path: Output CSV file path
        """
        # Ensure parent directory exists
        csv_path_obj = Path(csv_path)
        csv_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        df = pd.read_sql_query("SELECT * FROM detections", self.conn)
        df.to_csv(csv_path, index=False)
        print(f"✓ Exported {len(df)} detections to {csv_path}")
    def clear_database(self):
        """Clear all detections from database."""
        # Thread-safe write operation
        with self._write_lock:
            try:
                self.cursor.execute("DELETE FROM detections")
                self.conn.commit()
                print("✓ Database cleared")
            except Exception as e:
                print(f"Error clearing database: {e}")
                self.conn.rollback()
    
    def vacuum_database(self):
        """
        Reclaim space by running VACUUM on the database.
        Note: This operation locks the database and should be run when offline.
        """
        try:
            print("Running VACUUM to reclaim space...")
            self.cursor.execute("VACUUM")
            self.conn.commit()
            print("✓ Database vacuumed successfully")
        except Exception as e:
            print(f"Error vacuuming database: {e}")
            self.conn.rollback()
    def close(self):
        """Close database connection."""
        self.conn.close()
        print("Database connection closed")
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
# Test the logger
if __name__ == "__main__":
    print("Testing DetectionLogger...")
    try:
        # Initialize logger
        logger = DetectionLogger(db_path="test_logs.db")
        # Test single detection
        logger.log_detection(
            track_id=1,
            plate_text="MH 12 AB 1234",
            confidence=0.95,
            bbox=[100, 100, 300, 150],
            frame_number=1,
            is_valid=True,
            video_source="test_video.mp4",
            metadata={'ocr_method': 'easyocr'}
        )
        print("✓ Logged single detection")
        # Test batch logging
        batch = [
            {
                'track_id': 2,
                'plate_text': "DL 01 CZ 9999",
                'confidence': 0.88,
                'bbox': [200, 200, 400, 250],
                'frame_number': 2,
                'is_valid': True
            },
            {
                'track_id': 3,
                'plate_text': "KA 05 MH 7890",
                'confidence': 0.92,
                'bbox': [300, 300, 500, 350],
                'frame_number': 3,
                'is_valid': True
            }
        ]
        logger.log_batch(batch)
        # Get statistics
        stats = logger.get_statistics()
        print(f"\nStatistics:")
        print(f" Total detections: {stats['total_detections']}")
        print(f" Unique tracks: {stats['unique_tracks']}")
        print(f" Valid plates: {stats['valid_indian_plates']}")
        print(f" Avg confidence: {stats['avg_confidence']:.2f}")
        # Export to CSV
        logger.export_to_csv("test_export.csv")
        # Close
        logger.close()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
