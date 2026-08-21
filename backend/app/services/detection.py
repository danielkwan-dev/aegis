"""YOLOv8 ONNX signage/storefront detector: letterbox preprocessing, raw
output decode, and NMS -- the "detect" stage of the detect->crop->
preprocess->OCR->NER cascade.

The decode/NMS/coordinate-mapping math is kept as pure functions (no I/O),
so it's unit-testable with synthetic tensors instead of real model weights.
SignageDetector glues that math to an actual onnxruntime session -- and, if
no fine-tuned model has been trained yet (`vision_model_path` unset, or the
file doesn't exist -- the YOLOv8n fine-tune currently runs on Colab, not
locally), it silently reports no detections rather than erroring, so the
serving app's OCR cascade can fall back to whole-image OCR.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

DEFAULT_INPUT_SIZE = 640
DEFAULT_CONF_THRESHOLD = 0.35
DEFAULT_IOU_THRESHOLD = 0.45

Box = tuple[float, float, float, float]


def letterbox(image: Image.Image, size: int = DEFAULT_INPUT_SIZE) -> tuple[Image.Image, float, int, int]:
    """Resize `image` to fit within `size` x `size` preserving aspect ratio,
    padding the rest with mid-gray (matches ultralytics' training-time
    preprocessing). Returns (padded_image, scale, pad_x, pad_y)."""
    orig_w, orig_h = image.size
    scale = min(size / orig_w, size / orig_h)
    new_w, new_h = round(orig_w * scale), round(orig_h * scale)
    resized = image.resize((new_w, new_h), Image.BILINEAR)

    pad_x = (size - new_w) // 2
    pad_y = (size - new_h) // 2
    canvas = Image.new("RGB", (size, size), (114, 114, 114))
    canvas.paste(resized, (pad_x, pad_y))
    return canvas, scale, pad_x, pad_y


def decode_yolov8_output(anchors: np.ndarray, *, conf_threshold: float = DEFAULT_CONF_THRESHOLD) -> list[dict]:
    """Decode raw per-anchor rows into candidate boxes (pre-NMS), in
    letterboxed input-pixel space.

    `anchors`: array of shape (n_anchors, 4 + n_classes); each row is
    [cx, cy, w, h, class_0_score, class_1_score, ...] (ultralytics' YOLOv8
    ONNX export layout, already transposed to anchor-major).
    """
    boxes = []
    for row in np.asarray(anchors):
        cx, cy, w, h = row[:4]
        class_scores = row[4:]
        class_id = int(np.argmax(class_scores))
        score = float(class_scores[class_id])
        if score < conf_threshold:
            continue
        boxes.append({
            "bbox": (float(cx - w / 2), float(cy - h / 2), float(cx + w / 2), float(cy + h / 2)),
            "confidence": score,
            "class_id": class_id,
        })
    return boxes


def non_max_suppression(boxes: list[dict], *, iou_threshold: float = DEFAULT_IOU_THRESHOLD) -> list[dict]:
    """Greedy NMS: keep the highest-confidence box in each overlapping
    group, drop the rest."""
    ordered = sorted(boxes, key=lambda b: b["confidence"], reverse=True)
    kept: list[dict] = []
    for candidate in ordered:
        if all(_iou(candidate["bbox"], k["bbox"]) <= iou_threshold for k in kept):
            kept.append(candidate)
    return kept


def _iou(a: Box, b: Box) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def map_box_to_original(bbox: Box, *, scale: float, pad_x: int, pad_y: int, orig_w: int, orig_h: int) -> Box:
    """Undo letterbox scale+padding to map a box back to original-image
    pixel coordinates, clamped to the image bounds."""
    x1, y1, x2, y2 = bbox
    x1 = (x1 - pad_x) / scale
    y1 = (y1 - pad_y) / scale
    x2 = (x2 - pad_x) / scale
    y2 = (y2 - pad_y) / scale
    return (
        max(0.0, min(x1, orig_w)),
        max(0.0, min(y1, orig_h)),
        max(0.0, min(x2, orig_w)),
        max(0.0, min(y2, orig_h)),
    )


def _to_model_input(image: Image.Image) -> np.ndarray:
    arr = np.asarray(image, dtype=np.float32) / 255.0
    arr = arr.transpose(2, 0, 1)  # HWC -> CHW
    return arr[np.newaxis, ...]


class SignageDetector:
    """Detects signage/storefronts in an image via a fine-tuned YOLOv8 ONNX
    model, if one is configured and present.

    `session` is injectable for testing (pass an object exposing
    `.get_inputs()` / `.run()` like onnxruntime.InferenceSession) --
    production code just passes `model_path` and lets it load lazily.
    """

    def __init__(self, model_path: str | Path | None, *, session: Any | None = None):
        self._model_path = Path(model_path) if model_path else None
        self._session = session
        self._loaded = session is not None

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self._model_path or not self._model_path.exists():
            return
        import onnxruntime as ort

        self._session = ort.InferenceSession(str(self._model_path), providers=["CPUExecutionProvider"])

    @property
    def available(self) -> bool:
        self._ensure_loaded()
        return self._session is not None

    def detect(
        self,
        image_bytes: bytes,
        *,
        conf_threshold: float = DEFAULT_CONF_THRESHOLD,
        iou_threshold: float = DEFAULT_IOU_THRESHOLD,
    ) -> list[dict]:
        self._ensure_loaded()
        if self._session is None:
            return []

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        orig_w, orig_h = image.size
        letterboxed, scale, pad_x, pad_y = letterbox(image, DEFAULT_INPUT_SIZE)

        input_name = self._session.get_inputs()[0].name
        raw = self._session.run(None, {input_name: _to_model_input(letterboxed)})[0]
        anchors = raw[0].T  # (4+nc, n_anchors) -> (n_anchors, 4+nc)

        candidates = decode_yolov8_output(anchors, conf_threshold=conf_threshold)
        kept = non_max_suppression(candidates, iou_threshold=iou_threshold)

        return [
            {
                **box,
                "bbox": map_box_to_original(
                    box["bbox"], scale=scale, pad_x=pad_x, pad_y=pad_y, orig_w=orig_w, orig_h=orig_h,
                ),
            }
            for box in kept
        ]
