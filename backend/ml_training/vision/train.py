"""Fine-tunes YOLOv8n (pretrained COCO weights, not from-scratch) for
sign/storefront detection on a Roboflow-exported YOLOv8 dataset.

Meant to run on a GPU (a free Colab T4 trains this in roughly an hour or two
for a dataset in the ~800-3000 image range) -- see ../COLAB.md. Not
hardcoded to one dataset: pass whatever data.yaml download_dataset.py (or a
manual Roboflow export) produced.

Usage (from backend/ml_training/):
    venv/Scripts/python.exe -m vision.train --data data/vision/<project>/data.yaml
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO

OUT_DIR = Path(__file__).resolve().parent.parent / "models" / "vision-yolov8n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to a Roboflow-exported YOLOv8 data.yaml")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    args = parser.parse_args()

    model = YOLO("yolov8n.pt")  # pretrained on COCO -- fine-tuning, not training from random init
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=str(OUT_DIR),
        name="finetune",
        patience=15,
    )

    metrics = model.val()
    print(f"\nmAP50: {metrics.box.map50:.3f}   mAP50-95: {metrics.box.map:.3f}")

    onnx_path = Path(model.export(format="onnx"))
    print(f"Exported ONNX -> {onnx_path}")

    _quantize(onnx_path)

    print(f"\nBest weights -> {OUT_DIR}/finetune/weights/best.pt")
    print("Next: publish the quantized ONNX to Hugging Face Hub and wire it into")
    print("the detect->crop->preprocess->OCR->NER cascade in the serving app.")


def _quantize(onnx_path: Path) -> None:
    from onnxruntime.quantization import QuantType, quantize_dynamic

    quantized_path = onnx_path.with_name(onnx_path.stem + ".int8.onnx")
    quantize_dynamic(str(onnx_path), str(quantized_path), weight_type=QuantType.QUInt8)

    orig_mb = onnx_path.stat().st_size / 1e6
    quant_mb = quantized_path.stat().st_size / 1e6
    print(f"Quantized ONNX -> {quantized_path} ({orig_mb:.1f}MB -> {quant_mb:.1f}MB)")


if __name__ == "__main__":
    main()
