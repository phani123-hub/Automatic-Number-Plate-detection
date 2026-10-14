# Placeholder for benchmark_fps.py
"""
Benchmark FPS Performance of Detection System
"""
import argparse
import time
from pathlib import Path

import cv2
import numpy as np

from core.detector import LicensePlateDetector
from core.preprocess import NightPreprocessor


def benchmark_fps(
    model_path: str,
    video_path: str,
    num_frames: int = 100,
    enable_preprocessing: bool = True,
) -> None:
    """Benchmark detection FPS.

    Args:
        model_path: Path to detection model weights.
        video_path: Path to input video.
        num_frames: Number of frames to benchmark.
        enable_preprocessing: Whether to run preprocessor on frames.
    """
    model_path = str(model_path)
    video_path = str(video_path)

    print(f"Model: {model_path}")
    print(f"Video: {video_path}")
    print(f"Frames to process: {num_frames}")
    print(f"Preprocessing enabled: {enable_preprocessing}")
    print("-" * 50)

    # Initialize detector and preprocessor
    detector = LicensePlateDetector(model_path=model_path)
    preprocessor = NightPreprocessor() if enable_preprocessing else None

    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")

    times = []
    frames_processed = 0
    try:
        for i in range(num_frames):
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            start = time.time()

            # Preprocess
            if preprocessor:
                frame_proc = preprocessor.process(frame)
            else:
                frame_proc = frame

            # Detect
            try:
                boxes, confs, crops = detector.detect(frame_proc)
            except Exception:
                # If detector fails for a frame, continue
                boxes, confs, crops = [], [], []

            elapsed = time.time() - start
            times.append(elapsed)
            frames_processed += 1

            if frames_processed % 10 == 0:
                recent_avg_fps = 1.0 / np.mean(times[-10:]) if len(times) >= 10 and np.mean(times[-10:]) > 0 else float("nan")
                print(f"Frame {frames_processed}/{num_frames}: {recent_avg_fps:.2f} FPS")

    finally:
        cap.release()

    if len(times) == 0:
        print("No frames processed.")
        return

    avg_time = float(np.mean(times))
    avg_fps = 1.0 / avg_time if avg_time > 0 else float("inf")

    print("\n" + "=" * 50)
    print("Benchmark Results:")
    print(f" Frames processed: {len(times)}")
    print(f" Avg Time/frame: {avg_time*1000:.2f} ms")
    print(f" Avg FPS: {avg_fps:.2f}")
    print(f" Min FPS: {1.0/max(times):.2f}")
    print(f" Max FPS: {1.0/min(times):.2f}")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark FPS for license plate detector")
    parser.add_argument("--model", "-m", type=str, required=True, help="Path to model weights")
    parser.add_argument("--video", "-v", type=str, required=True, help="Path to input video")
    parser.add_argument("--frames", "-f", type=int, default=100, help="Number of frames to process")
    parser.add_argument("--no-preprocess", dest="preprocess", action="store_false", help="Disable preprocessing")
    args = parser.parse_args()

    benchmark_fps(args.model, args.video, num_frames=args.frames, enable_preprocessing=args.preprocess)