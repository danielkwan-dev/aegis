"""
Aegis Threat Engine
───────────────────
1. OCR extraction  (pytesseract)
2. EXIF metadata   (Pillow)
3. Data merge      (draft + OCR + metadata → single string)
4. Stalker baseline (mock digital history)
5. TF-IDF + clustering threat analysis
6. Stalker's Web output (nodes + edges)
"""

from __future__ import annotations

import io
import json
from datetime import datetime

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


# ──────────────────────────────────────────────
# 1. Image OCR
# ──────────────────────────────────────────────

def extract_ocr_text(image_bytes: bytes) -> str:
    """Run Tesseract OCR on raw image bytes and return extracted text."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception:
        return ""


# ──────────────────────────────────────────────
# 2. EXIF metadata extraction
# ──────────────────────────────────────────────

def _convert_to_degrees(value) -> float:
    """Convert EXIF GPS coordinate tuple to decimal degrees."""
    d, m, s = value
    return float(d) + float(m) / 60.0 + float(s) / 3600.0


def extract_exif_metadata(image_bytes: bytes) -> dict:
    """Extract useful EXIF fields from an image. Returns a flat dict."""
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


def metadata_to_text(metadata: dict) -> str:
    """Convert EXIF metadata dict into a human-readable string for merging."""
    parts = []
    if "gps_lat" in metadata and "gps_lon" in metadata:
        parts.append(f"GPS location {metadata['gps_lat']}, {metadata['gps_lon']}")
    if "datetime_original" in metadata:
        parts.append(f"Photo taken at {metadata['datetime_original']}")
    if "camera_make" in metadata or "camera_model" in metadata:
        cam = f"{metadata.get('camera_make', '')} {metadata.get('camera_model', '')}".strip()
        parts.append(f"Camera {cam}")
    return ". ".join(parts)


# ──────────────────────────────────────────────
# 3. Data merge
# ──────────────────────────────────────────────

def merge_signals(draft_text: str, ocr_text: str, metadata_text: str) -> str:
    """Concatenate all extracted text signals into one analysis string."""
    parts = [p for p in [draft_text, ocr_text, metadata_text] if p]
    return " . ".join(parts)


# ──────────────────────────────────────────────
# 4. Stalker baseline — mock digital history
# ──────────────────────────────────────────────

MOCK_HISTORY = [
    {
        "id": "hist_1",
        "label": "Morning coffee routine",
        "text": "Getting my usual oat latte at Blue Bottle on 4th and Market every weekday at 7:30am",
        "category": "daily_routine",
    },
    {
        "id": "hist_2",
        "label": "Home neighborhood",
        "text": "Love my apartment in the Sunset District, GPS location 37.7527, -122.4947. Beautiful fog every morning from my window on 25th Ave",
        "category": "home_location",
    },
    {
        "id": "hist_3",
        "label": "Gym schedule",
        "text": "Hitting the gym at 24 Hour Fitness on Divisadero every Monday Wednesday Friday at 6pm after work",
        "category": "daily_routine",
    },
    {
        "id": "hist_4",
        "label": "Workplace",
        "text": "Another day at the office on 5th floor 101 California Street financial district. My desk is by the east window",
        "category": "work_location",
    },
    {
        "id": "hist_5",
        "label": "Weekend pattern",
        "text": "Every Saturday morning farmers market at Ferry Building then walk along Embarcadero with the dog",
        "category": "daily_routine",
    },
    {
        "id": "hist_6",
        "label": "Commute route",
        "text": "Taking the N-Judah from Sunset to downtown every morning, board at 19th Ave station at 8:15am sharp",
        "category": "daily_routine",
    },
    {
        "id": "hist_7",
        "label": "Kids school",
        "text": "Dropping kids off at Lincoln Elementary on Quintara Street at 8am then heading to work",
        "category": "family_location",
    },
    {
        "id": "hist_8",
        "label": "Favorite restaurant",
        "text": "Friday date night at Nopalito on 9th Ave, always get the table near the back patio around 7pm",
        "category": "daily_routine",
    },
]


def load_stalker_baseline() -> list[dict]:
    """Load the mock digital history representing a user's past posts.
    In production this would pull from a real user history store."""
    return MOCK_HISTORY


# ──────────────────────────────────────────────
# 5. TF-IDF clustering + threat scoring
# ──────────────────────────────────────────────

def compute_threat_analysis(merged_text: str, history: list[dict]) -> dict:
    """
    Vectorize the merged text against the user's history using TF-IDF.
    Compute cosine similarity to find which historical clusters the new
    post is dangerously close to. Return threat scores per category.
    """
    history_texts = [entry["text"] for entry in history]
    all_texts = history_texts + [merged_text]

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(all_texts)

    # The new post is the last vector
    new_post_vec = tfidf_matrix[-1]
    history_vecs = tfidf_matrix[:-1]

    # Cosine similarity between new post and each history entry
    similarities = cosine_similarity(new_post_vec, history_vecs).flatten()

    # Build per-entry scores
    scored_entries = []
    for i, entry in enumerate(history):
        scored_entries.append({
            **entry,
            "similarity": round(float(similarities[i]), 4),
        })

    # Sort by most dangerous match
    scored_entries.sort(key=lambda x: x["similarity"], reverse=True)

    # Aggregate threat by category
    category_threats: dict[str, list[float]] = {}
    for entry in scored_entries:
        cat = entry["category"]
        if cat not in category_threats:
            category_threats[cat] = []
        category_threats[cat].append(entry["similarity"])

    category_scores = {}
    for cat, scores in category_threats.items():
        category_scores[cat] = round(float(np.max(scores)), 4)

    # Overall risk level
    max_sim = float(similarities.max()) if len(similarities) > 0 else 0.0

    if max_sim >= 0.4:
        risk_level = "CRITICAL"
    elif max_sim >= 0.2:
        risk_level = "HIGH"
    elif max_sim >= 0.1:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "risk_level": risk_level,
        "max_similarity": round(max_sim, 4),
        "category_scores": category_scores,
        "matched_entries": scored_entries,
    }


# ──────────────────────────────────────────────
# 6. Stalker's Web — nodes + edges output
# ──────────────────────────────────────────────

CATEGORY_COLORS = {
    "daily_routine": "#f59e0b",
    "home_location": "#ef4444",
    "work_location": "#3b82f6",
    "family_location": "#a855f7",
}


def build_stalker_web(
    merged_text: str,
    threat_analysis: dict,
    ocr_text: str,
    metadata: dict,
) -> dict:
    """
    Build a graph payload (nodes + edges) representing the Stalker's Web.
    The new post is the center node. History entries are surrounding nodes.
    Edge weight = similarity score.
    """
    nodes = []
    edges = []

    # Center node: the new post
    nodes.append({
        "id": "new_post",
        "label": "Your Draft Post",
        "type": "post",
        "risk_level": threat_analysis["risk_level"],
        "color": "#ef4444" if threat_analysis["risk_level"] in ("CRITICAL", "HIGH") else "#f59e0b",
    })

    # OCR node (if text was extracted)
    if ocr_text:
        nodes.append({
            "id": "ocr_extract",
            "label": "Image Text (OCR)",
            "type": "extraction",
            "text_preview": ocr_text[:100],
            "color": "#06b6d4",
        })
        edges.append({
            "source": "new_post",
            "target": "ocr_extract",
            "type": "contains",
            "weight": 1.0,
        })

    # Metadata node (if EXIF found)
    if metadata:
        meta_label = []
        if "gps_lat" in metadata:
            meta_label.append(f"GPS: {metadata['gps_lat']}, {metadata['gps_lon']}")
        if "datetime_original" in metadata:
            meta_label.append(f"Time: {metadata['datetime_original']}")
        nodes.append({
            "id": "exif_metadata",
            "label": "EXIF Metadata",
            "type": "metadata",
            "details": metadata,
            "description": " | ".join(meta_label) if meta_label else "Camera info found",
            "color": "#f43f5e",
        })
        edges.append({
            "source": "new_post",
            "target": "exif_metadata",
            "type": "leaks",
            "weight": 1.0,
        })

    # History nodes + edges
    SIMILARITY_THRESHOLD = 0.02  # include anything remotely related
    for entry in threat_analysis["matched_entries"]:
        if entry["similarity"] < SIMILARITY_THRESHOLD:
            continue

        cat = entry["category"]
        nodes.append({
            "id": entry["id"],
            "label": entry["label"],
            "type": "history",
            "category": cat,
            "similarity": entry["similarity"],
            "color": CATEGORY_COLORS.get(cat, "#6b7280"),
        })
        edges.append({
            "source": "new_post",
            "target": entry["id"],
            "type": "correlates",
            "weight": entry["similarity"],
            "category": cat,
        })

    return {"nodes": nodes, "edges": edges}


# ──────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────

def analyze_threat(draft_text: str, image_bytes: bytes | None) -> dict:
    """Full Aegis analysis pipeline. Called by the /api/simulate endpoint."""

    # 1 & 2. Extract from image
    ocr_text = ""
    metadata: dict = {}
    if image_bytes:
        ocr_text = extract_ocr_text(image_bytes)
        metadata = extract_exif_metadata(image_bytes)

    metadata_text = metadata_to_text(metadata)

    # 3. Merge all signals
    merged = merge_signals(draft_text, ocr_text, metadata_text)

    if not merged.strip():
        return {
            "status": "empty",
            "message": "No text or image data to analyze.",
            "web": {"nodes": [], "edges": []},
        }

    # 4. Load history & run clustering
    history = load_stalker_baseline()
    threat = compute_threat_analysis(merged, history)

    # 5. Build stalker web
    web = build_stalker_web(merged, threat, ocr_text, metadata)

    return {
        "status": "analyzed",
        "risk_level": threat["risk_level"],
        "max_similarity": threat["max_similarity"],
        "category_scores": threat["category_scores"],
        "signals": {
            "draft_text_length": len(draft_text),
            "ocr_text": ocr_text if ocr_text else None,
            "exif_metadata": metadata if metadata else None,
            "merged_length": len(merged),
        },
        "web": web,
    }
