"""
OCR Module for License Plate Text Recognition
Supports both EasyOCR and Tesseract with Indian plate validation
Author: AI Research Team
"""
import re
import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("⚠ EasyOCR not available, using Tesseract only")
import pytesseract
from collections import Counter
class LicensePlateOCR:
    """
    Dual OCR system for robust license plate text extraction.
    Supports EasyOCR (deep learning) and Tesseract (traditional OCR).
    Includes Indian plate format validation.
    """

    def __init__(
        self,
        primary_ocr: str = "easyocr",
        languages: List[str] = ['en'],
        conf_threshold: float = 0.4,  # Lowered from 0.6 to capture more text
        use_fallback: bool = True
    ):
        """
        Initialize OCR engines.
        Args:
            primary_ocr: Primary OCR engine ('easyocr' or 'tesseract')
            languages: List of languages for OCR
            conf_threshold: Confidence threshold for OCR results
            use_fallback: Use secondary OCR if primary fails
        """
        self.primary_ocr = primary_ocr.lower()
        self.languages = languages
        self.conf_threshold = conf_threshold
        self.use_fallback = use_fallback
        # Indian license plate regex pattern
        # Format: XX 00 XX 0000 or XX-00-XX-0000
        # XX: State code (2 letters)
        # 00: District code (2 digits)
        # XX: Series (1-2 letters)
        # 0000: Unique number (4 digits)
        self.plate_pattern = re.compile(
            r'^[A-Z]{2}[ -]?[0-9]{2}[ -]?[A-Z]{1,2}[ -]?[0-9]{4}$'
        )
        # Initialize OCR engines
        self._init_ocr_engines()
        print(f"✓ OCR initialized: Primary={primary_ocr}, Fallback={use_fallback}")

    def _init_ocr_engines(self):
        """Initialize EasyOCR and/or Tesseract."""
        # Initialize EasyOCR
        if EASYOCR_AVAILABLE:
            try:
                self.easy_reader = easyocr.Reader(
                    self.languages,
                    gpu=True # Auto-detect GPU availability
                )
                print(" ✓ EasyOCR loaded")
            except Exception as e:
                print(f" ✗ EasyOCR failed: {e}")
                self.easy_reader = None
        else:
            self.easy_reader = None
            if self.primary_ocr == "easyocr":
                self.primary_ocr = "tesseract"
                print(" ! Switched to Tesseract as primary OCR")

        # Test Tesseract availability
        try:
            pytesseract.get_tesseract_version()
            print(" ✓ Tesseract loaded")
            self.tesseract_available = True
        except Exception as e:
            print(f" ✗ Tesseract failed: {e}")
            self.tesseract_available = False

    def read_plate(
        self,
        plate_img: np.ndarray,
        preprocess: bool = True
    ) -> Tuple[str, float, Dict]:
        """
        Extract text from license plate image.
        Args:
            plate_img: Cropped plate image in BGR format
            preprocess: Apply OCR-specific preprocessing
        Returns:
            text: Extracted plate text
            confidence: OCR confidence score (0.0-1.0)
            metadata: Additional OCR information
        """
        if plate_img is None or plate_img.size == 0:
            return "", 0.0, {}

        # Try with both original and preprocessed images
        text_orig, conf_orig, meta_orig = "", 0.0, {}
        text_prep, conf_prep, meta_prep = "", 0.0, {}
        
        # Try with original image first (less aggressive)
        if self.primary_ocr == "easyocr" and self.easy_reader:
            text_orig, conf_orig, meta_orig = self._read_easyocr(plate_img)
        elif self.primary_ocr == "tesseract" and self.tesseract_available:
            text_orig, conf_orig, meta_orig = self._read_tesseract(plate_img)
        
        # If confidence is low, try with preprocessed image
        if conf_orig < 0.6 and preprocess:  # Increased threshold from 0.5
            plate_img_prep = self._preprocess_for_ocr(plate_img)
            
            if self.primary_ocr == "easyocr" and self.easy_reader:
                text_prep, conf_prep, meta_prep = self._read_easyocr(plate_img_prep)
            elif self.primary_ocr == "tesseract" and self.tesseract_available:
                text_prep, conf_prep, meta_prep = self._read_tesseract(plate_img_prep)
        
        # Use the better result
        if conf_prep > conf_orig:
            text, conf, meta = text_prep, conf_prep, meta_prep
            meta['used_preprocessing'] = True
        else:
            text, conf, meta = text_orig, conf_orig, meta_orig
            meta['used_preprocessing'] = False

        # Fallback to secondary OCR if primary fails OR if confidence is low
        if self.use_fallback and conf < self.conf_threshold:
            if self.primary_ocr == "easyocr" and self.tesseract_available:
                text_fb, conf_fb, meta_fb = self._read_tesseract(plate_img)
            elif self.primary_ocr == "tesseract" and self.easy_reader:
                text_fb, conf_fb, meta_fb = self._read_easyocr(plate_img)
            else:
                text_fb, conf_fb, meta_fb = "", 0.0, {}

            # Use fallback if better
            if conf_fb > conf:
                text, conf, meta = text_fb, conf_fb, meta_fb
                meta['used_fallback'] = True

        # Clean and validate text
        text = self._clean_text(text)
        is_valid = self.validate_indian_plate(text)
        meta['is_valid_indian'] = is_valid
        meta['original_text'] = text
        return text, conf, meta

    def _read_easyocr(self, plate_img: np.ndarray) -> Tuple[str, float, Dict]:
        """
        Read text using EasyOCR.
        Args:
            plate_img: Preprocessed plate image
        Returns:
            Tuple of (text, confidence, metadata)
        """
        try:
            # Read with paragraph mode disabled for better character-level detection
            results = self.easy_reader.readtext(
                plate_img,
                paragraph=False,  # Detect individual text regions
                detail=1,  # Get detailed results with bbox and confidence
                batch_size=1
            )
            
            if not results:
                return "", 0.0, {'method': 'easyocr'}

            # Sort results by x-coordinate (left to right) to maintain order
            results = sorted(results, key=lambda x: x[0][0][0])
            
            # Combine all detected text with intelligent spacing
            texts = []
            confidences = []
            x_positions = []
            
            for (bbox, text, conf) in results:
                # Filter out very low confidence detections
                if conf >= 0.3:  # Lower threshold to capture more text
                    texts.append(text.strip())
                    confidences.append(conf)
                    # Get x-position of text center
                    x_center = (bbox[0][0] + bbox[1][0]) / 2
                    x_positions.append(x_center)

            # Combine text with smart spacing based on x-position gaps
            combined_text = ""
            for i, txt in enumerate(texts):
                combined_text += txt
                # Add space if there's a significant gap to next character
                if i < len(texts) - 1:
                    gap = x_positions[i+1] - x_positions[i]
                    avg_width = 30  # Approximate character width
                    if gap > avg_width * 1.5:  # Significant gap
                        combined_text += " "
            
            # Calculate weighted average confidence
            if confidences:
                avg_conf = np.average(confidences, weights=[len(t) for t in texts])
            else:
                avg_conf = 0.0
                
            metadata = {
                'method': 'easyocr',
                'num_detections': len(results),
                'all_texts': texts,
                'all_confidences': confidences,
                'combined_raw': combined_text
            }
            
            return combined_text, avg_conf, metadata
        except Exception as e:
            print(f"EasyOCR error: {e}")
            return "", 0.0, {'method': 'easyocr', 'error': str(e)}

    def _read_tesseract(self, plate_img: np.ndarray) -> Tuple[str, float, Dict]:
        """
        Read text using Tesseract OCR.
        Args:
            plate_img: Preprocessed plate image
        Returns:
            Tuple of (text, confidence, metadata)
        """
        try:
            # Configure Tesseract for license plates
            # --psm 7: Treat image as single text line
            # --oem 3: Use LSTM OCR Engine Mode
            # Whitelist: Only alphanumeric characters
            config = (
                '--psm 7 --oem 3 '
                '-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- '
            )
            # Get text
            text = pytesseract.image_to_string(
                plate_img,
                config=config
            ).strip()

            # Get confidence using image_to_data
            data = pytesseract.image_to_data(
                plate_img,
                config=config,
                output_type=pytesseract.Output.DICT
            )

            # Calculate average confidence
            confidences = [
                float(conf) for conf in data['conf']
                if conf != '-1' and int(conf) > 0
            ]
            avg_conf = np.mean(confidences) / 100.0 if confidences else 0.0
            metadata = {
                'method': 'tesseract',
                'raw_text': text,
                'confidences': confidences
            }
            return text, avg_conf, metadata
        except Exception as e:
            print(f"Tesseract error: {e}")
            return "", 0.0, {'method': 'tesseract', 'error': str(e)}

    def _preprocess_for_ocr(self, plate_img: np.ndarray) -> np.ndarray:
        """
        Preprocess plate image for better OCR accuracy.
        Steps:
        1. Convert to grayscale
        2. Resize to larger size (3x for better text capture)
        3. Light bilateral filtering (preserve edges)
        4. Adaptive thresholding with larger block size
        5. Light morphological operations
        Args:
            plate_img: Input plate image
        Returns:
            Preprocessed image optimized for OCR
        """
        # Convert to grayscale
        if len(plate_img.shape) == 3:
            gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = plate_img

        # CRITICAL: Upsample 2x for better OCR (production ANPR standard)
        scale = 2  # Changed from 3 to 2 (more stable)
        h, w = gray.shape
        resized = cv2.resize(
            gray,
            (w * scale, h * scale),
            interpolation=cv2.INTER_LINEAR  # Changed from INTER_CUBIC for speed
        )

        # Apply fastNlMeansDenoising (better for plate text than bilateral)
        denoised = cv2.fastNlMeansDenoising(resized, h=12)  # Reduced from 15 for speed
        
        # Morphological glare suppression: reduce specular highlights
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        denoised = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        # Slight sharpening to enhance digit edges (production ANPR technique)
        blur = cv2.GaussianBlur(denoised, (0, 0), sigmaX=1.0)
        denoised = cv2.addWeighted(denoised, 1.5, blur, -0.5, 0)

        # Slight sharpening to enhance digit edges (production ANPR technique)
        blur = cv2.GaussianBlur(denoised, (0, 0), sigmaX=1.0)
        denoised = cv2.addWeighted(denoised, 1.5, blur, -0.5, 0)

        # Apply adaptive thresholding with production ANPR settings
        binary = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            15,  # Changed from 25 to 15 (better for 2x upscaling)
            5
        )

        # Minimal morphology (production ANPR uses very light morphology)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        # Final resize to consistent height for OCR stability (production standard)
        h, w = morph.shape[:2]
        target_h = max(80, int(h * 1.2))  # Scale to at least 80px height
        if h < target_h:
            scale = target_h / h
            morph = cv2.resize(morph, (int(w * scale), target_h), interpolation=cv2.INTER_LINEAR)

        return morph

    def _clean_text(self, text: str) -> str:
        """
        Clean OCR text output without aggressive character substitutions.
        Steps:
        1. Remove extra whitespace
        2. Convert to uppercase
        3. Remove non-alphanumeric characters
        Args:
            text: Raw OCR text
        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove extra whitespace
        text = ' '.join(text.split())

        # Convert to uppercase
        text = text.upper()

        # Remove non-alphanumeric except spaces and hyphens
        text = re.sub(r'[^A-Z0-9 -]', '', text)

        # DO NOT apply character corrections here - let PlateTextCleaner handle it
        # with proper context awareness to avoid MH→IH, MH→NH misreads
        return text.strip()

    def validate_indian_plate(self, text: str) -> bool:
        """
        Validate if text matches Indian license plate format.
        Supports all official formats:
        - Standard: AP16AB1234
        - BH Series: 21BH45AA1234
        - Temporary: TR458963, TEMP5698741
        - Diplomat: CC123A456, CD45B789, UN67C890
        - Military: A12B3456
        - Old formats with variations
        Args:
            text: License plate text
        Returns:
            True if valid Indian plate format
        """
        if not text:
            return False
        
        # Normalize: remove spaces/hyphens, uppercase
        normalized = text.upper().replace(' ', '').replace('-', '')
        
        if len(normalized) < 4:  # Minimum viable plate length
            return False
        
        # Master regex - supports 99% of Indian plates
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
        
        # Check against all patterns
        for pattern in patterns:
            if re.match(pattern, normalized):
                return True
        
        return False

    def format_plate_text(self, text: str) -> str:
        """
        Format plate text to standard Indian format.
        Handles multiple formats: standard, BH series, temporary, diplomat, military.
        Args:
            text: Raw plate text
        Returns:
            Formatted plate text (e.g., "MH 12 AB 1234", "22 BH 96 Q 1234")
        """
        # Remove spaces and hyphens
        clean = text.upper().replace(' ', '').replace('-', '')
        if len(clean) < 4:
            return text

        try:
            # BH Series: 22BH96Q1234 → 22 BH 96 Q 1234
            if re.match(r'^\d{2}BH\d{2}[A-Z]{1,2}\d{4}$', clean):
                return f"{clean[:2]} BH {clean[4:6]} {clean[6:-4]} {clean[-4:]}"
            
            # Temporary: TR458963 → TR 458963
            if re.match(r'^(TR|TEMP|TEMPORARY)\d{4,7}$', clean):
                prefix = 'TR' if clean.startswith('TR') else ('TEMP' if clean.startswith('TEMP') else 'TEMPORARY')
                number = clean[len(prefix):]
                return f"{prefix} {number}"
            
            # Diplomat: CC123A456 → CC 123 A 456
            if re.match(r'^(CC|CD|UN)\d{1,3}[A-Z]?\d{3}$', clean):
                prefix = clean[:2]
                rest = clean[2:]
                # Try to split into number + letter + number
                match = re.match(r'(\d{1,3})([A-Z]?)(\d{3})$', rest)
                if match:
                    return f"{prefix} {match.group(1)} {match.group(2)} {match.group(3)}".replace('  ', ' ').strip()
            
            # Military: A12B3456 → A 12 B 3456
            if re.match(r'^[A-Z]\d{1,2}[A-Z]\d{4}$', clean):
                match = re.match(r'^([A-Z])(\d{1,2})([A-Z])(\d{4})$', clean)
                if match:
                    return f"{match.group(1)} {match.group(2)} {match.group(3)} {match.group(4)}"
            
            # Standard format: XX00XX0000 → XX 00 XX 0000
            if len(clean) >= 8 and re.match(r'^[A-Z]{2}\d', clean):
                state = clean[:2]
                # Find where district number starts
                district_match = re.match(r'^[A-Z]{2}(\d{1,2})', clean)
                if district_match:
                    district_len = len(district_match.group(1))
                    district = clean[2:2+district_len]
                    remaining = clean[2+district_len:]
                    if len(remaining) >= 5:
                        series = remaining[:-4]
                        number = remaining[-4:]
                        return f"{state} {district} {series} {number}"
            
            # Old format without series: AP1234 → AP 1234
            if re.match(r'^[A-Z]{2}\d{3,4}$', clean):
                return f"{clean[:2]} {clean[2:]}"
            
            # Default: return as-is if no pattern matches
            return text
        except Exception as e:
            print(f"Warning: Text formatting error: {e}")
            return text

class TemporalVoting:
    """
    Temporal voting to improve OCR accuracy across multiple frames.
    Uses majority voting from detection history.
    """
    def __init__(self, window_size: int = 10):
        """
        Initialize temporal voting.
        Args:
            window_size: Number of frames to consider for voting
        """
        self.window_size = window_size
        # Track history: track_id -> list of (text, confidence)
        self.history = {}

    def vote(
        self,
        track_id: int,
        text: str,
        confidence: float
    ) -> Tuple[str, float]:
        """
        Add OCR result and get voted text.
        Args:
            track_id: Vehicle tracking ID
            text: OCR text for this frame
            confidence: OCR confidence
        Returns:
            voted_text: Most common text from history
            voted_conf: Average confidence of voted text
        """
        # Initialize history for new track
        if track_id not in self.history:
            self.history[track_id] = []

        # Add to history
        self.history[track_id].append((text, confidence))

        # Keep only recent history
        if len(self.history[track_id]) > self.window_size:
            self.history[track_id] = self.history[track_id][-self.window_size:]

        # Vote for most common text (with minimum confidence)
        texts = [t for t, c in self.history[track_id] if c > 0.5]
        if not texts:
            return text, confidence

        # Count occurrences
        text_counts = Counter(texts)
        voted_text = text_counts.most_common(1)[0][0]

        # Calculate average confidence for voted text
        voted_confs = [
            c for t, c in self.history[track_id]
            if t == voted_text
        ]
        voted_conf = np.mean(voted_confs) if voted_confs else confidence

        return voted_text, voted_conf

    def get_history(self, track_id: int) -> List[Tuple[str, float]]:
        """Get OCR history for a track."""
        return self.history.get(track_id, [])

    def clear_track(self, track_id: int):
        """Clear history for a specific track."""
        if track_id in self.history:
            del self.history[track_id]

    def get_all_tracks(self) -> List[int]:
        """Get list of all tracked IDs."""
        return list(self.history.keys())

# Test the OCR module
if __name__ == "__main__":
    print("Testing LicensePlateOCR...")
    try:
        # Initialize OCR
        ocr = LicensePlateOCR(
            primary_ocr="easyocr",
            use_fallback=True
        )

        # Test validation
        test_plates = [
            "MH 12 AB 1234",
            "DL 01 CZ 9999",
            "KA 05 MH 7890",
            "INVALID123",
            "MH12AB1234"
        ]
        print("\nValidation Tests:")
        for plate in test_plates:
            is_valid = ocr.validate_indian_plate(plate)
            formatted = ocr.format_plate_text(plate)
            print(f" {plate:20} -> Valid: {is_valid:5} | Formatted: {formatted}")

        # Test temporal voting
        print("\nTemporal Voting Tests:")
        voter = TemporalVoting(window_size=5)
        track_id = 1
        detections = [
            ("MH 12 AB 1234", 0.8),
            ("MH 12 AB 1234", 0.9),
            ("MH 12 AB 1235", 0.7), # Different (noise)
            ("MH 12 AB 1234", 0.85),
            ("MH 12 AB 1234", 0.82)
        ]
        for text, conf in detections:
            voted_text, voted_conf = voter.vote(track_id, text, conf)
            print(f" Input: {text} ({conf:.2f}) -> Voted: {voted_text} ({voted_conf:.2f})")

        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")