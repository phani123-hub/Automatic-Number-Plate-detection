"""
Detection Repository
Store and retrieve license plate detection results
"""
from typing import Optional, List, Dict
from datetime import datetime
from bson import ObjectId
import base64
import cv2
import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.mongodb_client import mongodb_client


class DetectionRepository:
    """Repository for detection results."""
    
    def __init__(self):
        self.collection = mongodb_client.detections
    
    def save_detection(
        self,
        user_id: str,
        username: str,
        plate_text: str,
        confidence: float,
        cropped_plate: np.ndarray,
        bbox: List[int],
        track_id: int,
        frame_number: int,
        is_valid: bool = False,
        session_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Save detection result to MongoDB.
        
        Args:
            user_id: User ID who performed detection
            username: Username
            plate_text: Detected plate text
            confidence: OCR confidence score
            cropped_plate: Cropped plate image (numpy array)
            bbox: Bounding box [x1, y1, x2, y2]
            track_id: Tracking ID
            frame_number: Frame number in video
            is_valid: Whether plate format is valid
            session_id: Optional session identifier
            
        Returns:
            Detection ID if successful
        """
        try:
            # Convert image to base64 with error handling
            crop_base64 = None
            if cropped_plate is not None and cropped_plate.size > 0:
                try:
                    _, buffer = cv2.imencode('.jpg', cropped_plate, [cv2.IMWRITE_JPEG_QUALITY, 90])
                    crop_base64 = base64.b64encode(buffer).decode('utf-8')
                except Exception as e:
                    print(f"Warning: Failed to encode crop image: {e}")
                    crop_base64 = None
            
            detection_doc = {
                'user_id': user_id,
                'username': username,
                'timestamp': datetime.utcnow(),
                'plate_text': plate_text,
                'confidence_score': float(confidence),
                'is_valid_indian': bool(is_valid),
                
                # Image data (base64 encoded)
                'crop': crop_base64,  # Clearer name for crop image
                'cropped_plate_image': crop_base64,  # Keep for backward compatibility
                
                # Vehicle/detection info
                'bbox': [int(x) for x in bbox] if bbox else None,  # Top-level for easier access
                'track_id': int(track_id),  # Top-level for easier access
                'frame_number': int(frame_number),  # Top-level for easier access
                
                # Legacy nested format (keep for backward compatibility)
                'vehicle_info': {
                    'bbox': [int(x) for x in bbox] if bbox else None,
                    'tracking_id': int(track_id),
                    'frame_number': int(frame_number),
                },
                
                'session_id': session_id or 'default',
            }
            
            result = self.collection.insert_one(detection_doc)
            print(f"✓ Saved detection: ID={result.inserted_id}, Plate={plate_text}, Conf={confidence:.2f}, Track={track_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            print(f"❌ Error saving detection: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def update_detection(
        self,
        detection_id: str,
        plate_text: str,
        confidence: float,
        cropped_plate: np.ndarray,
        bbox: List[int],
        frame_number: int,
        is_valid: bool = False
    ) -> bool:
        """
        Update an existing detection with better confidence data.
        
        Args:
            detection_id: ID of detection to update
            plate_text: Updated plate text
            confidence: Updated confidence score
            cropped_plate: Updated cropped plate image
            bbox: Updated bounding box [x1, y1, x2, y2]
            frame_number: New frame number
            is_valid: Updated validation status
            
        Returns:
            True if successful
        """
        try:
            # Convert image to base64 with error handling
            crop_base64 = None
            if cropped_plate is not None and cropped_plate.size > 0:
                try:
                    _, buffer = cv2.imencode('.jpg', cropped_plate, [cv2.IMWRITE_JPEG_QUALITY, 90])
                    crop_base64 = base64.b64encode(buffer).decode('utf-8')
                except Exception as e:
                    print(f"Warning: Failed to encode crop image: {e}")
            
            update_doc = {
                '$set': {
                    'plate_text': plate_text,
                    'confidence_score': float(confidence),
                    'is_valid_indian': bool(is_valid),
                    'timestamp': datetime.utcnow(),  # Update timestamp to latest
                }
            }
            
            # Add image fields if encoding was successful
            if crop_base64:
                update_doc['$set']['crop'] = crop_base64
                update_doc['$set']['cropped_plate_image'] = crop_base64
            
            # Add bbox and frame_number if provided
            if bbox:
                update_doc['$set']['bbox'] = [int(x) for x in bbox]
                update_doc['$set']['vehicle_info.bbox'] = [int(x) for x in bbox]
            
            if frame_number is not None:
                update_doc['$set']['frame_number'] = int(frame_number)
                update_doc['$set']['vehicle_info.frame_number'] = int(frame_number)
            
            result = self.collection.update_one(
                {'_id': ObjectId(detection_id)},
                update_doc
            )
            
            if result.modified_count > 0:
                print(f"✓ Updated detection: ID={detection_id}, Plate={plate_text}, Conf={confidence:.2f}")
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"❌ Error updating detection: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_user_detections(
        self,
        user_id: str,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict]:
        """Get detection history for a user."""
        try:
            cursor = self.collection.find(
                {'user_id': user_id}
            ).sort('timestamp', -1).skip(skip).limit(limit)
            
            detections = []
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                # Convert timestamp to ISO string for JSON serialization
                if 'timestamp' in doc and isinstance(doc['timestamp'], datetime):
                    doc['timestamp'] = doc['timestamp'].isoformat()
                detections.append(doc)
            
            return detections
            
        except Exception as e:
            print(f"Error fetching detections: {e}")
            return []
    
    def get_detection_by_id(self, detection_id: str) -> Optional[Dict]:
        """Get single detection by ID."""
        try:
            doc = self.collection.find_one({'_id': ObjectId(detection_id)})
            if doc:
                doc['_id'] = str(doc['_id'])
                # Convert timestamp to ISO string for JSON serialization
                if 'timestamp' in doc and isinstance(doc['timestamp'], datetime):
                    doc['timestamp'] = doc['timestamp'].isoformat()
                return doc
        except Exception as e:
            print(f"Error fetching detection: {e}")
        return None
    
    def get_session_detections(
        self,
        user_id: str,
        session_id: str
    ) -> List[Dict]:
        """Get all detections for a specific session."""
        try:
            cursor = self.collection.find({
                'user_id': user_id,
                'session_id': session_id
            }).sort('timestamp', 1)
            
            detections = []
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                # Convert timestamp to ISO string for JSON serialization
                if 'timestamp' in doc and isinstance(doc['timestamp'], datetime):
                    doc['timestamp'] = doc['timestamp'].isoformat()
                detections.append(doc)
            
            return detections
            
        except Exception as e:
            print(f"Error fetching session detections: {e}")
            return []
    
    def get_detection_stats(self, user_id: str) -> Dict:
        """Get detection statistics for user."""
        try:
            total = self.collection.count_documents({'user_id': user_id})
            valid = self.collection.count_documents({
                'user_id': user_id,
                'is_valid_indian': True
            })
            
            # Get unique plates
            unique_plates = self.collection.distinct('plate_text', {'user_id': user_id})
            
            return {
                'total_detections': total,
                'valid_detections': valid,
                'unique_plates': len(unique_plates),
                'success_rate': (valid / total * 100) if total > 0 else 0
            }
            
        except Exception as e:
            print(f"Error fetching stats: {e}")
            return {
                'total_detections': 0,
                'valid_detections': 0,
                'unique_plates': 0,
                'success_rate': 0
            }
    
    def delete_detection(self, detection_id: str, user_id: str) -> bool:
        """Delete a detection (must belong to user)."""
        try:
            result = self.collection.delete_one({
                '_id': ObjectId(detection_id),
                'user_id': user_id
            })
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting detection: {e}")
            return False
    
    def decode_image(self, image_base64: str) -> Optional[np.ndarray]:
        """Decode base64 image back to numpy array."""
        try:
            image_bytes = base64.b64decode(image_base64)
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return image
        except Exception as e:
            print(f"Error decoding image: {e}")
            return None
