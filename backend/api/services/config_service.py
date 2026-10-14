"""
Configuration Service
Handles detection configuration management
Migrated from sidebar_controls.py
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class ConfigService:
    """Service for managing detection configuration."""
    
    # Default configuration values (from sidebar_controls.py)
    DEFAULT_CONFIG = {
        # Input source
        "input_source": "Webcam",
        "video_path": "data/sample_videos/test.mp4",
        
        # Model settings
        "model_path": "models/yolov9c.pt",
        "conf_threshold": 0.5,
        "iou_threshold": 0.45,
        "device": "cpu",
        
        # Preprocessing
        "enable_preprocessing": True,
        "enable_clahe": True,
        "clip_limit": 2.0,
        "enable_denoise": True,
        "enable_exposure": True,
        
        # OCR
        "primary_ocr": "easyocr",
        "ocr_threshold": 0.7,  # Increased for better accuracy
    }
    
    VALIDATION_RULES = {
        "conf_threshold": {"type": float, "min": 0.0, "max": 1.0},
        "iou_threshold": {"type": float, "min": 0.0, "max": 1.0},
        "clip_limit": {"type": float, "min": 1.0, "max": 5.0},
        "ocr_threshold": {"type": float, "min": 0.0, "max": 1.0},
        "device": {"type": str, "options": ["cuda", "cpu"]},
        "primary_ocr": {"type": str, "options": ["easyocr", "tesseract"]},
        "input_source": {"type": str, "options": ["Webcam", "Video File", "RTSP Stream"]},
    }
    
    def get_default_config(self):
        """Get default configuration."""
        return self.DEFAULT_CONFIG.copy()
    
    def validate_config(self, config: dict):
        """
        Validate configuration dictionary.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Tuple of (is_valid, errors_list)
        """
        errors = []
        
        if not isinstance(config, dict):
            return False, ["Configuration must be a dictionary"]
        
        # Check each field in validation rules
        for field, rules in self.VALIDATION_RULES.items():
            if field in config:
                value = config[field]
                
                # Type check
                if "type" in rules:
                    expected_type = rules["type"]
                    if not isinstance(value, expected_type):
                        errors.append(
                            f"{field}: Expected {expected_type.__name__}, got {type(value).__name__}"
                        )
                        continue
                
                # Range check
                if "min" in rules and isinstance(value, (int, float)):
                    if value < rules["min"]:
                        errors.append(f"{field}: Must be >= {rules['min']}")
                
                if "max" in rules and isinstance(value, (int, float)):
                    if value > rules["max"]:
                        errors.append(f"{field}: Must be <= {rules['max']}")
                
                # Options check
                if "options" in rules:
                    if value not in rules["options"]:
                        errors.append(
                            f"{field}: Must be one of {rules['options']}"
                        )
        
        return len(errors) == 0, errors
    
    def merge_with_defaults(self, partial_config: dict):
        """
        Merge partial config with defaults.
        
        Args:
            partial_config: User provided config
            
        Returns:
            Complete config with defaults for missing values
        """
        config = self.DEFAULT_CONFIG.copy()
        config.update(partial_config)
        return config
    
    def get_model_info(self):
        """Get information about available models."""
        return {
            "detector": {
                "name": "YOLOv9c",
                "default_path": "models/yolov9c.pt",
                "description": "YOLOv9 Compact model for license plate detection"
            },
            "ocr": {
                "options": [
                    {
                        "name": "easyocr",
                        "description": "EasyOCR - Deep learning based OCR"
                    },
                    {
                        "name": "tesseract",
                        "description": "Tesseract OCR - Traditional OCR engine"
                    }
                ]
            },
            "preprocessing": {
                "clahe": {
                    "name": "CLAHE",
                    "description": "Contrast Limited Adaptive Histogram Equalization for nighttime images"
                },
                "denoise": {
                    "name": "Denoising",
                    "description": "Reduces noise in low-light video frames"
                },
                "exposure": {
                    "name": "Auto Exposure",
                    "description": "Automatic exposure adjustment for dark frames"
                }
            }
        }
    
    def get_preprocessing_recommendations(self, use_case: str):
        """
        Get preprocessing recommendations for specific use case.
        
        Args:
            use_case: Type of video ('nighttime', 'daytime', 'low_light')
            
        Returns:
            Recommended config for use case
        """
        recommendations = {
            "nighttime": {
                "enable_preprocessing": True,
                "enable_clahe": True,
                "clip_limit": 3.0,
                "enable_denoise": True,
                "enable_exposure": True,
                "conf_threshold": 0.4,
            },
            "daytime": {
                "enable_preprocessing": False,
                "enable_clahe": False,
                "enable_denoise": False,
                "enable_exposure": False,
                "conf_threshold": 0.6,
            },
            "low_light": {
                "enable_preprocessing": True,
                "enable_clahe": True,
                "clip_limit": 2.5,
                "enable_denoise": True,
                "enable_exposure": True,
                "conf_threshold": 0.35,
            }
        }
        
        return recommendations.get(use_case, self.DEFAULT_CONFIG)
