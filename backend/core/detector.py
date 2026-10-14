"""
YOLOv8x License Plate Detector Module
Uses PyTorch inference via Ultralytics
Optimized for nighttime vehicle plate detection
Author: AI Research Team
"""
import cv2
import numpy as np
import torch
from pathlib import Path
from typing import List, Tuple, Optional
class LicensePlateDetector:
    """
    YOLOv8x-based license plate detector with PyTorch inference.
    Detects license plates in images with configurable confidence and IoU thresholds.
    """
    def __init__(
        self,
        model_path: str = "models/yolov8x.pt",
        conf_threshold: float = 0.10,
        iou_threshold: float = 0.30,
        device: str = "cuda",
        multi_scale: bool = True,
        imgsz: int = 1280
    ):
        """
        Initialize the license plate detector.
        
        Args:
            model_path: Path to YOLOv8x model (.pt)
            conf_threshold: Confidence threshold for detections (0.0-1.0)
            iou_threshold: IoU threshold for NMS (0.0-1.0)
            device: Device to use ('cuda' or 'cpu')
            imgsz: YOLO inference image size (640/1280/1920) - industry tuning point
        """
        # Resolve model path relative to project root
        model_path_obj = Path(model_path)
        if not model_path_obj.is_absolute():
            # Find project root (directory containing core/ and models/)
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent
            model_path_obj = project_root / model_path
        
        self.model_path = model_path_obj
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.multi_scale = multi_scale
        self.imgsz = imgsz  # Industry tuning: YOLO inference size
        
        # Set device with CUDA availability check
        if device == "cuda":
            if torch.cuda.is_available():
                self.device = "cuda"
            else:
                print("⚠️ CUDA not available, falling back to CPU")
                self.device = "cpu"
        else:
            self.device = "cpu"
        
        # Load model
        self._load_model()
        print(f"✓ Detector initialized: {self.model_path.name}")
        print(f"  Device: {self.device}")
    def _load_model(self):
        """Load YOLOv8x PyTorch model.

        If the configured model file does not exist or fails to load, fall back to
        an official Ultralytics model (`yolov8n.pt`) which will be auto-downloaded
        by the ultralytics package. This makes the app more robust for first-time
        installs where the custom model hasn't been placed yet.
        """
        try:
            # Try loading the configured model file if it exists
            if self.model_path.exists():
                try:
                    self._load_pytorch_model()
                    return
                except Exception as e:
                    print(f"Warning: failed to load PyTorch model {self.model_path}: {e}")

            # Fallback: use a small official Ultralytics model that will be auto-downloaded
            try:
                print(f"Model file not found or failed to load: {self.model_path}. Falling back to 'yolov8n.pt' (will auto-download).")
                from ultralytics import YOLO
                self.model = YOLO('yolov8n.pt')
                # Update state to reflect fallback model
                self.model_path = Path('yolov8n.pt')
                # Move model to device if supported
                try:
                    self.model.to(self.device)
                except Exception:
                    pass
                print(f"✓ Loaded fallback model: yolov8n.pt")
                return
            except ImportError:
                raise ImportError("Ultralytics not installed. Run: pip install ultralytics")
            except Exception as e:
                raise RuntimeError(f"Failed to load fallback model: {e}")

        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")
    def _load_pytorch_model(self):
        """Load PyTorch YOLOv8x model using Ultralytics."""
        try:
            from ultralytics import YOLO
            self.model = YOLO(str(self.model_path))
            self.model.to(self.device)
            print(f"✓ Loaded PyTorch model: {self.model_path}")
        except ImportError:
            raise ImportError("Ultralytics not installed. Run: pip install ultralytics")
        except Exception as e:
            raise RuntimeError(f"Failed to load PyTorch model: {e}")
    
    def detect(
        self,
        frame: np.ndarray,
        return_crops: bool = True
    ) -> Tuple[List[List[int]], List[float], List[np.ndarray]]:
        """
        Detect license plates in a frame.
        
        Args:
            frame: Input image in BGR format (H, W, 3)
            return_crops: Whether to return cropped plate images
        
        Returns:
            boxes: List of bounding boxes [[x1, y1, x2, y2], ...]
            confidences: List of confidence scores [0.0-1.0] 
            crops: List of cropped plate images (if return_crops=True)
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return [], [], []
        
        try:
            return self._detect_pytorch(frame, return_crops)
        except Exception as e:
            print(f"Detection error: {e}")
            return [], [], []
    def _detect_pytorch(
        self,
        frame: np.ndarray,
        return_crops: bool
    ) -> Tuple[List[List[int]], List[float], List[np.ndarray]]:
        """
        PyTorch inference implementation using documented Boxes API.
        Optimized for nighttime-trained YOLOv8x model.
        Args:
            frame: Input BGR image
            return_crops: Whether to return cropped regions
        Returns:
            Tuple of (boxes, confidences, crops)
        """
        # Skip pre-enhancement for nighttime-trained model
        # Model is already trained on nighttime images - additional processing may degrade quality
        
        # Single-scale detection (multi-scale disabled for speed)
        # YOLOv8x is robust enough without multi-scale
        # Industry tuning: imgsz controls accuracy vs speed tradeoff
        results = self.model.predict(
            frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            imgsz=self.imgsz,  # 640=fast, 1280=balanced, 1920=accurate
            verbose=False
        )
        
        # Extract detections
        boxes = []
        confidences = []
        
        if len(results) > 0 and results[0].boxes is not None:
            det = results[0].boxes
            xyxy_coords = det.xyxy.cpu().numpy().astype(int)
            conf_scores = det.conf.cpu().numpy()
            
            h, w = frame.shape[:2]
            
            for xyxy, conf in zip(xyxy_coords, conf_scores):
                x1, y1, x2, y2 = xyxy
                
                # Ensure within bounds
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                
                if x2 > x1 and y2 > y1:
                    boxes.append([x1, y1, x2, y2])
                    confidences.append(float(conf))
        
        # Get frame dimensions
        h, w = frame.shape[:2]
        
        # Create crops with padding
        crops = []
        for box in boxes:
            if return_crops:
                x1, y1, x2, y2 = box
                
                # Add 10% padding on all sides to capture full plate text
                box_w = x2 - x1
                box_h = y2 - y1
                pad_x = int(box_w * 0.1)
                pad_y = int(box_h * 0.1)
                
                # Calculate padded coordinates
                crop_x1 = max(0, x1 - pad_x)
                crop_y1 = max(0, y1 - pad_y)
                crop_x2 = min(w, x2 + pad_x)
                crop_y2 = min(h, y2 + pad_y)
                
                crop = frame[crop_y1:crop_y2, crop_x1:crop_x2].copy()
                crops.append(crop)
        
        return boxes, confidences, crops
    
    def visualize_detections(
        self,
        frame: np.ndarray,
        boxes: List[List[int]],
        confidences: List[float],
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2
    ) -> np.ndarray:
        """
        Draw bounding boxes and labels on frame.
        Args:
            frame: Input image
            boxes: List of bounding boxes [[x1, y1, x2, y2], ...]
            confidences: List of confidence scores
            color: Box color in BGR format
            thickness: Line thickness
        Returns:
            Annotated frame with bounding boxes
        """
        annotated = frame.copy()
        
        # Validate inputs
        if not boxes or not confidences:
            return annotated
            
        for box, conf in zip(boxes, confidences):
            try:
                # Ensure box is a valid list/array with 4 elements
                if not hasattr(box, '__len__') or len(box) != 4:
                    print(f"Invalid box format: {box}")
                    continue
                
                # Convert to integers and unpack
                x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
                
                # Validate coordinates
                if x2 <= x1 or y2 <= y1:
                    print(f"Invalid box coordinates: [{x1}, {y1}, {x2}, {y2}]")
                    continue
                
                # Draw rectangle with validated integer coordinates
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)
                
                # Prepare label
                label = f"Plate: {conf:.2f}"
                
                # Get text size
                (w, h), _ = cv2.getTextSize(
                    label,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    1
                )
                
                # Clamp label position to avoid drawing outside image
                label_y_top = max(0, y1 - 20)
                label_y_bottom = max(20, y1)
                label_y_text = max(15, y1 - 5)
                
                # Draw label background
                cv2.rectangle(
                    annotated,
                    (x1, label_y_top),
                    (x1 + w, label_y_bottom),
                    color,
                    -1
                )
                
                # Draw label text
                cv2.putText(
                    annotated,
                    label,
                    (x1, label_y_text),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    1
                )
            except Exception as e:
                print(f"Visualization error for box {box}: {e}")
                continue
                
        return annotated
    def update_config(
        self,
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None
    ):
        """
        Update detection parameters dynamically.
        Args:
            conf_threshold: New confidence threshold (0.0-1.0)
            iou_threshold: New IoU threshold (0.0-1.0)
        """
        if conf_threshold is not None:
            if not 0 <= conf_threshold <= 1:
                raise ValueError("Confidence threshold must be between 0 and 1")
            self.conf_threshold = conf_threshold
            print(f"Updated confidence threshold: {conf_threshold}")
        
        if iou_threshold is not None:
            if not 0 <= iou_threshold <= 1:
                raise ValueError("IoU threshold must be between 0 and 1")
            self.iou_threshold = iou_threshold
            print(f"Updated IoU threshold: {iou_threshold}")
# Test the detector
if __name__ == "__main__":
    print("Testing LicensePlateDetector...")
    try:
        # Check if model file exists before initializing
        model_path = "models/yolov8x.pt"
        if not Path(model_path).exists():
            print(f"⚠️ Model file not found: {model_path}")
            print("Please ensure you have a valid YOLOv8x model file (.pt or .onnx)")
            print("You can download one from: https://github.com/ultralytics/ultralytics")
            exit(1)
        
        # Initialize detector
        detector = LicensePlateDetector(
            model_path=model_path,
            conf_threshold=0.5,
            device="cuda"
        )
        # Create test image
        test_img = np.zeros((640, 640, 3), dtype=np.uint8)
        cv2.putText(
            test_img,
            "Test Image",
            (200, 320),
            cv2.FONT_HERSHEY_SIMPLEX,
            2,
            (255, 255, 255),
            3
        )
        # Test detection
        boxes, confs, crops = detector.detect(test_img)
        print(f"✓ Detected {len(boxes)} plates")
        # Test visualization
        vis = detector.visualize_detections(test_img, boxes, confs)
        print(f"✓ Visualization complete: {vis.shape}")
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")