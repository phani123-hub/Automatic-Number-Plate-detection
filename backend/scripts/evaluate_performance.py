# Placeholder for evaluate_performance.py
"""
Performance Evaluation Script
Evaluates detection accuracy, OCR accuracy, and system performance
"""
import cv2
import numpy as np
import json
import sys
from pathlib import Path
from tqdm import tqdm
import argparse

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.detector import LicensePlateDetector
from core.preprocess import NightPreprocessor
from core.ocr import LicensePlateOCR
from core.utils import calculate_iou


class PerformanceEvaluator:
    """Comprehensive performance evaluation."""

    def __init__(self, detector, preprocessor=None, ocr=None):
        """Initialize evaluator."""
        self.detector = detector
        self.preprocessor = preprocessor
        self.ocr = ocr
        self.detection_metrics = {
            'tp': 0,
            'fp': 0,
            'fn': 0,
            'ious': []
        }
        self.ocr_metrics = {
            'correct': 0,
            'incorrect': 0,
            'total': 0
        }

    def evaluate_detection(
        self,
        image_path: str,
        ground_truth: list,
        iou_threshold: float = 0.5
    ):
        """Evaluate detection on a single image.

        ground_truth: list of dicts with at least {'bbox': [x1,y1,x2,y2], 'text': <expected_text>?}
        """
        frame = cv2.imread(image_path)
        if frame is None:
            print(f"Warning: could not read image {image_path}")
            return

        # Preprocess if available
        enhanced = self.preprocessor.process(frame) if self.preprocessor is not None else frame

        # Detect
        boxes, confidences, crops = self.detector.detect(enhanced)  # Expect lists
        boxes = boxes or []
        confidences = confidences or []
        crops = crops or []

        matched_gt = set()
        matched_det = set()

        # Evaluate detections
        for det_idx, det_box in enumerate(boxes):
            max_iou = 0.0
            max_gt_idx = -1
            for gt_idx, gt in enumerate(ground_truth):
                if gt_idx in matched_gt:
                    continue
                iou = calculate_iou(det_box, gt['bbox'])
                if iou > max_iou:
                    max_iou = iou
                    max_gt_idx = gt_idx

            if max_iou >= iou_threshold and max_gt_idx >= 0:
                # True positive
                self.detection_metrics['tp'] += 1
                matched_gt.add(max_gt_idx)
                matched_det.add(det_idx)
                self.detection_metrics['ious'].append(max_iou)

                # OCR evaluation if possible and gt has expected text
                expected_text = ground_truth[max_gt_idx].get('text') or ground_truth[max_gt_idx].get('plate_text')
                if self.ocr is not None and expected_text:
                    # try to get crop corresponding to this detection
                    crop = crops[det_idx] if det_idx < len(crops) else None
                    if crop is not None:
                        try:
                            ocr_result = self.ocr.read_plate(crop)
                            # Support different return shapes: (text, conf, meta) or (text, conf)
                            if isinstance(ocr_result, tuple) and len(ocr_result) >= 2:
                                text = ocr_result[0]
                            else:
                                text = str(ocr_result)
                        except Exception:
                            text = ""

                        self.ocr_metrics['total'] += 1
                        if text and text.strip().upper() == expected_text.strip().upper():
                            self.ocr_metrics['correct'] += 1
                        else:
                            self.ocr_metrics['incorrect'] += 1
            else:
                # False positive (no matching GT)
                self.detection_metrics['fp'] += 1

        # False negatives = ground truth not matched
        self.detection_metrics['fn'] += max(0, len(ground_truth) - len(matched_gt))

    def calculate_metrics(self):
        """Calculate final metrics."""
        tp = self.detection_metrics['tp']
        fp = self.detection_metrics['fp']
        fn = self.detection_metrics['fn']
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        avg_iou = float(np.mean(self.detection_metrics['ious'])) if self.detection_metrics['ious'] else 0.0
        ocr_accuracy = (self.ocr_metrics['correct'] / self.ocr_metrics['total']) if self.ocr_metrics['total'] > 0 else 0.0

        return {
            'detection': {
                'precision': precision,
                'recall': recall,
                'f1_score': f1_score,
                'avg_iou': avg_iou
            },
            'ocr': {
                'accuracy': ocr_accuracy,
                'total': int(self.ocr_metrics['total']),
                'correct': int(self.ocr_metrics['correct']),
                'incorrect': int(self.ocr_metrics['incorrect'])
            },
            'overall': {
                'end_to_end_accuracy': precision * ocr_accuracy
            }
        }

    def print_results(self, results):
        """Print evaluation results."""
        print("\n" + "=" * 60)
        print("EVALUATION RESULTS")
        print("=" * 60)
        print("\nDETECTION:")
        print(f" Precision: {results['detection']['precision']:.4f}")
        print(f" Recall:    {results['detection']['recall']:.4f}")
        print(f" F1-Score:  {results['detection']['f1_score']:.4f}")
        print(f" Avg IoU:   {results['detection']['avg_iou']:.4f}")
        print("\nOCR:")
        print(f" Accuracy:  {results['ocr']['accuracy']:.4f} ({results['ocr'].get('correct',0)}/{results['ocr'].get('total',0)})")
        print("\nOVERALL:")
        print(f" End-to-End: {results['overall']['end_to_end_accuracy']:.4f}")
        print("=" * 60)


def main():
    """Main evaluation function."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', required=True, help="Path to images root")
    parser.add_argument('--annotations', required=True, help="JSON annotations file")
    parser.add_argument('--model', default='models/yolov8x.pt', help="Path to detector weights")
    args = parser.parse_args()

    # Initialize components
    detector = LicensePlateDetector(model_path=args.model)
    preprocessor = NightPreprocessor()
    ocr = LicensePlateOCR()

    # Create evaluator
    evaluator = PerformanceEvaluator(detector, preprocessor, ocr)

    # Load annotations
    with open(args.annotations, 'r', encoding='utf-8') as f:
        annotations = json.load(f)

    # Evaluate
    for ann in tqdm(annotations):
        image_path = str(Path(args.dataset) / ann['image'])
        gt_list = ann.get('annotations', [])
        evaluator.evaluate_detection(image_path, gt_list)

    # Calculate and print results
    results = evaluator.calculate_metrics()
    evaluator.print_results(results)


if __name__ == "__main__":
    main()