"""OCR + EXIF signal extraction, and cross-signal text merging."""

from __future__ import annotations

import io
import shutil
from datetime import datetime

import pytesseract
from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

from app.core.config import get_settings
from app.services.entity_extraction import extract_entities

_settings = get_settings()
_tesseract_cmd = _settings.tesseract_cmd or shutil.which("tesseract")
if _tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd


def extract_ocr_text(image_bytes: bytes) -> str:
    """Run Tesseract OCR on raw image bytes."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception:
        return ""


def extract_ocr_entities(ocr_text: str) -> dict:
    """Run entity extraction on OCR text, flagging high-value finds."""
    entities = extract_entities(ocr_text)

    high_value = []
    if entities["streets"]:
        high_value.extend([{"type": "street_sign", "value": s} for s in entities["streets"]])
    if entities["businesses"]:
        high_value.extend([{"type": "brand_name", "value": b} for b in entities["businesses"]])
    if entities["coordinates"]:
        high_value.extend([{"type": "visible_coordinates", "value": c} for c in entities["coordinates"]])

    entities["high_value_ocr"] = high_value
    return entities


def _convert_to_degrees(value) -> float:
    d, m, s = value
    return float(d) + float(m) / 60.0 + float(s) / 3600.0


def extract_exif_metadata(image_bytes: bytes) -> dict:
    metadata: dict = {}
    try:
        img = Image.open(io.BytesIO(image_bytes))
        exif_data = img._getexif()
        if not exif_data:
            return metadata

        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)

            if tag_name == "GPSInfo":
                gps: dict = {}
                for gps_tag_id, gps_value in value.items():
                    gps_tag_name = GPSTAGS.get(gps_tag_id, gps_tag_id)
                    gps[gps_tag_name] = gps_value

                if "GPSLatitude" in gps and "GPSLatitudeRef" in gps:
                    lat = _convert_to_degrees(gps["GPSLatitude"])
                    if gps["GPSLatitudeRef"] == "S":
                        lat = -lat
                    metadata["gps_lat"] = round(lat, 6)

                if "GPSLongitude" in gps and "GPSLongitudeRef" in gps:
                    lon = _convert_to_degrees(gps["GPSLongitude"])
                    if gps["GPSLongitudeRef"] == "W":
                        lon = -lon
                    metadata["gps_lon"] = round(lon, 6)

            elif tag_name == "DateTimeOriginal":
                metadata["datetime_original"] = str(value)

            elif tag_name == "Make":
                metadata["camera_make"] = str(value)

            elif tag_name == "Model":
                metadata["camera_model"] = str(value)
    except Exception:
        pass

    return metadata


def infer_time_context(metadata: dict, text_entities: dict) -> dict | None:
    """Build a time context from EXIF datetime or text keywords."""
    if "datetime_original" in metadata:
        try:
            dt = datetime.strptime(metadata["datetime_original"], "%Y:%m:%d %H:%M:%S")
            hour = dt.hour
            if 6 <= hour < 12:
                period = "morning"
            elif 12 <= hour < 17:
                period = "afternoon"
            elif 17 <= hour < 21:
                period = "evening"
            else:
                period = "night"
            return {
                "source": "exif",
                "datetime": metadata["datetime_original"],
                "day_of_week": dt.strftime("%A").lower(),
                "period": period,
                "hour": hour,
            }
        except ValueError:
            pass

    # Fallback: text keywords
    if text_entities.get("time_context"):
        kw = text_entities["time_context"][0]
        return {
            "source": "text_keyword",
            "keyword": kw["keyword"],
            "window": kw["window"],
            "period": kw["keyword"],
        }

    return None


def metadata_to_text(metadata: dict) -> str:
    parts = []
    if "gps_lat" in metadata and "gps_lon" in metadata:
        parts.append(f"GPS location {metadata['gps_lat']}, {metadata['gps_lon']}")
    if "datetime_original" in metadata:
        parts.append(f"Photo taken at {metadata['datetime_original']}")
    if "camera_make" in metadata or "camera_model" in metadata:
        cam = f"{metadata.get('camera_make', '')} {metadata.get('camera_model', '')}".strip()
        parts.append(f"Camera {cam}")
    return ". ".join(parts)


def merge_signals(draft_text: str, ocr_text: str, metadata_text: str) -> str:
    parts = [p for p in [draft_text, ocr_text, metadata_text] if p]
    return " . ".join(parts)
