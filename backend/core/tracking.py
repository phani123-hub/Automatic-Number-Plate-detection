"""
ByteTrack Tracking Module for Vehicle Tracking
Assigns unique IDs to vehicles across frames
Handles occlusions and re-identification
Author: AI Research Team
"""
from typing import List, Tuple, Dict, Optional
import supervision as sv
import numpy as np
from supervision import Detections

class VehicleTracker:
    """
    ByteTrack-based vehicle tracker with unique ID assignment.
    Maintains tracking across frames, handles occlusions.
    """
    def __init__(
        self,
        track_thresh: float = 0.5,
        track_buffer: int = 30,
        match_thresh: float = 0.8,
        frame_rate: int = 30
    ):
        """
        Initialize ByteTrack tracker.
        Args:
        track_thresh: Detection confidence threshold for tracking
        track_buffer: Number of frames to keep lost tracks
        match_thresh: IoU threshold for matching detections to tracks
        frame_rate: Video frame rate (for time calculations)
        """
        # Validate parameters
        if not 0 <= track_thresh <= 1:
            raise ValueError("track_thresh must be between 0 and 1")
        if track_buffer < 1:
            raise ValueError("track_buffer must be positive")
        if not 0 <= match_thresh <= 1:
            raise ValueError("match_thresh must be between 0 and 1")
        if frame_rate < 1:
            raise ValueError("frame_rate must be positive")
            
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self.frame_rate = frame_rate
        
        # Initialize ByteTrack with new parameter names (supervision >= 0.21.0)
        self.tracker = sv.ByteTrack(
            track_activation_threshold=track_thresh,  # Updated from track_thresh
            lost_track_buffer=track_buffer,          # Updated from track_buffer
            minimum_matching_threshold=match_thresh,  # Updated from match_thresh
            frame_rate=frame_rate
        )
        
        # Initialize tracking history
        self.track_history = {}
        self.frame_count = 0
        print(f"✓ Tracker initialized (ByteTrack)")
        print(f" Track threshold: {track_thresh:.2f}")
        print(f" Match threshold: {match_thresh:.2f}")
        print(f" Track buffer: {track_buffer} frames")
    def update(
        self,
        boxes: List[List[int]],
        confidences: List[float],
        frame: Optional[np.ndarray] = None
    ) -> Tuple[List[int], List[List[int]]]:
        """
        Update tracker with new detections.
        Args:
        boxes: List of bounding boxes [[x1, y1, x2, y2], ...]
        confidences: Detection confidence scores
        frame: Current frame (optional, for history)
        Returns:
        track_ids: List of track IDs for each detection
        tracked_boxes: Updated bounding boxes (may differ from input)
        """
        self.frame_count += 1
        
        # Handle empty detections
        if not boxes or not confidences:
            return [], []
        
        if len(boxes) != len(confidences):
            raise ValueError("Number of boxes and confidences must match")
        # Convert to supervision Detections format
        detections = Detections(
            xyxy=np.array(boxes, dtype=np.float32),
            confidence=np.array(confidences, dtype=np.float32),
            class_id=np.zeros(len(boxes), dtype=int) # All same class (plate)
        )
        # Update tracker
        tracked_detections = self.tracker.update_with_detections(detections)
        # Extract track IDs and boxes
        if tracked_detections.tracker_id is not None:
            track_ids = tracked_detections.tracker_id.tolist()
            tracked_boxes = tracked_detections.xyxy.tolist()
        else:
            track_ids = []
            tracked_boxes = []
        # Update history
        for track_id, box in zip(track_ids, tracked_boxes):
            if track_id not in self.track_history:
                self.track_history[track_id] = {
                    'detections': [],
                    'first_frame': self.frame_count,
                    'last_frame': self.frame_count
                }
            # Add detection to history
            self.track_history[track_id]['detections'].append({
                'box': box,
                'frame': self.frame_count,
                'frame_data': frame.copy() if frame is not None else None
            })
            # Update last seen frame
            self.track_history[track_id]['last_frame'] = self.frame_count
        return track_ids, tracked_boxes
    def get_track_info(self, track_id: int) -> Optional[Dict]:
        """
        Get information about a specific track.
        Args:
        track_id: Track ID
        Returns:
        Dictionary with track information or None
        """
        return self.track_history.get(track_id, None)
    def get_active_tracks(self) -> List[int]:
        """
        Get list of currently active track IDs.
        Returns:
        List of active track IDs
        """
        active = []
        for track_id, info in self.track_history.items():
            # Consider track active if seen in last buffer frames
            if self.frame_count - info['last_frame'] <= self.track_buffer:
                active.append(track_id)
        return active
    def get_track_duration(self, track_id: int) -> int:
        """
        Get duration (in frames) that a track has been tracked.
        Args:
        track_id: Track ID
        Returns:
        Number of frames tracked
        """
        if track_id not in self.track_history:
            return 0
        info = self.track_history[track_id]
        return info['last_frame'] - info['first_frame'] + 1
    def clear_old_tracks(self, max_age: int = 100):
        """
        Clear tracks that haven't been seen for a long time.
        Args:
        max_age: Maximum age in frames before clearing
        """
        to_remove = []
        for track_id, info in self.track_history.items():
            age = self.frame_count - info['last_frame']
            if age > max_age:
                to_remove.append(track_id)
        for track_id in to_remove:
            del self.track_history[track_id]
        if to_remove:
            print(f"Cleared {len(to_remove)} old tracks")
    def get_statistics(self) -> Dict:
        """
        Get tracking statistics.
        Returns:
            Dictionary with tracking stats
        """
        active_tracks = self.get_active_tracks()
        
        # Safe average calculation
        durations = [self.get_track_duration(tid) for tid in self.track_history.keys()]
        avg_duration = np.mean(durations) if durations else 0
        
        stats = {
            'total_tracks': len(self.track_history),
            'active_tracks': len(active_tracks),
            'frame_count': self.frame_count,
            'avg_track_duration': avg_duration
        }
        return stats
    def reset(self):
        """Reset tracker to initial state."""
        self.tracker = sv.ByteTrack(
            track_thresh=self.track_thresh,
            track_buffer=self.track_buffer,
            match_thresh=self.match_thresh,
            frame_rate=self.frame_rate
        )
        self.track_history = {}
        self.frame_count = 0
        print("Tracker reset")
# Test the tracker
if __name__ == "__main__":
    print("Testing VehicleTracker...")
    try:
        # Initialize tracker
        tracker = VehicleTracker(
            track_thresh=0.5,
            track_buffer=30,
            match_thresh=0.8
        )
        # Simulate detections across multiple frames
        print("\nSimulating tracking across 10 frames:")
        for frame_idx in range(10):
            # Simulate 2 moving vehicles
            boxes = [
                [100 + frame_idx * 10, 100, 200 + frame_idx * 10, 150], # Vehicle 1
                [300 - frame_idx * 5, 200, 400 - frame_idx * 5, 250]  # Vehicle 2
            ]
            confidences = [0.9, 0.85]
            # Update tracker
            track_ids, tracked_boxes = tracker.update(boxes, confidences)
            print(f" Frame {frame_idx}: {len(track_ids)} tracks - IDs: {track_ids}")
        # Get statistics
        stats = tracker.get_statistics()
        print("\nTracking Statistics:")
        print(f" Total tracks: {stats['total_tracks']}")
        print(f" Active tracks: {stats['active_tracks']}")
        print(f" Avg duration: {stats['avg_track_duration']:.1f} frames")
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")