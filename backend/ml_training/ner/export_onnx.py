"""Exports the fine-tuned NER model to ONNX and applies dynamic int8
quantization for fast CPU inference in the serving app (no GPU needed to
run this script itself -- it's a format conversion, not training).

Usage (from backend/ml_training/):
    venv/Scripts/python.exe -m ner.export_onnx
"""

from __future__ import annotations

from pathlib import Path

from optimum.onnxruntime import ORTModelForTokenClassification, ORTQuantizer
from optimum.onnxruntime.configuration import AutoQuantizationConfig
from transformers import AutoTokenizer

MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "ner-distilbert" / "final"
ONNX_DIR = Path(__file__).resolve().parent.parent / "models" / "ner-distilbert" / "onnx"
QUANTIZED_DIR = Path(__file__).resolve().parent.parent / "models" / "ner-distilbert" / "onnx-quantized"


def main() -> None:
    if not MODEL_DIR.exists():
        raise SystemExit(f"{MODEL_DIR} not found -- run `python -m ner.train` first.")

    print(f"Exporting {MODEL_DIR} -> ONNX...")
    ort_model = ORTModelForTokenClassification.from_pretrained(MODEL_DIR, export=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    ort_model.save_pretrained(ONNX_DIR)
    tokenizer.save_pretrained(ONNX_DIR)

    onnx_size = sum(f.stat().st_size for f in ONNX_DIR.glob("*.onnx")) / 1e6
    print(f"  ONNX model: {onnx_size:.1f} MB")

    print("Applying dynamic int8 quantization (AVX2 -- portable across standard cloud CPUs)...")
    quantizer = ORTQuantizer.from_pretrained(ONNX_DIR)
    qconfig = AutoQuantizationConfig.avx2(is_static=False, per_channel=False)
    quantizer.quantize(save_dir=QUANTIZED_DIR, quantization_config=qconfig)
    tokenizer.save_pretrained(QUANTIZED_DIR)

    quant_size = sum(f.stat().st_size for f in QUANTIZED_DIR.glob("*.onnx")) / 1e6
    ratio = onnx_size / max(quant_size, 0.01)
    print(f"  Quantized model: {quant_size:.1f} MB ({ratio:.1f}x smaller than unquantized ONNX)")
    print(f"\nDone -> {QUANTIZED_DIR}")
    print("Next: `python -m ner.benchmark` for the regex vs. base vs. fine-tuned vs.")
    print("quantized comparison, then publish QUANTIZED_DIR to Hugging Face Hub and")
    print("point app/ml/ner_inference.py (serving app) at it.")


if __name__ == "__main__":
    main()
