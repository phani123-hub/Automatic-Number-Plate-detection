"""
Post-processing Module for License Plate Detection
Implements temporal voting, confidence filtering, and result aggregation
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter
import re


class TemporalVoter:
    """
    Temporal voting system to improve OCR accuracy across multiple frames.
    Aggregates results from multiple detections of the same vehicle.
    """
    def __init__(
        self,
        window_size: int = 10,
        confidence_threshold: float = 0.6,
        vote_threshold: float = 0.5
    ):
        """Initialize temporal voter."""
        self.window_size = window_size
        self.confidence_threshold = confidence_threshold
        self.vote_threshold = vote_threshold
        self.track_history = defaultdict(list)
        self.final_results = {}
        print(f"✓ Temporal Voter initialized (window={window_size})")

    def add_detection(
        self,
        track_id: int,
        text: str,
        confidence: float,
        frame_number: int
    ) -> Tuple[str, float, bool]:
        """Add a detection and get voted result."""
        if confidence >= self.confidence_threshold:
            self.track_history[track_id].append((text, confidence, frame_number))

        if len(self.track_history[track_id]) > self.window_size:
            self.track_history[track_id] = self.track_history[track_id][-self.window_size:]

        voted_text, voted_conf, is_stable = self._vote(track_id)
        
        if is_stable:
            self.final_results[track_id] = (
                voted_text,
                voted_conf,
                len(self.track_history[track_id])
            )
        return voted_text, voted_conf, is_stable

    def _vote(self, track_id: int) -> Tuple[str, float, bool]:
        """Perform voting on track history."""
        history = self.track_history[track_id]
        if not history:
            return "", 0.0, False

        texts = [h[0] for h in history]
        confidences = [h[1] for h in history]
        text_counts = Counter(texts)

        if not text_counts:
            return "", 0.0, False

        best_text, vote_count = text_counts.most_common(1)[0]
        vote_ratio = vote_count / len(texts)
        best_confidences = [c for t, c in zip(texts, confidences) if t == best_text]
        avg_confidence = np.mean(best_confidences) if best_confidences else 0.0
        is_stable = vote_ratio >= self.vote_threshold and vote_count >= 3
        
        return best_text, avg_confidence, is_stable

    def get_final_result(self, track_id: int) -> Optional[Tuple[str, float, int]]:
        """Get final stable result for a track."""
        return self.final_results.get(track_id)

    def clear_track(self, track_id: int) -> None:
        """Clear history for a specific track."""
        if track_id in self.track_history:
            del self.track_history[track_id]
        if track_id in self.final_results:
            del self.final_results[track_id]

    def get_statistics(self) -> Dict:
        """Get voting statistics."""
        return {
            'total_tracks': len(self.track_history),
            'stable_tracks': len(self.final_results),
            'avg_detections_per_track': np.mean([
                len(h) for h in self.track_history.values()
            ]) if self.track_history else 0
        }


class ConfidenceFilter:
    """Filter detections based on confidence scores and quality metrics."""
    def __init__(
        self,
        min_detection_conf: float = 0.5,
        min_ocr_conf: float = 0.6,
        min_plate_width: int = 50,
        min_plate_height: int = 20,
        aspect_ratio_range: Tuple[float, float] = (2.0, 6.0)
    ):
        """Initialize confidence filter."""
        self.min_detection_conf = min_detection_conf
        self.min_ocr_conf = min_ocr_conf
        self.min_plate_width = min_plate_width
        self.min_plate_height = min_plate_height
        self.aspect_ratio_range = aspect_ratio_range

    def filter_detection(
        self,
        bbox: List[int],
        detection_conf: float,
        ocr_text: str = "",
        ocr_conf: float = 0.0
    ) -> Tuple[bool, str]:
        """Filter a single detection."""
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1

        if detection_conf < self.min_detection_conf:
            return False, f"Low detection confidence: {detection_conf:.2f}"

        if width < self.min_plate_width:
            return False, f"Plate too narrow: {width}px"

        if height < self.min_plate_height:
            return False, f"Plate too short: {height}px"

        aspect_ratio = width / height if height > 0 else 0
        if not (self.aspect_ratio_range[0] <= aspect_ratio <= self.aspect_ratio_range[1]):
            return False, f"Invalid aspect ratio: {aspect_ratio:.2f}"

        if ocr_text and ocr_conf < self.min_ocr_conf:
            return False, f"Low OCR confidence: {ocr_conf:.2f}"

        return True, "OK"


class ResultAggregator:
    """Aggregate detection results across multiple frames and tracks."""
    def __init__(self):
        """Initialize result aggregator."""
        self.all_detections = []
        self.unique_plates = {}  # plate_text -> count
        self.track_plates = {}   # track_id -> plate_text

    def add_result(
        self,
        track_id: int,
        text: str,
        confidence: float,
        bbox: List[int],
        frame_number: int,
        metadata: Optional[Dict] = None
    ) -> None:
        """Add a detection result."""
        result = {
            'track_id': track_id,
            'text': text,
            'confidence': confidence,
            'bbox': bbox,
            'frame_number': frame_number,
            'metadata': metadata or {}
        }
        self.all_detections.append(result)
        
        if text:
            self.unique_plates[text] = self.unique_plates.get(text, 0) + 1
            self.track_plates[track_id] = text

    def get_summary(self) -> Dict:
        """Get summary statistics."""
        return {
            'total_detections': len(self.all_detections),
            'unique_vehicles': len(self.track_plates),
            'unique_plates': len(self.unique_plates)
        }


class PlateTextCleaner:
    """Advanced text cleaning and correction for license plates."""
    def __init__(self):
        """Initialize text cleaner."""
        # OCR confusion mappings for context-aware corrections
        self.char_corrections = {
            'O': '0', 'I': '1', 'L': '1', 'l': '1', 'i': '1',
            'S': '5', 'B': '8', 'Z': '2', 'G': '6',
            'Q': '0', 'D': '0'
        }
        # All valid Indian state/UT codes + special codes
        self.valid_state_codes = {
            'AP', 'AR', 'AS', 'BR', 'CG', 'GA', 'GJ', 'HR', 'HP', 'JH',
            'KA', 'KL', 'MP', 'MH', 'MN', 'ML', 'MZ', 'NL', 'OD', 'PB',
            'RJ', 'SK', 'TN', 'TR', 'UP', 'UK', 'WB', 'AN', 'CH', 'DN',
            'DD', 'DL', 'LD', 'PY', 'LA', 'TS',
            # Special codes
            'BH',  # Bharat Series
            'CC', 'CD', 'UN',  # Diplomat
        }
        # Special plate prefixes
        self.special_prefixes = {'TR', 'TEMP', 'TEMPORARY', 'CC', 'CD', 'UN', 'BH'}

    def clean(self, text: str) -> str:
        """Clean and correct OCR text with smart position-aware corrections."""
        if not text:
            return ""
        
        text = text.upper().strip()
        text = re.sub(r'[^A-Z0-9 -]', '', text)
        text = ' '.join(text.split())
        
        # Smart position-aware correction
        text = self._apply_smart_corrections(text)
        # Validate and correct state code
        text = self._correct_invalid_state_code(text)
        text = self._standardize_format(text)
        return text
    
    def _correct_invalid_state_code(self, text: str) -> str:
        """Correct invalid state codes using similarity matching."""
        clean = text.replace(' ', '').replace('-', '')
        
        if len(clean) < 2:
            return text
        
        # Extract potential state code (first 2 chars)
        state_code = clean[:2]
        
        # If valid, return as-is
        if state_code in self.valid_state_codes:
            return text
        
        # Only correct CONFIRMED invalid codes that are common OCR errors
        # Be conservative - don't change codes that might be valid
        corrections = {
            'HH': 'MH',  # HH is not valid, likely Maharashtra (M looks like HH)
            'IH': 'MH',  # I+H misread of M
            'NH': 'MH',  # N+H misread of M
            'HL': 'ML',  # Meghalaya misread
            'HI': 'MH',  # Another M misread
            # Remove KH→KA: KH could be valid old format, and we might be changing correct readings
            # Remove other ambiguous corrections
        }
        
        if state_code in corrections:
            corrected_code = corrections[state_code]
            # Replace in original text preserving formatting
            corrected_text = corrected_code + clean[2:]
            # Re-apply formatting
            if ' ' in text or '-' in text:
                return self._standardize_format(corrected_text)
            return corrected_text
        
        return text
    
    def _apply_smart_corrections(self, text: str) -> str:
        """Apply corrections based on position in plate format."""
        # Remove spaces temporarily to analyze
        clean = text.replace(' ', '').replace('-', '')
        
        if len(clean) < 8:
            return text
        
        corrected = []
        
        # Positions 0-1: State code (LETTERS ONLY - never convert to digits)
        for i in range(min(2, len(clean))):
            char = clean[i]
            if char.isalpha():
                # Keep letters as-is (MH should stay MH, not become IH/NH/HH)
                corrected.append(char)
            elif char.isdigit():
                # Only convert obvious digit→letter if it makes a valid state code
                if char == '0':
                    corrected.append('O')
                elif char == '1':
                    corrected.append('I')
                else:
                    corrected.append(char)  # Keep digit if unsure
            else:
                corrected.append(char)
        
        # Positions 2-3: District code (NUMBERS ONLY)
        for i in range(2, min(4, len(clean))):
            char = clean[i]
            if char.isdigit():
                # Keep numbers as-is
                corrected.append(char)
            elif char.isalpha():
                # Convert only common OCR letter→number errors
                if char == 'O':
                    corrected.append('0')
                elif char in ('I', 'L'):
                    corrected.append('1')
                elif char in ('Z', 'z'):  # Z is often misread 2
                    corrected.append('2')
                elif char == 'S':
                    corrected.append('5')
                elif char == 'B':
                    corrected.append('8')
                else:
                    corrected.append(char)  # Keep if unsure
            else:
                corrected.append(char)
        
        # Positions 4 to -4: Series code (LETTERS, 1-2 chars)
        series_end = len(clean) - 4
        for i in range(4, series_end):
            char = clean[i]
            if char.isalpha():
                # Keep letters as-is
                corrected.append(char)
            elif char.isdigit():
                # Convert only obvious digit→letter for series
                if char == '0':
                    corrected.append('O')
                elif char == '1':
                    corrected.append('I')
                else:
                    corrected.append(char)
            else:
                corrected.append(char)
        
        # Last 4 positions: Unique number (NUMBERS ONLY)
        for i in range(max(series_end, 4), len(clean)):
            char = clean[i]
            if char.isdigit():
                # Keep numbers as-is
                corrected.append(char)
            elif char.isalpha():
                # Convert letters to numbers for last 4 digits
                if char == 'O':
                    corrected.append('0')
                elif char in ('I', 'L'):
                    corrected.append('1')
                elif char in ('Z', 'z'):  # Z is often misread 2
                    corrected.append('2')
                elif char == 'S':
                    corrected.append('5')
                elif char == 'B':
                    corrected.append('8')
                elif char == 'G':
                    corrected.append('6')
                else:
                    corrected.append(char)
            else:
                corrected.append(char)
        
        return ''.join(corrected)

    def _standardize_format(self, text: str) -> str:
        """Standardize to format: XX 00 XX 0000"""
        clean = text.replace(' ', '').replace('-', '')
        if len(clean) < 8 or len(clean) > 10:
            return text

        try:
            state = clean[:2]
            district = clean[2:4]
            if len(clean) == 9:
                series = clean[4:5]
                number = clean[5:9]
            else:
                series = clean[4:6]
                number = clean[6:10]
            formatted = f"{state} {district} {series} {number}"
            return formatted
        except Exception:
            return text
