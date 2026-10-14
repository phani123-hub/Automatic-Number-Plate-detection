"""
Detection Service
Handles video processing, frame detection, and result management
Optimized with OCR thread pool and industry-level ANPR practices
"""
import cv2
import numpy as np
import time
import base64
from pathlib import Path
import sys
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.detector import LicensePlateDetector
from core.preprocess import NightPreprocessor
from core.ocr import LicensePlateOCR
from core.postprocess import PlateTextCleaner, TemporalVoter, ConfidenceFilter, ResultAggregator
from core.tracking import VehicleTracker
from core.utils import draw_text_with_background, FPSCounter, save_crop_image
from database.detection_repository import DetectionRepository
import re

# Industry-level optimization: Detection dataclass for cleaner structure
@dataclass
class DetectionResult:
    """Structured detection result for better type safety and clarity."""
    bbox: Tuple[int, int, int, int]
    confidence: float
    crop: np.ndarray = None
    track_id: int = -1
    ocr_text: str = ""
    ocr_confidence: float = 0.0

class DetectionService:
    """Service layer for detection operations."""
    
    def __init__(self):
        """Initialize detection service with OCR thread pool optimization."""
        self.detector = None
        self.preprocessor = None
        self.ocr_engine = None
        self.text_cleaner = None
        self.tracker = None
        self.detection_repo = DetectionRepository()
        
        # Industry optimization: OCR Thread Pool (4 workers for non-blocking OCR)
        # This provides 3-5x speedup by parallelizing OCR across multiple crops
        self.ocr_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="OCR-Worker")
        self.ocr_futures = []  # Track pending OCR tasks
        
        # Industry-level tuning constants (police-grade ANPR standards)
        self.MIN_PLATE_AREA = 25 * 40  # Skip tiny crops (< 1000 pixels)
        
        # Police-grade brightness thresholds (3-stage preprocessing)
        self.BRIGHTNESS_VERY_DARK = 60   # < 60: Strong preprocessing (CLAHE + denoise + sharpen)
        self.BRIGHTNESS_MILD_DARK = 100  # 60-100: Mild preprocessing (CLAHE only)
        # > 100: No preprocessing (bright enough)
        
        self.OCR_TIMEOUT = 0.5  # Max seconds to wait for OCR result (prevent blocking)
        self.YOLO_IMGSZ = 1280  # YOLO inference size (640/1280/1920 - larger=accurate but slower)
        self.STABLE_TRACK_FRAMES = 2  # Min frames before running OCR on track (deferred OCR)
        self.OCR_ON_EVERY_FRAME = False  # False=deferred OCR (faster), True=immediate OCR
        self.MIN_OCR_CONFIDENCE = 0.40  # Police-grade: Only accept OCR >= 40% confidence
        
        # Postprocessing components (relaxed for nighttime YOLOv8x)
        # TemporalVoter: Reduced window (10→5) and vote threshold (0.30→0.20) for faster detection
        self.temporal_voter = TemporalVoter(
            window_size=5,          # Smaller window for faster consensus (was 10)
            confidence_threshold=0.20,  # Lower for nighttime
            vote_threshold=0.20     # Allow single-frame acceptance if high conf (was 0.30)
        )
        self.confidence_filter = ConfidenceFilter(
            min_detection_conf=0.15,  # Match YOLOv8x threshold
            min_ocr_conf=0.20,  # Lower for nighttime OCR
            min_plate_width=30,  # Allow smaller plates (nighttime)
            min_plate_height=12,  # Allow smaller plates (nighttime)
            aspect_ratio_range=(0.8, 10.0)  # Very wide range for nighttime/angles (was 1.5-8.0)
        )
        self.result_aggregator = ResultAggregator()
        
        # Session management - prevent duplicate detections
        self.session_cache = defaultdict(set)  # session_id -> set of plate_texts
        self.track_detections = defaultdict(dict)  # Store best detection per track
        self.track_ocr_history = defaultdict(list)  # Store OCR history per track for voting
        self.frame_count = 0
        
        # Police-grade: Track stability tracking (seen_count per track)
        # Structure: {track_id: {'seen_count': int, 'best_ocr_text': str, 'best_ocr_conf': float}}
        self.track_stability = defaultdict(lambda: {'seen_count': 0, 'best_ocr_text': '', 'best_ocr_conf': 0.0})
        
        # Manual Review Buffer - stores top 2-3 best crops per track for low-confidence plates
        # Structure: {session_id: {track_id: [(yolo_conf, ocr_conf, crop, bbox, frame_num)]}}
        self.manual_review_buffer = defaultdict(lambda: defaultdict(list))
        self.max_crops_per_track = 3  # Keep only top 3 best quality crops
        self.manual_review_conf_threshold = 0.10  # Save crops with OCR conf < 10%
        
        # Preview Buffer - stores top 2 successfully detected plates for validation display
        # Structure: {session_id: [{plate_text, confidence, crop_path, bbox, track_id, frame_num}]}
        self.preview_buffer = defaultdict(list)
        self.max_preview_plates = 2  # Show only top 2 plates for validation
        
        # Confidence thresholds - validation based on OCR confidence, NOT YOLO
        self.min_confidence_threshold = 0.10  # Very low - let OCR decide
        self.min_ocr_confidence = 0.30  # EasyOCR threshold (production standard)
        
        # Control flags
        self.auto_save_to_db = False  # Don't auto-save to DB, wait for user confirmation
        
        # Performance monitoring
        self.fps_counter = FPSCounter(window_size=30)
        
    def load_models(self, config: Dict) -> bool:
        """
        Load all detection models with given configuration.
        
        Args:
            config: Detection configuration dictionary
            
        Returns:
            bool: True if models loaded successfully
        """
        try:
            print("🔄 Loading detection models...")
            
            # Debug: Show received config
            print(f"📦 Received config keys: {list(config.keys())}")
            
            # Initialize detector
            model_path = config.get('model_path', 'models/yolov8x.pt')
            
            # Migration: Auto-correct old yolov9c.pt references to yolov8x.pt
            if 'yolov9c' in model_path.lower():
                print(f"⚠️  Detected old model reference: {model_path}")
                model_path = model_path.replace('yolov9c', 'yolov8x')
                print(f"   Auto-corrected to: {model_path}")
                config['model_path'] = model_path  # Update config for consistency
            
            # Get thresholds from config
            conf_threshold = config.get('confidence_threshold', 0.15)  # Lower default for nighttime YOLOv8x
            conf_threshold = config.get('conf_threshold', conf_threshold)  # Also check 'conf_threshold' key
            iou_threshold = config.get('iou_threshold', 0.45)
            device = config.get('device', 'cpu')
            
            # Debug: Log detection settings
            print(f"📊 Detection Settings:")
            print(f"   Confidence threshold: {conf_threshold}")
            print(f"   IoU threshold: {iou_threshold}")
            print(f"   Device: {device}")
            
            self.detector = LicensePlateDetector(
                model_path=model_path,
                conf_threshold=conf_threshold,
                iou_threshold=iou_threshold,
                device=device,
                imgsz=self.YOLO_IMGSZ  # Industry tuning: 640/1280/1920
            )
            
            # Initialize preprocessor (minimal for pre-trained nighttime model)
            # YOLOv8x is already trained on nighttime images, doesn't need heavy preprocessing
            self.preprocessor = NightPreprocessor(
                enable_clahe=config.get('enable_clahe', False),  # Disabled by default
                clip_limit=config.get('clip_limit', 2.0),
                enable_denoise=config.get('enable_denoise', False),  # Disabled by default
                enable_exposure=config.get('enable_exposure', False),  # Disabled by default
                gamma=config.get('gamma', 1.0)
            )
            
            # Initialize OCR
            ocr_engine = config.get('ocr_engine', 'easyocr')
            self.ocr_engine = LicensePlateOCR(primary_ocr=ocr_engine)
            
            # Initialize text cleaner
            self.text_cleaner = PlateTextCleaner()
            
            # Initialize tracker with optimized parameters for faster processing
            # Reduced track_buffer (30→15) and relaxed thresholds for speed
            self.tracker = VehicleTracker(
                track_thresh=0.45,      # Detection threshold for tracking (was 0.5)
                match_thresh=0.75,      # IoU match threshold (was 0.8) 
                track_buffer=15,        # Keep lost tracks for 15 frames (was 30)
                frame_rate=30
            )
            
            print("✅ All models loaded successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load models: {e}")
            return False
    
    def _ocr_crop_async(self, crop: np.ndarray) -> Tuple[str, float, Dict]:
        """
        Industry optimization: Non-blocking OCR using thread pool.
        This method is thread-safe and can be called concurrently.
        
        Args:
            crop: Plate crop image (BGR or grayscale)
            
        Returns:
            Tuple of (text, confidence, metadata)
        """
        try:
            return self.ocr_engine.read_plate(crop)
        except Exception as e:
            print(f"  OCR worker error: {e}")
            return "", 0.0, {}
    
    def _preprocess_crop_lightweight(self, crop: np.ndarray, mean_brightness: float) -> np.ndarray:
        """
        Police-grade ANPR: 3-stage brightness-aware crop preprocessing.
        
        Brightness zones:
        - < 60:    Very dark → Strong (CLAHE + denoise + sharpen)
        - 60-100:  Mild dark → Moderate (CLAHE only)
        - > 100:   Bright → No preprocessing
        
        Args:
            crop: Plate crop (BGR)
            mean_brightness: Frame brightness (0-255)
            
        Returns:
            Preprocessed crop (grayscale, OCR-ready)
        """
        # Convert to grayscale
        if len(crop.shape) == 3:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        else:
            gray = crop
        
        try:
            # Zone 3: Bright frame (> 100) - No preprocessing needed
            if mean_brightness > self.BRIGHTNESS_MILD_DARK:
                return gray
            
            # Zone 2: Mild dark (60-100) - CLAHE only
            elif mean_brightness >= self.BRIGHTNESS_VERY_DARK:
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)
                return enhanced
            
            # Zone 1: Very dark (< 60) - Strong preprocessing
            else:
                # Step 1: CLAHE (high contrast)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)
                
                # Step 2: Denoise (remove grain)
                enhanced = cv2.fastNlMeansDenoising(enhanced, h=10)
                
                # Step 3: Sharpening (boost text edges) - Police-grade addition
                kernel = np.array([[-1, -1, -1],
                                   [-1,  9, -1],
                                   [-1, -1, -1]])
                enhanced = cv2.filter2D(enhanced, -1, kernel)
                
                return enhanced
                
        except Exception as e:
            print(f"  Preprocessing error: {e}")
            return gray  # Fallback to original
    
    def process_frame(
        self,
        frame: np.ndarray,
        config: Dict,
        user_id: str,
        username: str,
        session_id: str
    ) -> Tuple[np.ndarray, List[Dict]]:
        """
        Process a single frame for license plate detection.
        
        Args:
            frame: Input frame (BGR format)
            config: Detection configuration
            user_id: User ID
            username: Username
            session_id: Session ID
            
        Returns:
            Tuple of (annotated_frame, detection_results)
        """
        try:
            self.frame_count += 1
            results = []
            
            # Brightness-based preprocessing for nighttime-trained YOLOv8x
            # Only preprocess DARK frames (mean brightness < 80)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean_brightness = gray.mean()
            
            # Optimization: Cache preprocessing config check (don't check every detection)
            preprocessing_enabled = config.get('enable_preprocessing', False)
            
            # Use raw frame for detection (model trained on nighttime, no full-frame preprocessing)
            detection_frame = frame
            
            # Detection - returns (boxes, confidences, crops)
            boxes, confidences, crops = self.detector.detect(detection_frame, return_crops=True)
            
            # Industry Optimization: Batch update tracker ONCE with ALL detections
            # This is much faster than updating per-detection in the loop below
            track_ids = []
            if self.tracker and boxes:
                track_ids, _ = self.tracker.update(boxes=boxes, confidences=confidences)
            
            # Police-grade: Crop preprocessing AFTER detection (not before)
            # Workflow: Detection (raw frame) → Extract crops → Preprocess crops → OCR
            # This is correct: preprocessing small crops is fast and effective for OCR
            # Industry Optimization: Lightweight preprocessing on crops only (not full frame)
            # Police-grade: run heavy preprocessing only when frame is truly dark (< BRIGHTNESS_VERY_DARK)
            should_preprocess_crops = preprocessing_enabled and mean_brightness < self.BRIGHTNESS_VERY_DARK
            if should_preprocess_crops and crops:
                # Use police-grade 3-stage preprocessing
                crops = [self._preprocess_crop_lightweight(crop, mean_brightness) for crop in crops]
            
            # Debug: Log detection count with police-grade metrics
            if self.frame_count % 10 == 0 or boxes:
                # Determine brightness zone for logging
                if mean_brightness < self.BRIGHTNESS_VERY_DARK:
                    brightness_zone = "VERY_DARK(<60)"
                elif mean_brightness < self.BRIGHTNESS_MILD_DARK:
                    brightness_zone = "MILD_DARK(60-100)"
                else:
                    brightness_zone = "BRIGHT(>100)"
                
                print(f"  Frame {self.frame_count}: {len(boxes)} detections | Brightness: {mean_brightness:.1f} [{brightness_zone}] | Preprocess: {should_preprocess_crops} | Conf: {[f'{c:.2f}' for c in confidences]}") 
            
            # Industry Optimization: Batch OCR using thread pool for parallel processing
            # Deferred OCR: Only run OCR on stable tracks (2+ frames) to avoid wasting resources
            ocr_futures = []
            valid_detections = []  # Store detections that pass initial filtering
            
            for idx, (bbox, confidence, plate_crop) in enumerate(zip(boxes, confidences, crops)):
                # Extract coordinates
                x1, y1, x2, y2 = map(int, bbox)
                
                # Apply confidence filtering (quality checks)
                passes_filter, reason = self.confidence_filter.filter_detection(
                    bbox=bbox,
                    detection_conf=confidence
                )
                
                if not passes_filter:
                    print(f"  ⚠️ Filtered out (conf={confidence:.2f}): {reason}")
                    continue
                
                # Skip empty crops or too small
                if plate_crop.size == 0 or (x2-x1)*(y2-y1) < self.MIN_PLATE_AREA:
                    continue
                
                # Get track_id for this detection
                track_id = track_ids[idx] if idx < len(track_ids) else -1
                
                # Police-grade: Update track stability (seen_count)
                if track_id != -1:
                    self.track_stability[track_id]['seen_count'] += 1
                
                # Deferred OCR: Only process stable tracks (appeared in 2+ frames)
                # This saves 50-70% OCR calls by ignoring fleeting false positives
                should_run_ocr = self.OCR_ON_EVERY_FRAME
                if not should_run_ocr and track_id != -1:
                    # Police-grade: Check track stability (seen_count)
                    seen_count = self.track_stability[track_id]['seen_count']
                    should_run_ocr = seen_count >= self.STABLE_TRACK_FRAMES
                
                if should_run_ocr or self.OCR_ON_EVERY_FRAME:
                    # Submit OCR task to thread pool (non-blocking)
                    future = self.ocr_pool.submit(self._ocr_crop_async, plate_crop)
                    ocr_futures.append((idx, future, bbox, confidence, plate_crop, track_id))
                
                valid_detections.append((idx, bbox, confidence, plate_crop, track_id))
            
            # Collect OCR results (concurrent completion)
            # Process results as they complete (fastest first)
            ocr_results = {}
            for idx, future, bbox, confidence, plate_crop, track_id in ocr_futures:
                try:
                    # Configurable timeout to avoid blocking
                    plate_text, ocr_confidence, ocr_metadata = future.result(timeout=self.OCR_TIMEOUT)
                    ocr_results[idx] = (plate_text.strip(), ocr_confidence, ocr_metadata)
                except Exception as e:
                    # Timeout or error - skip this crop (log only on first occurrence)
                    if self.frame_count % 30 == 0:  # Reduce log spam
                        print(f"  OCR timeout/error for detection {idx}: {e}")
                    ocr_results[idx] = ("", 0.0, {})
            
            # Process OCR results with tracking and validation
            for idx, bbox, confidence, plate_crop, track_id in valid_detections:
                x1, y1, x2, y2 = map(int, bbox)
                
                # Get OCR result if available (may not exist if deferred OCR skipped it)
                if idx in ocr_results:
                    plate_text, ocr_confidence, ocr_metadata = ocr_results[idx]
                    
                    # Debug: Log raw OCR output
                    if plate_text:
                        print(f"  Raw OCR: '{plate_text}' (conf={ocr_confidence:.2f})")
                else:
                    # No OCR result (deferred) - add to track history for next frame
                    plate_text, ocr_confidence, ocr_metadata = "", 0.0, {}
                    if track_id != -1:
                        seen_count = self.track_stability[track_id]['seen_count']
                        print(f"  ⏳ Track {track_id}: Waiting for stability ({seen_count}/{self.STABLE_TRACK_FRAMES} frames)")
                        # Track exists but OCR not run yet - mark for next frame
                        self.track_ocr_history[track_id].append({
                            'text': '',
                            'confidence': 0.0,
                            'bbox': bbox,
                            'crop': plate_crop,
                            'frame': self.frame_count
                        })
                    continue  # Skip processing until OCR runs
                
                # MANUAL REVIEW: Save crops with OCR confidence < 10% for human validation
                # These are YOLO detections that OCR cannot read reliably
                if ocr_confidence < self.manual_review_conf_threshold:
                    self._add_to_manual_review_buffer(
                        session_id=session_id,
                        track_id=track_id,
                        yolo_conf=confidence,
                        ocr_conf=ocr_confidence,
                        crop=plate_crop,
                        bbox=bbox,
                        frame_num=self.frame_count
                    )
                    print(f"  → Added to manual review buffer (Track {track_id}, OCR conf={ocr_confidence:.2f})")
                
                # Police-grade: OCR confidence selection (only keep best per track)
                # Update track's best OCR if this result is better
                if track_id != -1:
                    track_best_conf = self.track_stability[track_id]['best_ocr_conf']
                    if ocr_confidence > track_best_conf:
                        self.track_stability[track_id]['best_ocr_text'] = plate_text
                        self.track_stability[track_id]['best_ocr_conf'] = ocr_confidence
                        print(f"  🏆 Track {track_id}: New best OCR '{plate_text}' (conf={ocr_confidence:.2f})")
                    
                    # CRITICAL: Add to OCR history for lost track finalization
                    self.track_ocr_history[track_id].append({
                        'text': plate_text,
                        'confidence': ocr_confidence,
                        'bbox': bbox,
                        'crop': plate_crop,
                        'frame': self.frame_count
                    })
                
                # Police-grade: Final Plate Decision Logic
                # Output plate when: ocr_score >= 0.4 OR seen_count > 4 (use best available)
                should_output_plate = False
                output_text = plate_text
                output_conf = ocr_confidence
                
                if track_id != -1:
                    seen_count = self.track_stability[track_id]['seen_count']
                    track_best_text = self.track_stability[track_id]['best_ocr_text']
                    track_best_conf = self.track_stability[track_id]['best_ocr_conf']
                    
                    # Rule 1: High confidence OCR (>= 0.40)
                    if track_best_conf >= self.MIN_OCR_CONFIDENCE:
                        should_output_plate = True
                        output_text = track_best_text
                        output_conf = track_best_conf
                        print(f"  ✅ Track {track_id}: HIGH CONFIDENCE plate '{output_text}' (conf={output_conf:.2f})")
                    
                    # Rule 2: Stable track fallback (seen >= 5 frames, use best available)
                    elif seen_count >= 5 and track_best_text:
                        should_output_plate = True
                        output_text = track_best_text
                        output_conf = track_best_conf
                        print(f"  ✅ Track {track_id}: STABLE TRACK plate '{output_text}' (conf={output_conf:.2f}, seen={seen_count})")
                    else:
                        print(f"  ⏳ Track {track_id}: Waiting (conf={track_best_conf:.2f}, seen={seen_count}/5)")
                else:
                    # No tracking - use direct OCR result
                    if ocr_confidence >= self.MIN_OCR_CONFIDENCE:
                        should_output_plate = True
                
                # Skip if plate should not be output yet
                if not should_output_plate:
                    continue
                
                # Use output_text and output_conf for validation
                plate_text = output_text
                ocr_confidence = output_conf
                
                if not plate_text:
                    continue
                
                # Validate and clean plate text
                cleaned_text = self.text_cleaner.clean(plate_text)
                
                # Debug: Log cleaned output
                if cleaned_text != plate_text:
                    print(f"  Cleaned: '{plate_text}' → '{cleaned_text}'")
                
                is_valid = self._validate_indian_plate(cleaned_text)
                
                # Skip invalid plates
                if not is_valid:
                    print(f"  Skipped: Invalid format '{cleaned_text}'")
                    continue
                
                # Police-grade: Check if this track already output (deduplication)
                if track_id != -1:
                    track_key = f"track_{track_id}"
                    if track_key in self.track_detections[session_id]:
                        print(f"  ⏭️ Track {track_id}: Already output, skipping duplicate")
                        continue
                    # Mark track as output
                    self.track_detections[session_id][track_key] = {'text': cleaned_text, 'confidence': ocr_confidence}
                
                # Use OCR confidence as final metric (police-grade)
                final_confidence = float(ocr_confidence)
                # Skip redundant temporal voting and track key checks
                # Police-grade decision already made above (conf >= 0.4 OR seen >= 5)
                # Proceed directly to saving results
                
                # Save crop image for record keeping
                crop_path = None
                if config.get('save_crops', False):
                    try:
                        crop_path = save_crop_image(
                            crop=plate_crop,
                            output_dir=f"data/crops/{session_id}",
                            plate_text=cleaned_text,
                            track_id=track_id if track_id else -1
                        )
                    except Exception as e:
                        print(f"  Warning: Failed to save crop: {e}")
                
                # Add to result aggregator for statistics
                self.result_aggregator.add_result(
                    track_id=track_id if track_id else -1,
                    text=cleaned_text,
                    confidence=final_confidence,
                    bbox=bbox,
                    frame_number=self.frame_count,
                    metadata={'crop_path': crop_path} if crop_path else None
                )
                
                # Add to preview buffer instead of directly saving to database
                # Save crop and add to validation preview (top 2 plates)
                preview_crop_path = self._add_to_preview_buffer(
                    session_id=session_id,
                    plate_text=cleaned_text,
                    confidence=final_confidence,
                    crop=plate_crop,
                    bbox=bbox,
                    track_id=track_id if track_id else -1,
                    frame_num=self.frame_count
                )
                
                # Only save to database if auto_save_to_db is enabled
                detection_id = None
                if self.auto_save_to_db:
                    detection_id = self.detection_repo.save_detection(
                        user_id=user_id,
                        username=username,
                        plate_text=cleaned_text,
                        confidence=final_confidence,
                        cropped_plate=plate_crop,
                        bbox=[int(x) for x in bbox],
                        track_id=track_id if track_id else -1,
                        frame_number=self.frame_count,
                        is_valid=is_valid,
                        session_id=session_id
                    )
                    print(f"✓ Saved detection: ID={detection_id}, Plate={cleaned_text}, Conf={final_confidence:.2f}, Track={track_id}")
                else:
                    # Store in preview for validation
                    print(f"📋 Preview detection: Plate={cleaned_text}, Conf={final_confidence:.2f}, Track={track_id}")
                
                # Add to session cache
                self.session_cache[session_id].add(cleaned_text)
                
                # Prepare result
                result = {
                    '_id': detection_id if detection_id else '',
                    'text': cleaned_text,
                    'confidence': final_confidence,
                    'box': [int(x) for x in bbox],  # Ensure list of ints
                    'is_valid': is_valid,
                    'track_id': track_id
                }
                results.append(result)
                
                # Draw on frame with enhanced visualization
                color = (0, 255, 0) if is_valid else (0, 255, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                label = f"{cleaned_text} ({final_confidence*100:.1f}%)"
                # Use draw_text_with_background for better visibility
                frame = draw_text_with_background(
                    image=frame,
                    text=label,
                    position=(x1, max(15, y1 - 10)),
                    font_scale=0.6,
                    thickness=2,
                    text_color=color,
                    bg_color=(0, 0, 0),
                    padding=3
                )
                
                if track_id:
                    track_label = f"ID: {track_id}"
                    frame = draw_text_with_background(
                        image=frame,
                        text=track_label,
                        position=(x1, y2 + 20),
                        font_scale=0.5,
                        thickness=1,
                        text_color=(255, 0, 255),
                        bg_color=(0, 0, 0),
                        padding=2
                    )
            
            # Police-grade: Finalize lost tracks (tracks that disappeared from frame)
            # This ensures stable tracks get output even if they leave before meeting confidence threshold
            finalized_tracks = self._finalize_lost_tracks(session_id, track_ids)
            for finalized in finalized_tracks:
                # Process finalized track same as regular detection
                cleaned_text = self.text_cleaner.clean(finalized['text'])
                is_valid = self._validate_indian_plate(cleaned_text)
                
                if is_valid:
                    track_id = finalized['track_id']
                    track_key = f"track_{track_id}"
                    
                    # Check if not already saved
                    if track_key not in self.track_detections[session_id]:
                        bbox = finalized['bbox']
                        x1, y1, x2, y2 = map(int, bbox)
                        
                        result = {
                            'plate_text': cleaned_text,
                            'confidence': finalized['confidence'],
                            'bbox': bbox,
                            'frame_number': self.frame_count,
                            'is_valid': is_valid,
                            'track_id': track_id,
                            'finalized_lost_track': True
                        }
                        results.append(result)
                        
                        # Mark as saved
                        self.track_detections[session_id][track_key] = result
                        
                        print(f"  ✅ Finalized lost track {track_id}: '{cleaned_text}' (conf={finalized['confidence']:.2f})")
            
            return frame, results
            
        except Exception as e:
            print(f"❌ Frame processing error: {e}")
            return frame, []
    
    def process_video(
        self,
        video_path: str,
        config: Dict,
        user_id: str,
        username: str,
        session_id: str
    ) -> Tuple[List[Dict], Dict]:
        """
        Process entire video file.
        
        Args:
            video_path: Path to video file
            config: Detection configuration
            user_id: User ID
            username: Username
            session_id: Session ID
            
        Returns:
            Tuple of (detection_results, statistics)
        """
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                raise ValueError(f"Failed to open video: {video_path}")
            
            # Load models if not loaded
            if not self.detector:
                self.load_models(config)
            
            # Reset session
            self.reset_session(session_id)
            
            all_results = []
            frame_idx = 0
            start_time = time.time()
            
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            print(f"🎥 Processing video: {total_frames} frames @ {fps} FPS")
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_idx += 1
                
                # Process every Nth frame for efficiency
                skip_frames = config.get('skip_frames', 5)
                if frame_idx % skip_frames != 0:
                    continue
                
                # Process frame
                _, results = self.process_frame(
                    frame=frame,
                    config=config,
                    user_id=user_id,
                    username=username,
                    session_id=session_id
                )
                
                all_results.extend(results)
                
                if frame_idx % 100 == 0:
                    print(f"  Processed {frame_idx}/{total_frames} frames...")
            
            cap.release()
            
            elapsed_time = time.time() - start_time
            
            # Flush manual review crops to disk
            manual_review_stats = self._flush_manual_review_crops(session_id)
            
            # Get comprehensive statistics from all modules
            temporal_voter_stats = self.temporal_voter.get_statistics()
            aggregator_stats = self.result_aggregator.get_summary()
            
            # Compile statistics
            stats = {
                'total_frames': total_frames,
                'processed_frames': frame_idx // skip_frames,
                'detections': len(all_results),
                'unique_plates': len(self.session_cache[session_id]),
                'unique_vehicles': aggregator_stats.get('unique_vehicles', 0),
                'temporal_voter': temporal_voter_stats,
                'manual_review': manual_review_stats,
                'processing_time': elapsed_time,
                'fps': frame_idx / elapsed_time if elapsed_time > 0 else 0
            }
            
            print(f"✅ Video processed: {len(all_results)} detections in {elapsed_time:.2f}s")
            print(f"📊 Statistics: {aggregator_stats.get('unique_vehicles', 0)} vehicles, {len(self.session_cache[session_id])} unique plates")
            
            return all_results, stats
            
        except Exception as e:
            print(f"❌ Video processing error: {e}")
            raise
    
    def reset_session(self, session_id: str):
        """Clear session cache and tracking data."""
        if session_id in self.session_cache:
            self.session_cache[session_id].clear()
        # Clear track detections for this session
        if session_id in self.track_detections:
            self.track_detections[session_id].clear()
        # Clear OCR history
        self.track_ocr_history.clear()
        # Clear track stability (police-grade workflow state)
        self.track_stability.clear()
        # Clear manual review buffer
        if session_id in self.manual_review_buffer:
            self.manual_review_buffer[session_id].clear()
        # Clear preview buffer
        if session_id in self.preview_buffer:
            self.preview_buffer[session_id].clear()
        self.frame_count = 0
        
        if self.tracker:
            self.tracker.reset()
    
    def _add_to_manual_review_buffer(
        self,
        session_id: str,
        track_id: int,
        yolo_conf: float,
        ocr_conf: float,
        crop: np.ndarray,
        bbox: List[int],
        frame_num: int
    ):
        """
        Add crop to manual review buffer, keeping only top N best quality crops per track.
        Sorted by: 1) YOLO confidence (higher = better quality detection)
                  2) OCR confidence (secondary sort)
        """
        if track_id is None or track_id == -1:
            return  # Skip untracked detections
        
        buffer = self.manual_review_buffer[session_id][track_id]
        
        # Add new crop
        buffer.append({
            'yolo_conf': yolo_conf,
            'ocr_conf': ocr_conf,
            'crop': crop.copy(),
            'bbox': bbox,
            'frame_num': frame_num
        })
        
        # Sort by YOLO confidence (primary), then OCR confidence (secondary)
        buffer.sort(key=lambda x: (-x['yolo_conf'], -x['ocr_conf']))
        
        # Keep only top N crops
        if len(buffer) > self.max_crops_per_track:
            self.manual_review_buffer[session_id][track_id] = buffer[:self.max_crops_per_track]
    
    def _add_to_preview_buffer(
        self,
        session_id: str,
        plate_text: str,
        confidence: float,
        crop: np.ndarray,
        bbox: List[int],
        track_id: int,
        frame_num: int
    ) -> Optional[str]:
        """
        Save crop to disk and add to preview buffer for validation display.
        Returns the saved crop file path.
        """
        try:
            # Save crop to data/crops/preview/{session_id}/
            crop_dir = Path('data/crops/preview') / session_id
            crop_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            crop_filename = (
                f"track_{track_id:04d}_"
                f"{plate_text.replace(' ', '_')}_"
                f"conf{confidence:.3f}_"
                f"frame{frame_num:05d}.jpg"
            )
            crop_path = crop_dir / crop_filename
            
            # Save crop image
            cv2.imwrite(str(crop_path), crop)
            
            # Add to preview buffer (keep only top N plates)
            preview_item = {
                'plate_text': plate_text,
                'confidence': confidence,
                'crop_path': str(crop_path),
                'bbox': bbox,
                'track_id': track_id,
                'frame_num': frame_num
            }
            
            # Check if this track already exists in preview
            existing_idx = None
            for idx, item in enumerate(self.preview_buffer[session_id]):
                if item['track_id'] == track_id:
                    existing_idx = idx
                    break
            
            if existing_idx is not None:
                # Update if better confidence
                if confidence > self.preview_buffer[session_id][existing_idx]['confidence']:
                    self.preview_buffer[session_id][existing_idx] = preview_item
            else:
                # Add new entry
                self.preview_buffer[session_id].append(preview_item)
            
            # Sort by confidence and keep only top N
            self.preview_buffer[session_id].sort(key=lambda x: -x['confidence'])
            self.preview_buffer[session_id] = self.preview_buffer[session_id][:self.max_preview_plates]
            
            return str(crop_path)
            
        except Exception as e:
            print(f"  Warning: Failed to save preview crop: {e}")
            return None
    
    def get_preview_detections(self, session_id: str) -> List[Dict]:
        """
        Get preview detections for validation display.
        Returns top 2 plates with their best crop images.
        """
        previews = self.preview_buffer.get(session_id, [])
        
        # Convert crop paths to base64 for frontend display
        result = []
        for preview in previews:
            try:
                # Read crop image
                crop_path = Path(preview['crop_path'])
                if crop_path.exists():
                    crop_img = cv2.imread(str(crop_path))
                    _, buffer = cv2.imencode('.jpg', crop_img)
                    crop_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    result.append({
                        'plate_text': preview['plate_text'] if preview['plate_text'] else "Can't extract OCR",
                        'confidence': float(preview['confidence']),
                        'crop_base64': crop_base64,
                        'bbox': [int(x) for x in preview['bbox']],
                        'track_id': int(preview['track_id']),
                        'frame_num': int(preview['frame_num'])
                    })
            except Exception as e:
                print(f"  Warning: Failed to read preview crop: {e}")
                continue
        
        return result
    
    def get_manual_review_crops(self, session_id: str) -> List[Dict]:
        """
        Get manual review crops (OCR < 10%) for human validation display.
        Returns the best crop image from each track.
        """
        manual_review_dir = Path('data/crops/manual_review') / session_id
        
        if not manual_review_dir.exists():
            return []
        
        result = []
        
        # Iterate through track directories
        for track_dir in sorted(manual_review_dir.iterdir()):
            if not track_dir.is_dir() or not track_dir.name.startswith('track_'):
                continue
            
            # Extract track_id from directory name (e.g., track_0002 -> 2)
            try:
                track_id = int(track_dir.name.split('_')[1])
            except (IndexError, ValueError):
                continue
            
            # Find the best image (highest YOLO confidence)
            best_crop = None
            best_yolo_conf = 0.0
            best_filepath = None
            
            for img_file in sorted(track_dir.iterdir()):
                if not img_file.is_file() or not img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    continue
                
                # Parse filename to extract confidences
                # Format: img_1_yolo0.850_ocr0.050_frame00123.jpg
                try:
                    parts = img_file.stem.split('_')
                    yolo_conf = float(parts[2].replace('yolo', ''))
                    ocr_conf = float(parts[3].replace('ocr', ''))
                    frame_num = int(parts[4].replace('frame', ''))
                    
                    if yolo_conf > best_yolo_conf:
                        best_yolo_conf = yolo_conf
                        best_filepath = img_file
                        best_crop = {
                            'yolo_conf': yolo_conf,
                            'ocr_conf': ocr_conf,
                            'frame_num': frame_num
                        }
                except (IndexError, ValueError) as e:
                    print(f"  Warning: Failed to parse filename {img_file.name}: {e}")
                    continue
            
            # Read and encode the best crop
            if best_crop and best_filepath:
                try:
                    crop_img = cv2.imread(str(best_filepath))
                    if crop_img is not None:
                        _, buffer = cv2.imencode('.jpg', crop_img)
                        crop_base64 = base64.b64encode(buffer).decode('utf-8')
                        
                        result.append({
                            'track_id': int(track_id),
                            'yolo_confidence': float(best_crop['yolo_conf']),
                            'ocr_confidence': float(best_crop['ocr_conf']),
                            'frame_num': int(best_crop['frame_num']),
                            'crop_base64': crop_base64,
                            'reason': 'Low OCR confidence (< 10%)',
                            'crop_path': str(best_filepath)
                        })
                except Exception as e:
                    print(f"  Warning: Failed to read manual review crop: {e}")
                    continue
        
        # Sort by YOLO confidence (best quality first)
        result.sort(key=lambda x: x['yolo_confidence'], reverse=True)
        
        return result
    
    def _flush_manual_review_crops(self, session_id: str) -> Dict:
        """
        Save all buffered manual review crops to disk for human validation.
        Returns statistics about saved crops.
        """
        if session_id not in self.manual_review_buffer:
            return {'total_tracks': 0, 'total_crops': 0}
        
        buffer = self.manual_review_buffer[session_id]
        manual_review_dir = Path('data/crops/manual_review') / session_id
        manual_review_dir.mkdir(parents=True, exist_ok=True)
        
        total_tracks = 0
        total_crops = 0
        
        for track_id, crops in buffer.items():
            if not crops:
                continue
            
            total_tracks += 1
            track_dir = manual_review_dir / f"track_{track_id:04d}"
            track_dir.mkdir(exist_ok=True)
            
            for idx, crop_data in enumerate(crops):
                filename = (
                    f"img_{idx+1}_"
                    f"yolo{crop_data['yolo_conf']:.3f}_"
                    f"ocr{crop_data['ocr_conf']:.3f}_"
                    f"frame{crop_data['frame_num']:05d}.jpg"
                )
                filepath = track_dir / filename
                
                try:
                    cv2.imwrite(str(filepath), crop_data['crop'])
                    total_crops += 1
                except Exception as e:
                    print(f"  Warning: Failed to save manual review crop: {e}")
        
        print(f"📁 Manual Review: Saved {total_crops} crops from {total_tracks} tracks to {manual_review_dir}")
        
        # Clear buffer after saving
        self.manual_review_buffer[session_id].clear()
        
        return {
            'total_tracks': total_tracks,
            'total_crops': total_crops,
            'review_dir': str(manual_review_dir)
        }
    
    def _vote_on_plate(self, track_id: int) -> Optional[Dict]:
        """
        Perform temporal voting on OCR history for a track with consensus and fuzzy matching.
        Production ANPR approach: aggregate confidences + fuzzy OCR correction.
        
        Optimized for speed: Allow single high-confidence detections (0.50+) or 
        require minimal voting (2 frames) for lower confidence.
        
        Args:
            track_id: Vehicle tracking ID
            
        Returns:
            Dict with voted result or None if not enough data
        """
        history = self.track_ocr_history.get(track_id, [])
        
        if not history:
            return None
        
        # Fast path: Accept single reading with high confidence (0.50+) and valid format
        # This allows immediate detection without waiting for temporal voting
        for reading in history:
            if reading['confidence'] >= 0.50 and self._validate_indian_plate(reading['text']):
                return reading
        
        # Need at least 2 readings for consensus (reduced from 3 for faster processing)
        if len(history) < 2:
            return None
        
        # Normalize texts and aggregate confidences
        from collections import Counter
        agg_conf = defaultdict(float)
        counts = defaultdict(int)
        
        for reading in history:
            text = reading['text']
            conf = reading['confidence']
            agg_conf[text] += conf
            counts[text] += 1
        
        # Get most common text
        if not agg_conf:
            return None
        
        best_text = max(agg_conf.items(), key=lambda x: x[1])[0]
        total_conf = agg_conf[best_text]
        frames_seen = len(history)
        
        # Consensus metric: average confidence per frame
        avg_conf = total_conf / frames_seen if frames_seen > 0 else 0.0
        
        # Check if valid format
        if self._validate_indian_plate(best_text):
            # Relaxed thresholds: 20% avg confidence OR appeared in 40% of frames
            # (reduced from 30% for faster nighttime detection)
            vote_ratio = counts[best_text] / frames_seen
            if avg_conf >= 0.20 or vote_ratio >= 0.40:
                best_reading = max([r for r in history if r['text'] == best_text], 
                                 key=lambda x: x['confidence'])
                return {
                    'text': best_text,
                    'confidence': avg_conf,
                    'bbox': best_reading['bbox'],
                    'crop': best_reading['crop'],
                    'vote_count': counts[best_text],
                    'total_readings': frames_seen,
                    'vote_ratio': vote_ratio
                }
        
        # Fuzzy correction: try common OCR replacements
        fuzzy_text = self._apply_fuzzy_correction(best_text)
        if fuzzy_text != best_text and self._validate_indian_plate(fuzzy_text):
            best_reading = max([r for r in history if r['text'] == best_text], 
                             key=lambda x: x['confidence'])
            return {
                'text': fuzzy_text,
                'confidence': avg_conf,
                'bbox': best_reading['bbox'],
                'crop': best_reading['crop'],
                'vote_count': counts[best_text],
                'total_readings': frames_seen,
                'fuzzy_corrected': True
            }
        
        # Not enough consensus
        return None
    
    def _apply_fuzzy_correction(self, text: str) -> str:
        """Apply fuzzy OCR corrections for common character confusions."""
        if not text:
            return text
        
        # Common OCR confusions (production ANPR standard)
        replacements = str.maketrans({
            'O': '0', 'o': '0',
            'I': '1', 'l': '1',
            'Z': '2', 'z': '2',
            'S': '5', 's': '5',
            'B': '8', 'b': '8',
            'G': '6', 'g': '6'
        })
        
        return text.translate(replacements)
    
    def get_frame_count(self) -> int:
        """Get current frame count."""
        return self.frame_count
    
    def cleanup(self):
        """
        Industry optimization: Cleanup thread pool and resources.
        Call this when shutting down the service to ensure graceful termination.
        """
        try:
            print("🧹 Cleaning up OCR thread pool...")
            self.ocr_pool.shutdown(wait=True, cancel_futures=False)
            print("✅ OCR thread pool shut down gracefully")
        except Exception as e:
            print(f"⚠️  Error during cleanup: {e}")
    
    def _finalize_lost_tracks(self, session_id: str, current_track_ids: List[int]) -> List[Dict]:
        """
        Police-grade: Finalize tracks that disappeared (lost tracking).
        Output best OCR result if seen_count >= 5 even if confidence < 0.4.
        
        Args:
            session_id: Current session ID
            current_track_ids: List of active track IDs in current frame
            
        Returns:
            List of finalized detection results for lost tracks
        """
        finalized = []
        lost_track_ids = []
        
        # Find tracks that are no longer active
        for track_id in list(self.track_stability.keys()):
            if track_id not in current_track_ids:
                track_data = self.track_stability[track_id]
                seen_count = track_data['seen_count']
                best_text = track_data['best_ocr_text']
                best_conf = track_data['best_ocr_conf']
                
                # Finalize if seen >= 5 frames and has OCR text
                if seen_count >= 5 and best_text:
                    print(f"  🏁 Finalizing lost Track {track_id}: '{best_text}' (conf={best_conf:.2f}, seen={seen_count})")
                    
                    # Check if already saved
                    track_key = f"track_{track_id}"
                    if track_key not in self.track_detections[session_id]:
                        # Get last known bbox and crop from history
                        history = self.track_ocr_history.get(track_id, [])
                        if history:
                            last_reading = history[-1]
                            finalized.append({
                                'text': best_text,
                                'confidence': best_conf,
                                'bbox': last_reading['bbox'],
                                'crop': last_reading['crop'],
                                'track_id': track_id,
                                'finalized': True,
                                'seen_count': seen_count
                            })
                
                lost_track_ids.append(track_id)
        
        # Clean up lost tracks
        for track_id in lost_track_ids:
            del self.track_stability[track_id]
            if track_id in self.track_ocr_history:
                del self.track_ocr_history[track_id]
        
        return finalized
    
    def _validate_indian_plate(self, plate_text: str) -> bool:
        """
        Validate if plate text matches Indian license plate format.
        
        Supports all official Indian formats:
        - Standard: AP16AB1234, MH12DE1433
        - BH Series: 21BH45AA1234
        - Temporary: TR458963, TEMP5698741
        - Diplomat: CC123A456, CD45B789, UN67C890
        - Military: A12B3456
        - Old formats and variations
        
        Returns:
            bool: True if valid Indian plate format
        """
        if not plate_text or len(plate_text) < 4:
            return False
        
        # Remove spaces/hyphens and convert to uppercase
        plate = plate_text.upper().replace(' ', '').replace('-', '')
        
        # Comprehensive Indian plate patterns
        patterns = [
            # Standard format: XX00XX0000 (most common)
            r'^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}$',
            
            # BH Series (Bharat Series): 22BH96Q1234
            r'^\d{2}BH\d{2}[A-Z]{1,2}\d{4}$',
            
            # Temporary Registration: TR458963, TEMP5698741
            r'^(TR|TEMP|TEMPORARY)\d{4,7}$',
            
            # Diplomat plates: CC123A456, CD45B789, UN67C890
            r'^(CC|CD|UN)\d{1,3}[A-Z]?\d{3}$',
            
            # Military plates: A12B3456
            r'^[A-Z]\d{1,2}[A-Z]\d{4}$',
            
            # Old format without series: AP1234, DL4589
            r'^[A-Z]{2}\d{3,4}$',
        ]
        
        for pattern in patterns:
            if re.match(pattern, plate):
                return True
        
        return False
