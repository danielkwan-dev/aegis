import io

from PIL import Image

from app.services.vision import crop_with_padding, preprocess_crop_for_ocr, run_ocr_cascade


def _png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_crop_with_padding_expands_box_by_ratio():
    img = Image.new("RGB", (1000, 1000))
    # 100x100 box in the middle; 10% padding should expand it by 10px each side.
    cropped = crop_with_padding(img, (450, 450, 550, 550), padding_ratio=0.1)

    assert cropped.size == (120, 120)


def test_crop_with_padding_clamps_to_image_bounds():
    img = Image.new("RGB", (200, 200))
    # Box already touches the top-left corner -- padding can't extend past 0.
    cropped = crop_with_padding(img, (0, 0, 50, 50), padding_ratio=0.5)

    assert cropped.size == (75, 75)  # 50 + 25 padding to the right/bottom only


def test_preprocess_crop_upscales_small_crops():
    small = Image.new("RGB", (40, 20), color=(200, 50, 50))
    processed = preprocess_crop_for_ocr(small)

    # Smaller dimension (20) should be scaled up to the OCR minimum.
    assert min(processed.size) == 200
    assert processed.size[0] / processed.size[1] == 2.0  # aspect ratio preserved


def test_preprocess_crop_converts_to_grayscale():
    color = Image.new("RGB", (300, 300), color=(200, 50, 50))
    processed = preprocess_crop_for_ocr(color)

    assert processed.mode == "L"


def test_preprocess_crop_leaves_already_large_crop_unscaled():
    large = Image.new("RGB", (400, 300), color=(0, 0, 0))
    processed = preprocess_crop_for_ocr(large)

    assert processed.size == (400, 300)


class _NoOpDetector:
    available = False

    def detect(self, image_bytes):
        return []


class _StubDetector:
    available = True

    def __init__(self, detections):
        self._detections = detections

    def detect(self, image_bytes):
        return self._detections


def test_run_ocr_cascade_falls_back_to_whole_image_when_detector_unavailable(monkeypatch):
    monkeypatch.setattr("app.services.vision.extract_ocr_text", lambda b: "WHOLE IMAGE TEXT")

    img = _png_bytes(Image.new("RGB", (500, 500)))
    result = run_ocr_cascade(img, detector=_NoOpDetector())

    assert result == {"text": "WHOLE IMAGE TEXT", "crops": []}


def test_run_ocr_cascade_falls_back_when_no_detections_found():
    calls = {"count": 0}

    def fake_ocr(_bytes):
        calls["count"] += 1
        return "fallback text"

    import app.services.vision as vision_module
    orig = vision_module.extract_ocr_text
    vision_module.extract_ocr_text = fake_ocr
    try:
        img = _png_bytes(Image.new("RGB", (500, 500)))
        result = run_ocr_cascade(img, detector=_StubDetector([]))
    finally:
        vision_module.extract_ocr_text = orig

    assert result["text"] == "fallback text"
    assert calls["count"] == 1


def test_run_ocr_cascade_ocrs_each_crop_and_merges_text(monkeypatch):
    seen_sizes = []

    def fake_ocr(image_bytes: bytes) -> str:
        crop = Image.open(io.BytesIO(image_bytes))
        seen_sizes.append(crop.size)
        return f"text-{len(seen_sizes)}"

    monkeypatch.setattr("app.services.vision.extract_ocr_text", fake_ocr)

    detections = [
        {"bbox": (10, 10, 60, 40), "confidence": 0.9, "class_id": 0},
        {"bbox": (200, 200, 260, 230), "confidence": 0.8, "class_id": 0},
    ]
    img = _png_bytes(Image.new("RGB", (500, 500)))
    result = run_ocr_cascade(img, detector=_StubDetector(detections))

    assert result["text"] == "text-1 . text-2"
    assert len(result["crops"]) == 2
    assert result["crops"][0]["bbox"] == (10, 10, 60, 40)
    assert result["crops"][0]["text"] == "text-1"
    # Each crop got OCR'd separately (not the whole 500x500 source image).
    assert all(size != (500, 500) for size in seen_sizes)


def test_run_ocr_cascade_deduplicates_identical_crop_text(monkeypatch):
    monkeypatch.setattr("app.services.vision.extract_ocr_text", lambda b: "Starbucks")

    detections = [
        {"bbox": (10, 10, 60, 40), "confidence": 0.9, "class_id": 0},
        {"bbox": (200, 200, 260, 230), "confidence": 0.8, "class_id": 0},
    ]
    img = _png_bytes(Image.new("RGB", (500, 500)))
    result = run_ocr_cascade(img, detector=_StubDetector(detections))

    assert result["text"] == "Starbucks"


def test_run_ocr_cascade_returns_empty_on_unreadable_image():
    result = run_ocr_cascade(b"not an image", detector=_StubDetector([]))

    assert result == {"text": "", "crops": []}
