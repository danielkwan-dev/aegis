"""
Aegis — Personal Security Audit Engine
───────────────────────────────────────
1. OCR extraction  (pytesseract)
2. EXIF metadata   (Pillow)
3. Data merge      (draft + OCR + metadata → single string)
4. Security baseline (in-memory exposure map)
5. TF-IDF clustering + Identity Link detection
6. Exposure Map output (nodes + edges)
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone

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
# 4. User footprint (in-memory exposure map)
# ──────────────────────────────────────────────

# Sensitive entity categories
ENTITY_KEYWORDS = {
    "home": ["home", "apartment", "house", "live", "moved", "neighbor", "street", "ave", "block", "rent"],
    "work": ["office", "work", "job", "desk", "coworker", "meeting", "company", "building", "commute"],
    "daily_route": ["every", "always", "morning", "evening", "daily", "routine", "usual", "regular", "weekday", "gym", "coffee"],
    "family": ["kid", "child", "school", "daycare", "son", "daughter", "family", "parent", "pickup"],
}


def classify_sensitive_entity(text: str) -> str:
    """Classify text into a sensitive entity type using keyword matching."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for entity, keywords in ENTITY_KEYWORDS.items():
        scores[entity] = sum(1 for kw in keywords if kw in text_lower)
    best = max(scores, key=scores.get)  # type: ignore
    return best if scores[best] > 0 else "general"


class UserFootprint:
    """In-memory exposure map — the user's known digital footprint."""

    def __init__(self) -> None:
        self._entries: list[dict] = []

    @property
    def entries(self) -> list[dict]:
        return list(self._entries)

    @property
    def count(self) -> int:
        return len(self._entries)

    def ingest(
        self,
        text: str,
        label: str | None = None,
        category: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """Ingest a data point into the security baseline. Returns the entry."""
        entry_id = f"bp_{uuid.uuid4().hex[:8]}"
        entity_type = category or classify_sensitive_entity(text)
        has_gps = bool(metadata and "gps_lat" in metadata)

        entry = {
            "id": entry_id,
            "label": label or self._generate_label(text),
            "text": text,
            "entity_type": entity_type,
            "has_gps": has_gps,
            "metadata": metadata or {},
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        self._entries.append(entry)
        return entry

    def clear(self) -> None:
        self._entries.clear()

    def exposure_map_stats(self) -> dict:
        """Return summary of the current exposure map."""
        entities: dict[str, int] = {}
        known_locations = 0
        for e in self._entries:
            entities[e["entity_type"]] = entities.get(e["entity_type"], 0) + 1
            if e["has_gps"]:
                known_locations += 1

        return {
            "total_data_points": self.count,
            "sensitive_entities": entities,
            "known_locations": known_locations,
        }

    @staticmethod
    def _generate_label(text: str) -> str:
        words = text.split()
        preview = " ".join(words[:6])
        if len(words) > 6:
            preview += "..."
        return preview


# Global instance
user_footprint = UserFootprint()


# ──────────────────────────────────────────────
# 5. TF-IDF clustering + Identity Link detection
# ──────────────────────────────────────────────

def detect_identity_links(merged_text: str, baseline: list[dict]) -> dict:
    """
    Vectorize the new post against the security baseline using TF-IDF.
    Detect Identity Links — connections between the new post and baseline
    entries that, when combined, reveal a Sensitive Entity.
    Returns threat scores, identity links, and breach probability.
    """
    baseline_texts = [entry["text"] for entry in baseline]
    all_texts = baseline_texts + [merged_text]

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(all_texts)

    new_post_vec = tfidf_matrix[-1]
    baseline_vecs = tfidf_matrix[:-1]

    similarities = cosine_similarity(new_post_vec, baseline_vecs).flatten()

    # Build identity links (scored connections to baseline entries)
    identity_links = []
    for i, entry in enumerate(baseline):
        sim = float(similarities[i])
        if sim > 0.01:
            identity_links.append({
                **entry,
                "similarity": round(sim, 4),
                "link_type": "identity_link",
            })

    identity_links.sort(key=lambda x: x["similarity"], reverse=True)

    # Aggregate by sensitive entity type
    entity_threats: dict[str, list[float]] = {}
    for link in identity_links:
        etype = link["entity_type"]
        if etype not in entity_threats:
            entity_threats[etype] = []
        entity_threats[etype].append(link["similarity"])

    entity_scores = {}
    for etype, scores in entity_threats.items():
        entity_scores[etype] = round(float(np.max(scores)), 4)

    # Max similarity
    max_sim = float(similarities.max()) if len(similarities) > 0 else 0.0

    # Risk level
    if max_sim >= 0.4:
        risk_level = "CRITICAL"
    elif max_sim >= 0.2:
        risk_level = "HIGH"
    elif max_sim >= 0.1:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # Breach probability (0–100%)
    # Factors: max similarity, number of entity types exposed, number of links
    num_entities_exposed = len(entity_scores)
    num_links = len(identity_links)
    total_baseline = len(baseline)

    # Base from similarity (0–50%)
    base_prob = min(max_sim * 125, 50.0)
    # Entity diversity bonus (0–25%): more entity types exposed = worse
    entity_bonus = min(num_entities_exposed * 6.25, 25.0)
    # Coverage bonus (0–25%): what fraction of baseline is linked
    coverage = (num_links / total_baseline) if total_baseline > 0 else 0
    coverage_bonus = min(coverage * 25.0, 25.0)

    breach_probability = round(min(base_prob + entity_bonus + coverage_bonus, 100.0), 1)

    return {
        "risk_level": risk_level,
        "max_similarity": round(max_sim, 4),
        "entity_scores": entity_scores,
        "identity_links": identity_links,
        "breach_probability": breach_probability,
    }


# ──────────────────────────────────────────────
# 6. Breach Report — human-readable warnings
# ──────────────────────────────────────────────

ENTITY_LABELS = {
    "daily_route": "Routine: Daily Route",
    "home": "Location: Home",
    "work": "Location: Work",
    "family": "Location: Family",
    "general": "General Data",
}


def generate_breach_report(
    threat_analysis: dict,
    ocr_text: str,
    metadata: dict,
) -> list[dict]:
    """
    Generate human-readable breach warnings.
    Each warning explains HOW the new post connects to a sensitive entity.
    """
    warnings: list[dict] = []

    for link in threat_analysis["identity_links"]:
        entity_label = ENTITY_LABELS.get(link["entity_type"], link["entity_type"])
        similarity_pct = round(link["similarity"] * 100)

        # Determine the signal source that created the link
        signal_source = "Text overlap"
        if ocr_text and any(word in link["text"].lower() for word in ocr_text.lower().split() if len(word) > 3):
            signal_source = f"OCR: {ocr_text[:50]}"
        elif metadata.get("gps_lat") and link.get("has_gps"):
            signal_source = f"GPS: {metadata['gps_lat']}, {metadata['gps_lon']}"
        elif metadata.get("datetime_original"):
            signal_source = f"Timestamp: {metadata['datetime_original']}"

        warnings.append({
            "severity": threat_analysis["risk_level"],
            "message": f"Warning: This post connects to [{entity_label}] via [{signal_source}] ({similarity_pct}% match)",
            "entity_type": link["entity_type"],
            "linked_entry": link["label"],
            "similarity": link["similarity"],
            "signal_source": signal_source,
        })

    # Add EXIF-specific warnings
    if metadata.get("gps_lat"):
        warnings.append({
            "severity": "HIGH",
            "message": f"Warning: Image contains GPS coordinates ({metadata['gps_lat']}, {metadata['gps_lon']}). This reveals your exact location.",
            "entity_type": "exif_leak",
            "linked_entry": "EXIF Metadata",
            "similarity": 1.0,
            "signal_source": "EXIF GPS",
        })

    if metadata.get("datetime_original"):
        warnings.append({
            "severity": "MEDIUM",
            "message": f"Warning: Image contains timestamp ({metadata['datetime_original']}). This reveals when you were at this location.",
            "entity_type": "exif_leak",
            "linked_entry": "EXIF Metadata",
            "similarity": 0.8,
            "signal_source": "EXIF Timestamp",
        })

    return warnings


# ──────────────────────────────────────────────
# 7. Exposure Map — nodes + edges output
# ──────────────────────────────────────────────

ENTITY_COLORS = {
    "daily_route": "#f59e0b",
    "home": "#ef4444",
    "work": "#3b82f6",
    "family": "#a855f7",
    "general": "#6b7280",
}


def build_exposure_map(
    threat_analysis: dict,
    ocr_text: str,
    metadata: dict,
) -> dict:
    """
    Build the Exposure Map graph (nodes + edges).
    Center = new post. Surrounding = identity-linked baseline entries.
    """
    nodes = []
    edges = []

    nodes.append({
        "id": "new_post",
        "label": "Your Draft Post",
        "type": "post",
        "risk_level": threat_analysis["risk_level"],
        "color": "#ef4444" if threat_analysis["risk_level"] in ("CRITICAL", "HIGH") else "#f59e0b",
    })

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

    for link in threat_analysis["identity_links"]:
        etype = link["entity_type"]
        nodes.append({
            "id": link["id"],
            "label": link["label"],
            "type": "baseline",
            "entity_type": etype,
            "similarity": link["similarity"],
            "color": ENTITY_COLORS.get(etype, "#6b7280"),
        })
        edges.append({
            "source": "new_post",
            "target": link["id"],
            "type": "identity_link",
            "weight": link["similarity"],
            "entity_type": etype,
        })

    return {"nodes": nodes, "edges": edges}


# ──────────────────────────────────────────────
# Public API — called by main.py
# ──────────────────────────────────────────────

def ingest_data_point(text: str, image_bytes: bytes | None, label: str | None = None, category: str | None = None) -> dict:
    """Ingest a data point into the security baseline (exposure map)."""
    ocr_text = ""
    metadata: dict = {}
    if image_bytes:
        ocr_text = extract_ocr_text(image_bytes)
        metadata = extract_exif_metadata(image_bytes)

    metadata_text = metadata_to_text(metadata)
    merged = merge_signals(text, ocr_text, metadata_text)

    if not merged.strip():
        return {"status": "empty", "message": "No data to ingest."}

    entry = user_footprint.ingest(
        text=merged,
        label=label,
        category=category,
        metadata=metadata if metadata else None,
    )

    return {
        "status": "secured",
        "message": "Data Point Secured",
        "entry": entry,
        "exposure_map": user_footprint.exposure_map_stats(),
    }


def analyze_threat(draft_text: str, image_bytes: bytes | None) -> dict:
    """Full Aegis threat analysis. Detects Identity Links against the security baseline."""

    ocr_text = ""
    metadata: dict = {}
    if image_bytes:
        ocr_text = extract_ocr_text(image_bytes)
        metadata = extract_exif_metadata(image_bytes)

    metadata_text = metadata_to_text(metadata)
    merged = merge_signals(draft_text, ocr_text, metadata_text)

    if not merged.strip():
        return {
            "status": "empty",
            "message": "No text or image data to analyze.",
            "web": {"nodes": [], "edges": []},
            "exposure_map": user_footprint.exposure_map_stats(),
        }

    # Check baseline state
    baseline = user_footprint.entries
    if len(baseline) == 0:
        return {
            "status": "initializing",
            "risk_level": "INITIALIZING",
            "max_similarity": 0.0,
            "breach_probability": 0.0,
            "entity_scores": {},
            "message": "No baseline data yet. Use /audit-ingest to build your exposure map first.",
            "signals": {
                "draft_text_length": len(draft_text),
                "ocr_text": ocr_text if ocr_text else None,
                "exif_metadata": metadata if metadata else None,
                "merged_length": len(merged),
            },
            "web": {"nodes": [{
                "id": "new_post",
                "label": "Your Draft Post",
                "type": "post",
                "risk_level": "INITIALIZING",
                "color": "#666",
            }], "edges": []},
            "exposure_map": user_footprint.exposure_map_stats(),
        }

    # Detect identity links
    threat = detect_identity_links(merged, baseline)
    web = build_exposure_map(threat, ocr_text, metadata)
    breach_report = generate_breach_report(threat, ocr_text, metadata)

    return {
        "status": "analyzed",
        "risk_level": threat["risk_level"],
        "max_similarity": threat["max_similarity"],
        "breach_probability": threat["breach_probability"],
        "entity_scores": threat["entity_scores"],
        "breach_report": breach_report,
        "signals": {
            "draft_text_length": len(draft_text),
            "ocr_text": ocr_text if ocr_text else None,
            "exif_metadata": metadata if metadata else None,
            "merged_length": len(merged),
        },
        "web": web,
        "exposure_map": user_footprint.exposure_map_stats(),
    }
