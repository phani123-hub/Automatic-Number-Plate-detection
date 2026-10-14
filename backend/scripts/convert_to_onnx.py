# Placeholder for convert_to_onnx.py
"""
Convert YOLOv8x PyTorch Model to ONNX Format
"""
import argparse
import shutil
from pathlib import Path
import torch
from ultralytics import YOLO


def convert_to_onnx(
    weights_path: str,
    output_path: str,
    img_size: int = 640,
    dynamic: bool = True,
):
    """
    Convert PyTorch YOLOv8x to ONNX.

    Args:
        weights_path: Path to .pt file
        output_path: Output .onnx path
        img_size: Input image size
        dynamic: Enable dynamic axes
    """
    weights_path = str(weights_path)
    output_path = str(output_path)
    print(f"Loading model: {weights_path}")
    model = YOLO(weights_path)

    print("Converting to ONNX...")
    try:
        exported = model.export(
            format="onnx",
            imgsz=img_size,
            dynamic=dynamic,
            simplify=True,
        )
    except Exception as e:
        print(f"✗ Export failed: {e}")
        raise

    # Determine exported filepath (ultralytics export return type can vary)
    exported_path = None
    if isinstance(exported, (list, tuple)) and len(exported) > 0:
        exported_path = Path(exported[0])
    elif isinstance(exported, dict):
        # try to find a sensible value containing 'onnx'
        for v in exported.values():
            if isinstance(v, (str, Path)) and str(v).lower().endswith(".onnx"):
                exported_path = Path(v)
                break
        if exported_path is None:
            # fallback to first string-like value
            for v in exported.values():
                if isinstance(v, (str, Path)):
                    exported_path = Path(v)
                    break
    elif isinstance(exported, (str, Path)):
        exported_path = Path(exported)

    # If exported_path was found and exists, move/rename to requested output_path
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if exported_path and exported_path.exists():
        try:
            shutil.move(str(exported_path), str(dest))
            print(f"✓ ONNX model saved: {dest}")
        except Exception as e:
            print(f"✗ Failed to move exported file: {e}")
            raise
    else:
        # If we couldn't determine export file, still inform user
        print("⚠ Export completed but exported file path couldn't be determined or does not exist.")
        print(f"Requested output path: {dest}")
        print("Check the ultralytics export return value or specify a valid output path.")
    return str(dest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert YOLOv8x .pt to ONNX")
    parser.add_argument("--weights", type=str, required=True, help="Path to .pt weights")
    parser.add_argument("--output", type=str, required=True, help="Output .onnx path")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image size")
    parser.add_argument("--dynamic", action="store_true", help="Enable dynamic axes in ONNX")
    args = parser.parse_args()

    convert_to_onnx(args.weights, args.output, img_size=args.imgsz, dynamic=args.dynamic)