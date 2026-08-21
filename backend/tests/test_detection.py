import numpy as np
import pytest
from PIL import Image

from app.services.detection import (
    SignageDetector,
    decode_yolov8_output,
    letterbox,
    map_box_to_original,
    non_max_suppression,
)


def test_letterbox_pads_wide_image_top_and_bottom():
    # 640x320 -> fits width exactly at scale 1.0, needs vertical padding.
    img = Image.new("RGB", (640, 320))
    padded, scale, pad_x, pad_y = letterbox(img, size=640)

    assert padded.size == (640, 640)
    assert scale == 1.0
    assert pad_x == 0
    assert pad_y == 160


def test_letterbox_pads_tall_image_left_and_right():
    img = Image.new("RGB", (320, 640))
    padded, scale, pad_x, pad_y = letterbox(img, size=640)

    assert padded.size == (640, 640)
    assert scale == 1.0
    assert pad_x == 160
    assert pad_y == 0


def test_decode_filters_below_confidence_threshold():
    # Two anchors: one confident, one not, single class.
    anchors = np.array([
        [100.0, 100.0, 20.0, 20.0, 0.9],
        [200.0, 200.0, 20.0, 20.0, 0.1],
    ])
    boxes = decode_yolov8_output(anchors, conf_threshold=0.35)

    assert len(boxes) == 1
    assert boxes[0]["confidence"] == pytest.approx(0.9)
    assert boxes[0]["class_id"] == 0


def test_decode_picks_highest_scoring_class():
    # Two classes; class 1 wins for this anchor.
    anchors = np.array([[100.0, 100.0, 20.0, 20.0, 0.2, 0.8]])
    boxes = decode_yolov8_output(anchors, conf_threshold=0.35)

    assert len(boxes) == 1
    assert boxes[0]["class_id"] == 1
    assert boxes[0]["confidence"] == pytest.approx(0.8)


def test_decode_converts_cxcywh_to_xyxy():
    anchors = np.array([[100.0, 100.0, 40.0, 20.0, 0.9]])
    boxes = decode_yolov8_output(anchors, conf_threshold=0.35)

    x1, y1, x2, y2 = boxes[0]["bbox"]
    assert (x1, y1, x2, y2) == pytest.approx((80.0, 90.0, 120.0, 110.0))


def _box(x1, y1, x2, y2, conf):
    return {"bbox": (x1, y1, x2, y2), "confidence": conf, "class_id": 0}


def test_nms_drops_heavily_overlapping_lower_confidence_box():
    boxes = [_box(100, 100, 200, 200, 0.5), _box(105, 105, 205, 205, 0.9)]
    kept = non_max_suppression(boxes, iou_threshold=0.45)

    assert len(kept) == 1
    assert kept[0]["confidence"] == pytest.approx(0.9)


def test_nms_keeps_non_overlapping_boxes():
    boxes = [_box(0, 0, 50, 50, 0.6), _box(500, 500, 550, 550, 0.9)]
    kept = non_max_suppression(boxes, iou_threshold=0.45)

    assert len(kept) == 2


def test_map_box_to_original_undoes_letterbox_padding_and_scale():
    # A 320x640 image letterboxed to 640: scale=1.0, pad_x=160, pad_y=0.
    box_in_letterboxed_space = (160.0, 100.0, 260.0, 300.0)
    mapped = map_box_to_original(
        box_in_letterboxed_space, scale=1.0, pad_x=160, pad_y=0, orig_w=320, orig_h=640,
    )

    assert mapped == pytest.approx((0.0, 100.0, 100.0, 300.0))


def test_map_box_to_original_clamps_to_image_bounds():
    mapped = map_box_to_original(
        (-50.0, -50.0, 700.0, 700.0), scale=1.0, pad_x=0, pad_y=0, orig_w=320, orig_h=640,
    )

    assert mapped == (0.0, 0.0, 320.0, 640.0)


def test_detector_unavailable_without_a_model_path():
    detector = SignageDetector(model_path=None)

    assert detector.available is False
    assert detector.detect(b"whatever") == []


def test_detector_unavailable_when_model_path_does_not_exist():
    detector = SignageDetector(model_path="C:/nonexistent/model.onnx")

    assert detector.available is False


class _FakeInput:
    name = "images"


class _FakeSession:
    """Stands in for onnxruntime.InferenceSession -- returns a canned raw
    YOLOv8-shaped output tensor with one confident detection, so detect()'s
    letterbox->decode->NMS->unletterbox pipeline can be tested end-to-end
    without real model weights."""

    def __init__(self, raw_output: np.ndarray):
        self._raw_output = raw_output

    def get_inputs(self):
        return [_FakeInput()]

    def run(self, output_names, input_feed):
        assert "images" in input_feed
        return [self._raw_output]


def test_detector_detect_maps_synthetic_detection_back_to_original_coords():
    # Square 640x640 source image -> letterbox is a no-op (scale=1, pad=0),
    # so the anchor's box should come back out unchanged.
    anchors = np.array([[320.0, 320.0, 100.0, 60.0, 0.95]])  # (n_anchors, 4+nc)
    raw = anchors.T[np.newaxis, ...]  # ONNX layout: (1, 4+nc, n_anchors)

    detector = SignageDetector(model_path=None, session=_FakeSession(raw))
    img = Image.new("RGB", (640, 640))
    buf = _png_bytes(img)

    assert detector.available is True
    detections = detector.detect(buf)

    assert len(detections) == 1
    x1, y1, x2, y2 = detections[0]["bbox"]
    assert (x1, y1, x2, y2) == pytest.approx((270.0, 290.0, 370.0, 350.0))
    assert detections[0]["confidence"] == pytest.approx(0.95)


def _png_bytes(image: Image.Image) -> bytes:
    import io
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
