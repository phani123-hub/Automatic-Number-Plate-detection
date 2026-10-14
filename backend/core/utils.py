# Placeholder for utils.py
"""
Utility Functions for License Plate Detection System
Helper functions for file I/O, video processing, visualization, etc.
"""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
import time
from datetime import datetime


class VideoWriter:
    """Video writer wrapper for saving processed videos."""
    def __init__(
        self,
        output_path: str,
        fps: int = 30,
        frame_size: Optional[Tuple[int, int]] = None,
        codec: str = 'mp4v'
    ):
        """Initialize video writer."""
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.fps = fps
        self.frame_size = frame_size
        self.codec = cv2.VideoWriter_fourcc(*codec)
        self.writer = None
        print(f"✓ Video writer initialized: {output_path}")

    def write(self, frame: np.ndarray) -> None:
        """Write a frame to video."""
        if self.writer is None:
            h, w = frame.shape[:2]
            if self.frame_size is None:
                self.frame_size = (w, h)
            self.writer = cv2.VideoWriter(
                str(self.output_path),
                self.codec,
                self.fps,
                self.frame_size
            )
        if frame.shape[:2][::-1] != self.frame_size:
            frame = cv2.resize(frame, self.frame_size)
        self.writer.write(frame)

    def release(self) -> None:
        """Release video writer."""
        if self.writer is not None:
            self.writer.release()
            print(f"✓ Video saved: {self.output_path}")


class FPSCounter:
    """FPS (Frames Per Second) counter for performance monitoring."""
    def __init__(self, window_size: int = 30):
        """Initialize FPS counter."""
        self.window_size = window_size
        self.frame_times = []
        self.last_time = time.time()

    def update(self) -> float:
        """Update FPS counter and return current FPS."""
        current_time = time.time()
        elapsed = current_time - self.last_time
        self.last_time = current_time
        self.frame_times.append(elapsed)
        if len(self.frame_times) > self.window_size:
            self.frame_times = self.frame_times[-self.window_size:]
        if len(self.frame_times) > 0:
            avg_time = np.mean(self.frame_times)
            fps = 1.0 / avg_time if avg_time > 0 else 0.0
        else:
            fps = 0.0
        return fps

    def reset(self) -> None:
        """Reset FPS counter."""
        self.frame_times = []
        self.last_time = time.time()


def draw_text_with_background(
    image: np.ndarray,
    text: str,
    position: Tuple[int, int],
    font_scale: float = 0.6,
    thickness: int = 1,
    text_color: Tuple[int, int, int] = (255, 255, 255),
    bg_color: Tuple[int, int, int] = (0, 0, 0),
    padding: int = 5
) -> np.ndarray:
    """Draw text with background rectangle."""
    x, y = position
    # Get text size
    (w, h), baseline = cv2.getTextSize(
        text,
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        thickness
    )
    # Draw background
    cv2.rectangle(
        image,
        (x - padding, y - h - padding),
        (x + w + padding, y + baseline + padding),
        bg_color,
        -1
    )
    # Draw text
    cv2.putText(
        image,
        text,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        text_color,
        thickness
    )
    return image


def calculate_iou(box1: List[int], box2: List[int]) -> float:
    """Calculate Intersection over Union (IoU) between two boxes."""
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2

    # Intersection
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)

    if x2_i < x1_i or y2_i < y1_i:
        return 0.0

    intersection_area = (x2_i - x1_i) * (y2_i - y1_i)

    # Union
    box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
    box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
    union_area = box1_area + box2_area - intersection_area

    iou = intersection_area / union_area if union_area > 0 else 0.0
    return iou


def get_video_info(video_path: str) -> dict:
    """Get video file information."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {}

    info = {
        'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        'fps': cap.get(cv2.CAP_PROP_FPS),
        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        'duration': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / cap.get(cv2.CAP_PROP_FPS)
    }
    cap.release()
    return info


def save_crop_image(
    crop: np.ndarray,
    output_dir: str,
    plate_text: str = "",
    track_id: int = 0,
    timestamp: Optional[str] = None
) -> str:
    """Save cropped plate image with metadata in filename."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    clean_text = plate_text.replace(' ', '_').replace('-', '_') if plate_text else "unknown"
    filename = f"plate_{clean_text}_track{track_id}_{timestamp}.jpg"
    filepath = output_path / filename
    cv2.imwrite(str(filepath), crop)
    return str(filepath)
