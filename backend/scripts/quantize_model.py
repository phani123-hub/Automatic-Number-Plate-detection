# Placeholder for quantize_model.py
"""
Quantize ONNX Model to INT8 for Faster Inference
"""
import argparse
from pathlib import Path

import onnx
from onnxruntime.quantization import quantize_dynamic, QuantType


def quantize_model(
    input_path: str,
    output_path: str,
    weight_type: QuantType = QuantType.QInt8,
) -> str:
    """
    Quantize ONNX model to INT8.

    Args:
        input_path: Input ONNX model path.
        output_path: Output quantized model path.
        weight_type: Quantization type (QuantType.QInt8 or QuantType.QUInt8).
    Returns:
        Path to the saved quantized model.
    """
    input_path = str(input_path)
    output_path = str(output_path)

    if not Path(input_path).exists():
        raise FileNotFoundError(f"Input ONNX model not found: {input_path}")

    print(f"Loading model: {input_path}")
    print("Quantizing to INT8...")

    quantize_dynamic(
        model_input=input_path,
        model_output=output_path,
        weight_type=weight_type,
    )

    # Verify the produced model
    model = onnx.load(output_path)
    onnx.checker.check_model(model)
    print(f"✓ Quantized model saved: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantize ONNX model to INT8")
    parser.add_argument("--input", "-i", type=str, required=True, help="Input ONNX model path")
    parser.add_argument("--output", "-o", type=str, required=True, help="Output quantized model path")
    parser.add_argument(
        "--weight-type",
        type=str,
        default="qint8",
        choices=["qint8", "quint8"],
        help="Weight quantization type (qint8 or quint8)",
    )
    args = parser.parse_args()

    wt = QuantType.QInt8 if args.weight_type.lower().startswith("qint") else QuantType.QUInt8
    quantize_model(args.input, args.output, weight_type=wt)