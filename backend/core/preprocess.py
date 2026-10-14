"""
Image Preprocessing Module for Low-Light Enhancement
Implements CLAHE, denoising, and auto exposure correction
Optimized for nighttime vehicle detection
Author: AI Research Team
"""
import cv2
import numpy as np
from typing import Tuple, Optional
class NightPreprocessor:
    """
    Preprocessing pipeline for low-light image enhancement.
    Applies CLAHE, bilateral filtering, and exposure correction.
    Works in LAB color space to preserve color information.
    """
    def __init__(
        self,
        enable_clahe: bool = True,
        clip_limit: float = 2.0,
        tile_grid_size: Tuple[int, int] = (8, 8),
        enable_denoise: bool = True,
        denoise_strength: int = 10,
        enable_exposure: bool = True,
        gamma: float = 1.2
    ):
        """
        Initialize preprocessor with enhancement parameters.
        Args:
        enable_clahe: Enable CLAHE enhancement
        clip_limit: CLAHE clip limit (1.0-5.0, higher = more contrast)
        tile_grid_size: CLAHE tile grid size (rows, cols)
        enable_denoise: Enable bilateral filtering
        denoise_strength: Denoising strength (5-20)
        enable_exposure: Enable gamma correction
        gamma: Gamma value for exposure (0.5-2.0, >1 = brighter)
        """
        # Add parameter validation
        if not 0.1 <= clip_limit <= 10.0:
            raise ValueError("clip_limit must be between 0.1 and 10.0")
        if not 5 <= denoise_strength <= 30:
            raise ValueError("denoise_strength must be between 5 and 30")
        if not 0.1 <= gamma <= 5.0:
            raise ValueError("gamma must be between 0.1 and 5.0")
        if not all(x > 0 for x in tile_grid_size):
            raise ValueError("tile_grid_size values must be positive")
        self.enable_clahe = enable_clahe
        self.clip_limit = clip_limit
        self.tile_grid_size = tile_grid_size
        self.enable_denoise = enable_denoise
        self.denoise_strength = denoise_strength
        self.enable_exposure = enable_exposure
        self.gamma = gamma
        # Create CLAHE object
        if self.enable_clahe:
            self.clahe = cv2.createCLAHE(
                clipLimit=self.clip_limit,
                tileGridSize=self.tile_grid_size
            )
        print(f"✓ Preprocessor initialized")
        print(f" CLAHE: {enable_clahe}, Denoise: {enable_denoise}, Exposure: {enable_exposure}")
    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply full preprocessing pipeline to enhance low-light images.
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            raise ValueError("Invalid input frame")
        enhanced = frame.copy()
        # Step 1: Auto exposure correction
        if self.enable_exposure:
            enhanced = self.adjust_exposure(enhanced)
        # Step 2: Denoising
        if self.enable_denoise:
            enhanced = self.denoise(enhanced)
        # Step 3: CLAHE enhancement
        if self.enable_clahe:
            enhanced = self.apply_clahe(enhanced)
        return enhanced
    def apply_clahe(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).
        Works in LAB color space to preserve color information.
        Only enhances the L (lightness) channel.
        Args:
        frame: Input BGR image
        Returns:
        CLAHE-enhanced BGR image
        """
        # Convert BGR to LAB color space
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        # Split into L, A, B channels
        l_channel, a_channel, b_channel = cv2.split(lab)
        # Apply CLAHE to L-channel only
        l_enhanced = self.clahe.apply(l_channel)
        # Merge channels back
        lab_enhanced = cv2.merge([l_enhanced, a_channel, b_channel])
        # Convert back to BGR
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        return enhanced
    def denoise(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply bilateral filtering for noise reduction.
        Preserves edges while smoothing flat regions.
        Args:
        frame: Input BGR image
        Returns:
        Denoised BGR image
        """
        denoised = cv2.bilateralFilter(
            frame,
            d=9, # Diameter of pixel neighborhood
            sigmaColor=self.denoise_strength * 3, # Color space sigma
            sigmaSpace=self.denoise_strength * 3 # Coordinate space sigma
        )
        return denoised
    def adjust_exposure(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply gamma correction for auto exposure adjustment.
        Gamma > 1: Brightens the image
        Gamma < 1: Darkens the image
        Args:
        frame: Input BGR image
        Returns:
        Exposure-corrected BGR image
        """
        # Build lookup table for gamma correction
        inv_gamma = 1.0 / self.gamma
        table = np.array([
            ((i / 255.0) ** inv_gamma) * 255
            for i in range(256)
        ]).astype("uint8")
        # Apply gamma correction using LUT
        corrected = cv2.LUT(frame, table)
        return corrected
    def adaptive_brightness(self, frame: np.ndarray) -> np.ndarray:
        """
        Automatically adjust brightness based on image statistics.
        Analyzes mean brightness and adjusts to target value.
        Args:
        frame: Input BGR image
        Returns:
        Brightness-adjusted BGR image
        """
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Calculate mean brightness
        mean_brightness = np.mean(gray)
        target_brightness = 128 # Target mean brightness (0-255)
        # Calculate adjustment factor
        if mean_brightness > 0:
            alpha = target_brightness / mean_brightness
            # Limit adjustment range to avoid over-correction
            alpha = np.clip(alpha, 0.5, 2.0)
        else:
            alpha = 1.0
        # Apply brightness adjustment
        adjusted = cv2.convertScaleAbs(frame, alpha=alpha, beta=0)
        return adjusted
    def sharpen(self, frame: np.ndarray, strength: float = 1.0) -> np.ndarray:
        """
        Apply unsharp masking for image sharpening.
        Enhances edges and fine details.
        Args:
        frame: Input BGR image
        strength: Sharpening strength (0.0-2.0)
        Returns:
        Sharpened BGR image
        """
        # Create Gaussian blur
        blurred = cv2.GaussianBlur(frame, (0, 0), 3)
        # Unsharp mask: original + strength * (original - blurred)
        sharpened = cv2.addWeighted(
            frame, 1.0 + strength,
            blurred, -strength,
            0
        )
        return sharpened
    def enhance_edges(self, frame: np.ndarray) -> np.ndarray:
        """
        Enhance edges using morphological operations.
        Useful for improving OCR performance on license plates.
        Args:
        frame: Input BGR image
        Returns:
        Edge-enhanced BGR image
        """
        # Convert to grayscale
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        # Apply morphological gradient to detect edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        gradient = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel)
        # Normalize gradient
        gradient = cv2.normalize(gradient, None, 0, 255, cv2.NORM_MINMAX)
        # Combine with original
        if len(frame.shape) == 3:
            gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            gradient_bgr = cv2.cvtColor(gradient, cv2.COLOR_GRAY2BGR)
            enhanced = cv2.addWeighted(gray_bgr, 0.7, gradient_bgr, 0.3, 0)
        else:
            enhanced = cv2.addWeighted(gray, 0.7, gradient, 0.3, 0)
        return enhanced
    def auto_white_balance(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply automatic white balance using Gray World assumption.
        Corrects color casts in images.
        Args:
        frame: Input BGR image
        Returns:
        White-balanced BGR image
        """
        # Split channels
        b, g, r = cv2.split(frame)
        # Calculate channel means
        b_mean = np.mean(b)
        g_mean = np.mean(g)
        r_mean = np.mean(r)
        # Calculate global mean
        gray_mean = (b_mean + g_mean + r_mean) / 3
        # Calculate scaling factors
        if b_mean > 0:
            b_scale = gray_mean / b_mean
        else:
            b_scale = 1.0
        if g_mean > 0:
            g_scale = gray_mean / g_mean
        else:
            g_scale = 1.0
        if r_mean > 0:
            r_scale = gray_mean / r_mean
        else:
            r_scale = 1.0
        # Apply scaling
        b = cv2.convertScaleAbs(b, alpha=b_scale)
        g = cv2.convertScaleAbs(g, alpha=g_scale)
        r = cv2.convertScaleAbs(r, alpha=r_scale)
        # Merge channels
        balanced = cv2.merge([b, g, r])
        return balanced
    def update_config(
        self,
        enable_clahe: Optional[bool] = None,
        clip_limit: Optional[float] = None,
        enable_denoise: Optional[bool] = None,
        enable_exposure: Optional[bool] = None,
        gamma: Optional[float] = None
    ):
        """
        Update preprocessing parameters dynamically.
        Args:
        enable_clahe: Enable/disable CLAHE
        clip_limit: New CLAHE clip limit
        enable_denoise: Enable/disable denoising
        enable_exposure: Enable/disable exposure correction
        gamma: New gamma value
        """
        if enable_clahe is not None:
            self.enable_clahe = enable_clahe
            print(f"CLAHE: {enable_clahe}")
        if clip_limit is not None:
            self.clip_limit = clip_limit
            if self.enable_clahe:
                self.clahe = cv2.createCLAHE(
                    clipLimit=self.clip_limit,
                    tileGridSize=self.tile_grid_size
                )
            print(f"CLAHE clip limit: {clip_limit}")
        if enable_denoise is not None:
            self.enable_denoise = enable_denoise
            print(f"Denoise: {enable_denoise}")
        if enable_exposure is not None:
            self.enable_exposure = enable_exposure
            print(f"Exposure correction: {enable_exposure}")
        if gamma is not None:
            self.gamma = gamma
            print(f"Gamma: {gamma}")
def compare_preprocessing(
    original: np.ndarray,
    preprocessor: NightPreprocessor
) -> np.ndarray:
    """
    Create side-by-side comparison of original and processed images.
    Args:
    original: Original input image
    preprocessor: NightPreprocessor instance
    Returns:
    Concatenated comparison image
    """
    # Process image
    processed = preprocessor.process(original)
    # Concatenate horizontally
    comparison = np.hstack([original, processed])
    # Add labels
    h, w = original.shape[:2]
    cv2.putText(
        comparison,
        "Original",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )
    cv2.putText(
        comparison,
        "Enhanced",
        (w + 10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )
    return comparison
# Test the preprocessor
if __name__ == "__main__":
    print("Testing NightPreprocessor...")
    try:
        # Initialize preprocessor
        preprocessor = NightPreprocessor(
            enable_clahe=True,
            clip_limit=2.0,
            enable_denoise=True,
            enable_exposure=True,
            gamma=1.2
        )
        # Create test image (simulating low-light)
        test_img = np.random.randint(0, 100, (480, 640, 3), dtype=np.uint8)
        # Test processing
        enhanced = preprocessor.process(test_img)
        print(f"✓ Preprocessing complete: {enhanced.shape}")
        # Test individual methods
        clahe_only = preprocessor.apply_clahe(test_img)
        denoised_only = preprocessor.denoise(test_img)
        exposure_only = preprocessor.adjust_exposure(test_img)
        print(f"✓ CLAHE: {clahe_only.shape}")
        print(f"✓ Denoise: {denoised_only.shape}")
        print(f"✓ Exposure: {exposure_only.shape}")
        # Test update config
        preprocessor.update_config(clip_limit=3.0, gamma=1.5)
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")