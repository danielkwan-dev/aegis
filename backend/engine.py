"""
Aegis — Evidence-Based Privacy Intelligence Engine
───────────────────────────────────────────────────
1. Entity extraction   (streets, businesses, times, coordinates)
2. OCR with high-value entity detection
3. EXIF metadata + time-of-day inference
4. User footprint      (in-memory, session-persistent)
5. Category-specific TF-IDF similarity (locations, timestamps, activities)
6. Entity correlation   (routine detection, static landmarks)
7. Vulnerability map    (evidence-based findings)
8. Exposure map graph   (nodes + edges for Hex)
"""

from __future__ import annotations

import io
import re
import uuid
from collections import Counter
from datetime import datetime, timezone

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


# ══════════════════════════════════════════════
# 1. Entity extraction
# ══════════════════════════════════════════════

STREET_SUFFIXES = [
    "st", "street", "ave", "avenue", "blvd", "boulevard", "rd", "road",
    "dr", "drive", "ln", "lane", "ct", "court", "pl", "place", "way",
    "pkwy", "parkway", "cir", "circle", "hwy", "highway",
]

BUSINESSES = [
    "starbucks", "equinox", "blue bottle", "peet's", "chipotle",
    "walgreens", "cvs", "target", "walmart", "costco", "trader joe's",
    "whole foods", "planet fitness", "24 hour fitness", "soulcycle",
    "mcdonald's", "subway", "dunkin", "panera", "chick-fil-a",
    "nopalito", "ferry building", "farmers market",
]

TIME_KEYWORDS = {
    "morning":   ("06:00", "11:59"),
    "noon":      ("11:00", "13:00"),
    "afternoon": ("12:00", "17:00"),
    "evening":   ("17:00", "21:00"),
    "night":     ("20:00", "23:59"),
    "dawn":      ("05:00", "07:00"),
    "dusk":      ("17:00", "19:00"),
    "lunch":     ("11:30", "13:30"),
    "breakfast":  ("06:00", "10:00"),
    "dinner":    ("17:00", "21:00"),
}

DAY_KEYWORDS = [
    "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday", "weekday", "weekend",
    "every day", "daily",
]

ACTIVITY_KEYWORDS = [
    "gym", "workout", "run", "jog", "yoga", "crossfit", "swim",
    "coffee", "commute", "train", "bus", "drive", "walk",
    "pickup", "drop off", "dropoff", "grocery", "shopping",
    "class", "meeting", "lunch break",
]

# Regex: "123 Main St" or "4th and Market"
STREET_PATTERN = re.compile(
    r'\b(\d+\s+\w+\s+(?:' + '|'.join(STREET_SUFFIXES) + r'))\b'
    r'|'
    r'\b(\w+\s+(?:and|&)\s+\w+)\b',
    re.IGNORECASE,
)

TIME_PATTERN = re.compile(
    r'\b(\d{1,2}:\d{2}\s*(?:am|pm)?)\b'
    r'|'
    r'\b(\d{1,2}\s*(?:am|pm))\b',
    re.IGNORECASE,
)

COORD_PATTERN = re.compile(
    r'(-?\d{1,3}\.\d{3,})\s*,\s*(-?\d{1,3}\.\d{3,})'
)


def extract_entities(text: str) -> dict:
    """Extract structured entities from free text."""
    text_lower = text.lower()

    # Streets
    streets = []
    for m in STREET_PATTERN.finditer(text):
        val = (m.group(1) or m.group(2)).strip()
        if len(val) > 4:
            streets.append(val)

    # Businesses
    found_businesses = []
    for biz in BUSINESSES:
        if biz in text_lower:
            found_businesses.append(biz.title())

    # Explicit times
    times = []
    for m in TIME_PATTERN.finditer(text):
        times.append((m.group(1) or m.group(2)).strip())

    # Time-of-day keywords (fallback when no GPS/explicit time)
    time_context = []
    for kw, (start, end) in TIME_KEYWORDS.items():
        if kw in text_lower:
            time_context.append({"keyword": kw, "window": f"{start}-{end}"})

    # Day keywords
    days = [d for d in DAY_KEYWORDS if d in text_lower]

    # Coordinates in text
    coordinates = []
    for m in COORD_PATTERN.finditer(text):
        coordinates.append({"lat": float(m.group(1)), "lon": float(m.group(2))})

    # Activities
    activities = [a for a in ACTIVITY_KEYWORDS if a in text_lower]

    return {
        "streets": streets,
        "businesses": found_businesses,
        "times": times,
        "time_context": time_context,
        "days": days,
        "coordinates": coordinates,
        "activities": activities,
    }


# ══════════════════════════════════════════════
# 2. OCR with high-value entity detection
# ══════════════════════════════════════════════

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


# ══════════════════════════════════════════════
# 3. EXIF metadata + time-of-day inference
# ══════════════════════════════════════════════

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


# ══════════════════════════════════════════════
# 4. User footprint (in-memory, session-persistent)
# ══════════════════════════════════════════════

def merge_signals(draft_text: str, ocr_text: str, metadata_text: str) -> str:
    parts = [p for p in [draft_text, ocr_text, metadata_text] if p]
    return " . ".join(parts)


class UserFootprint:
    """In-memory store. Persists for the lifetime of the server process."""

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
        entities: dict,
        metadata: dict | None = None,
        time_context: dict | None = None,
        label: str | None = None,
    ) -> dict:
        entry_id = f"fp_{uuid.uuid4().hex[:8]}"
        has_gps = bool(metadata and "gps_lat" in metadata)

        entry = {
            "id": entry_id,
            "label": label or self._generate_label(text),
            "text": text,
            "entities": entities,
            "metadata": metadata or {},
            "time_context": time_context,
            "has_gps": has_gps,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        self._entries.append(entry)
        return entry

    def clear(self) -> None:
        self._entries.clear()

    def all_streets(self) -> list[str]:
        out = []
        for e in self._entries:
            out.extend(e["entities"].get("streets", []))
        return out

    def all_coordinates(self) -> list[dict]:
        out = []
        for e in self._entries:
            out.extend(e["entities"].get("coordinates", []))
            if e["has_gps"]:
                out.append({"lat": e["metadata"]["gps_lat"], "lon": e["metadata"]["gps_lon"]})
        return out

    def exposure_map_stats(self) -> dict:
        all_streets = self.all_streets()
        all_coords = self.all_coordinates()
        all_businesses: list[str] = []
        all_activities: list[str] = []
        all_days: list[str] = []
        for e in self._entries:
            all_businesses.extend(e["entities"].get("businesses", []))
            all_activities.extend(e["entities"].get("activities", []))
            all_days.extend(e["entities"].get("days", []))

        return {
            "total_data_points": self.count,
            "unique_streets": len(set(s.lower() for s in all_streets)),
            "known_locations": len(all_coords),
            "unique_businesses": len(set(b.lower() for b in all_businesses)),
            "tracked_activities": len(set(all_activities)),
            "day_patterns": len(set(all_days)),
        }

    @staticmethod
    def _generate_label(text: str) -> str:
        words = text.split()
        preview = " ".join(words[:6])
        if len(words) > 6:
            preview += "..."
        return preview


# Global instance — session-persistent
user_footprint = UserFootprint()


# ══════════════════════════════════════════════
# 5. Category-specific TF-IDF similarity
# ══════════════════════════════════════════════

def _build_category_text(entry: dict) -> dict[str, str]:
    """Split an entry's text into category buckets for targeted similarity."""
    ents = entry.get("entities", {})
    meta = entry.get("metadata", {})
    tc = entry.get("time_context")

    location_parts = []
    location_parts.extend(ents.get("streets", []))
    location_parts.extend(ents.get("businesses", []))
    for c in ents.get("coordinates", []):
        location_parts.append(f"{c['lat']} {c['lon']}")
    if meta.get("gps_lat"):
        location_parts.append(f"{meta['gps_lat']} {meta['gps_lon']}")

    timestamp_parts = []
    timestamp_parts.extend(ents.get("times", []))
    timestamp_parts.extend(ents.get("days", []))
    for t in ents.get("time_context", []):
        timestamp_parts.append(t["keyword"])
    if tc:
        timestamp_parts.append(tc.get("period", ""))
        timestamp_parts.append(tc.get("day_of_week", ""))

    activity_parts = list(ents.get("activities", []))

    return {
        "locations": " ".join(location_parts),
        "timestamps": " ".join(timestamp_parts),
        "activities": " ".join(activity_parts),
    }


def compute_category_similarity(new_entry: dict, baseline: list[dict]) -> dict:
    """
    Compute TF-IDF cosine similarity per category (locations, timestamps, activities)
    plus a global similarity on full text.
    """
    categories = ["locations", "timestamps", "activities"]
    new_cats = _build_category_text(new_entry)

    results: dict[str, list[dict]] = {cat: [] for cat in categories}
    results["global"] = []

    # Global similarity
    all_texts = [e["text"] for e in baseline] + [new_entry["text"]]
    if len(all_texts) >= 2:
        try:
            vectorizer = TfidfVectorizer(stop_words="english")
            matrix = vectorizer.fit_transform(all_texts)
            sims = cosine_similarity(matrix[-1:], matrix[:-1]).flatten()
            for i, entry in enumerate(baseline):
                results["global"].append({
                    "entry_id": entry["id"],
                    "similarity": round(float(sims[i]), 4),
                })
        except ValueError:
            pass

    # Per-category similarity
    for cat in categories:
        new_text = new_cats[cat]
        if not new_text.strip():
            continue

        cat_texts = []
        cat_ids = []
        for entry in baseline:
            entry_cats = _build_category_text(entry)
            if entry_cats[cat].strip():
                cat_texts.append(entry_cats[cat])
                cat_ids.append(entry["id"])

        if not cat_texts:
            continue

        all_cat = cat_texts + [new_text]
        try:
            vectorizer = TfidfVectorizer(stop_words="english")
            matrix = vectorizer.fit_transform(all_cat)
            sims = cosine_similarity(matrix[-1:], matrix[:-1]).flatten()
            for i, eid in enumerate(cat_ids):
                results[cat].append({
                    "entry_id": eid,
                    "similarity": round(float(sims[i]), 4),
                })
        except ValueError:
            pass

    return results


# ══════════════════════════════════════════════
# 6. Entity correlation (routines + static landmarks)
# ══════════════════════════════════════════════

def detect_static_landmarks(footprint: UserFootprint) -> list[dict]:
    """
    If the same street name or coordinates appear in >20% of the footprint,
    tag them as Static Landmarks (likely Home or Work).
    """
    total = footprint.count
    if total < 2:
        return []

    threshold = 0.2
    landmarks = []

    # Street frequency
    street_counter: Counter = Counter()
    for entry in footprint.entries:
        seen = set()
        for s in entry["entities"].get("streets", []):
            key = s.lower().strip()
            if key not in seen:
                street_counter[key] += 1
                seen.add(key)

    for street, count in street_counter.items():
        if count / total >= threshold:
            landmarks.append({
                "type": "street",
                "value": street,
                "appearances": count,
                "percentage": round(count / total * 100, 1),
                "classification": "Home/Work Static Landmark",
            })

    # Coordinate clustering (within ~200m ≈ 0.002 degrees)
    coords = footprint.all_coordinates()
    if len(coords) >= 2:
        coord_clusters: list[dict] = []
        for c in coords:
            matched = False
            for cluster in coord_clusters:
                if abs(c["lat"] - cluster["lat"]) < 0.002 and abs(c["lon"] - cluster["lon"]) < 0.002:
                    cluster["count"] += 1
                    matched = True
                    break
            if not matched:
                coord_clusters.append({"lat": c["lat"], "lon": c["lon"], "count": 1})

        for cluster in coord_clusters:
            if cluster["count"] / total >= threshold:
                landmarks.append({
                    "type": "coordinates",
                    "value": {"lat": cluster["lat"], "lon": cluster["lon"]},
                    "appearances": cluster["count"],
                    "percentage": round(cluster["count"] / total * 100, 1),
                    "classification": "GPS Static Landmark",
                })

    return landmarks


def detect_routine_correlations(
    new_entities: dict,
    new_time_context: dict | None,
    footprint: UserFootprint,
) -> list[dict]:
    """
    Cross-reference new post entities with footprint patterns.
    Detect when location + time patterns form a predictable routine.
    """
    correlations = []
    fp_entries = footprint.entries

    # Check: does the new post share a street with footprint entries that have time patterns?
    new_streets = set(s.lower() for s in new_entities.get("streets", []))
    new_businesses = set(b.lower() for b in new_entities.get("businesses", []))
    new_period = new_time_context.get("period") if new_time_context else None
    new_days = set(d.lower() for d in new_entities.get("days", []))

    # Time-of-day from text keywords
    new_time_kws = set(t["keyword"] for t in new_entities.get("time_context", []))
    if new_period:
        new_time_kws.add(new_period)

    # Scan footprint for matching patterns
    location_time_hits: list[dict] = []
    for entry in fp_entries:
        e_streets = set(s.lower() for s in entry["entities"].get("streets", []))
        e_businesses = set(b.lower() for b in entry["entities"].get("businesses", []))
        e_days = set(d.lower() for d in entry["entities"].get("days", []))
        e_period = entry["time_context"]["period"] if entry.get("time_context") else None
        e_time_kws = set(t["keyword"] for t in entry["entities"].get("time_context", []))
        if e_period:
            e_time_kws.add(e_period)

        shared_streets = new_streets & e_streets
        shared_businesses = new_businesses & e_businesses
        shared_times = new_time_kws & e_time_kws
        shared_days = new_days & e_days

        if (shared_streets or shared_businesses) and (shared_times or shared_days):
            location_time_hits.append({
                "entry_id": entry["id"],
                "entry_label": entry["label"],
                "shared_locations": list(shared_streets | shared_businesses),
                "shared_times": list(shared_times | shared_days),
            })

    if location_time_hits:
        locs = set()
        times = set()
        for h in location_time_hits:
            locs.update(h["shared_locations"])
            times.update(h["shared_times"])

        correlations.append({
            "type": "routine_correlation",
            "evidence": f"Location-time pattern: {', '.join(locs)} during {', '.join(times)}",
            "matching_entries": len(location_time_hits),
            "details": location_time_hits,
        })

    # Check: same business across multiple days
    biz_entries: dict[str, int] = {}
    for entry in fp_entries:
        for b in entry["entities"].get("businesses", []):
            biz_entries[b.lower()] = biz_entries.get(b.lower(), 0) + 1

    for b in new_businesses:
        if biz_entries.get(b, 0) >= 2:
            correlations.append({
                "type": "frequent_visit",
                "evidence": f"You have visited '{b.title()}' in {biz_entries[b] + 1} posts (including this draft)",
                "business": b.title(),
                "total_visits": biz_entries[b] + 1,
            })

    return correlations


# ══════════════════════════════════════════════
# 7. Vulnerability map
# ══════════════════════════════════════════════

def generate_vulnerability_map(
    new_entities: dict,
    new_time_context: dict | None,
    ocr_entities: dict | None,
    metadata: dict,
    category_sims: dict,
    static_landmarks: list[dict],
    routine_correlations: list[dict],
    footprint: UserFootprint,
) -> list[dict]:
    """Generate evidence-based vulnerability findings."""
    findings: list[dict] = []

    # --- Routine leaks ---
    for corr in routine_correlations:
        if corr["type"] == "routine_correlation":
            findings.append({
                "category": "Routine Leak",
                "severity": "high",
                "finding": corr["evidence"],
                "evidence_count": corr["matching_entries"],
            })
        elif corr["type"] == "frequent_visit":
            findings.append({
                "category": "Routine Leak",
                "severity": "medium",
                "finding": corr["evidence"],
                "evidence_count": corr["total_visits"],
            })

    # --- Static landmark matches ---
    new_streets_lower = set(s.lower() for s in new_entities.get("streets", []))
    for lm in static_landmarks:
        if lm["type"] == "street" and lm["value"] in new_streets_lower:
            findings.append({
                "category": "Identity Leak",
                "severity": "critical",
                "finding": f"This street matches your '{lm['classification']}' cluster "
                           f"(appears in {lm['percentage']}% of your footprint)",
                "evidence_count": lm["appearances"],
            })

    # --- OCR high-value entities ---
    if ocr_entities:
        for hv in ocr_entities.get("high_value_ocr", []):
            if hv["type"] == "street_sign":
                # Check if it matches a known landmark
                matched_lm = any(
                    lm["type"] == "street" and hv["value"].lower().strip() in lm["value"]
                    for lm in static_landmarks
                )
                if matched_lm:
                    findings.append({
                        "category": "Identity Leak",
                        "severity": "critical",
                        "finding": f"OCR detected street sign '{hv['value']}' which matches your Home/Work cluster",
                        "evidence_count": 1,
                    })
                else:
                    findings.append({
                        "category": "Location Exposure",
                        "severity": "medium",
                        "finding": f"OCR detected street sign: '{hv['value']}'",
                        "evidence_count": 1,
                    })
            elif hv["type"] == "brand_name":
                findings.append({
                    "category": "Location Exposure",
                    "severity": "low",
                    "finding": f"OCR detected business name: '{hv['value']}'",
                    "evidence_count": 1,
                })

    # --- EXIF leaks ---
    if metadata.get("gps_lat"):
        findings.append({
            "category": "Metadata Leak",
            "severity": "critical",
            "finding": f"Image contains GPS coordinates ({metadata['gps_lat']}, {metadata['gps_lon']})",
            "evidence_count": 1,
        })

    if metadata.get("datetime_original"):
        findings.append({
            "category": "Metadata Leak",
            "severity": "medium",
            "finding": f"Image contains timestamp: {metadata['datetime_original']}",
            "evidence_count": 1,
        })

    # --- Category similarity warnings ---
    for cat in ["locations", "timestamps", "activities"]:
        sims = category_sims.get(cat, [])
        high_sims = [s for s in sims if s["similarity"] >= 0.15]
        if high_sims:
            top = max(high_sims, key=lambda x: x["similarity"])
            # Find the entry label
            entry_label = top["entry_id"]
            for e in footprint.entries:
                if e["id"] == top["entry_id"]:
                    entry_label = e["label"]
                    break
            findings.append({
                "category": f"{cat.title()} Correlation",
                "severity": "high" if top["similarity"] >= 0.3 else "medium",
                "finding": f"This post has {round(top['similarity'] * 100)}% {cat} similarity "
                           f"with footprint entry: '{entry_label}'",
                "evidence_count": len(high_sims),
            })

    # --- Time pattern aggregation ---
    if new_time_context and new_time_context.get("period"):
        period = new_time_context["period"]
        day = new_time_context.get("day_of_week", "")
        matching_period = sum(
            1 for e in footprint.entries
            if e.get("time_context") and e["time_context"].get("period") == period
        )
        if matching_period >= 2:
            day_str = f" on {day.title()}s" if day else ""
            findings.append({
                "category": "Routine Leak",
                "severity": "high",
                "finding": f"You have posted from this time window ({period}{day_str}) "
                           f"{matching_period + 1} times including this draft",
                "evidence_count": matching_period + 1,
            })

    # Sort: critical → high → medium → low
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(key=lambda f: severity_order.get(f["severity"], 4))

    return findings


# ══════════════════════════════════════════════
# 8. Exposure map graph (nodes + edges)
# ══════════════════════════════════════════════

ENTITY_COLORS = {
    "daily_route": "#f59e0b",
    "home": "#ef4444",
    "work": "#3b82f6",
    "family": "#a855f7",
    "general": "#6b7280",
}


def build_exposure_map(
    new_entities: dict,
    ocr_entities: dict | None,
    metadata: dict,
    category_sims: dict,
    static_landmarks: list[dict],
    footprint: UserFootprint,
) -> dict:
    nodes = []
    edges = []

    # Center: the new post
    has_critical = any(
        s["similarity"] >= 0.3
        for sims in category_sims.values()
        for s in sims
    )
    nodes.append({
        "id": "new_post",
        "label": "Your Draft Post",
        "type": "post",
        "color": "#ef4444" if has_critical else "#f59e0b",
    })

    # OCR node
    if ocr_entities and ocr_entities.get("high_value_ocr"):
        nodes.append({
            "id": "ocr_extract",
            "label": "Image Intelligence (OCR)",
            "type": "extraction",
            "high_value": ocr_entities["high_value_ocr"],
            "color": "#06b6d4",
        })
        edges.append({"source": "new_post", "target": "ocr_extract", "type": "contains", "weight": 1.0})

    # EXIF node
    if metadata.get("gps_lat") or metadata.get("datetime_original"):
        nodes.append({
            "id": "exif_metadata",
            "label": "EXIF Metadata",
            "type": "metadata",
            "details": metadata,
            "color": "#f43f5e",
        })
        edges.append({"source": "new_post", "target": "exif_metadata", "type": "leaks", "weight": 1.0})

    # Static landmark nodes
    for i, lm in enumerate(static_landmarks):
        lm_id = f"landmark_{i}"
        nodes.append({
            "id": lm_id,
            "label": f"Landmark: {lm['value'] if isinstance(lm['value'], str) else 'GPS cluster'}",
            "type": "landmark",
            "classification": lm["classification"],
            "percentage": lm["percentage"],
            "color": "#ef4444",
        })

    # Footprint entries connected by global similarity
    global_sims = {s["entry_id"]: s["similarity"] for s in category_sims.get("global", [])}
    for entry in footprint.entries:
        sim = global_sims.get(entry["id"], 0)
        if sim < 0.02:
            continue
        nodes.append({
            "id": entry["id"],
            "label": entry["label"],
            "type": "footprint",
            "similarity": sim,
            "color": "#ef4444" if sim >= 0.3 else "#f59e0b" if sim >= 0.15 else "#444",
        })
        edges.append({
            "source": "new_post",
            "target": entry["id"],
            "type": "identity_link",
            "weight": sim,
        })

    return {"nodes": nodes, "edges": edges}


# ══════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════

def ingest_data_point(text: str, image_bytes: bytes | None, label: str | None = None) -> dict:
    """Ingest a data point into the user footprint."""
    ocr_text = ""
    metadata: dict = {}
    if image_bytes:
        ocr_text = extract_ocr_text(image_bytes)
        metadata = extract_exif_metadata(image_bytes)

    metadata_text = metadata_to_text(metadata)
    merged = merge_signals(text, ocr_text, metadata_text)

    if not merged.strip():
        return {"status": "empty", "message": "No data to ingest."}

    # Extract entities from all text
    all_text = f"{text} {ocr_text}".strip()
    entities = extract_entities(all_text)
    time_ctx = infer_time_context(metadata, entities)

    entry = user_footprint.ingest(
        text=merged,
        entities=entities,
        metadata=metadata if metadata else None,
        time_context=time_ctx,
        label=label,
    )

    return {
        "status": "secured",
        "message": "Data Point Secured",
        "entry": entry,
        "detected_entities": {
            "streets": entities["streets"],
            "businesses": entities["businesses"],
            "times": entities["times"],
            "coordinates": entities["coordinates"],
        },
        "exposure_map": user_footprint.exposure_map_stats(),
    }


def analyze_threat(draft_text: str, image_bytes: bytes | None) -> dict:
    """Full evidence-based threat analysis."""
    ocr_text = ""
    metadata: dict = {}
    ocr_entities: dict | None = None
    if image_bytes:
        ocr_text = extract_ocr_text(image_bytes)
        metadata = extract_exif_metadata(image_bytes)
        if ocr_text:
            ocr_entities = extract_ocr_entities(ocr_text)

    metadata_text = metadata_to_text(metadata)
    merged = merge_signals(draft_text, ocr_text, metadata_text)

    if not merged.strip():
        return {
            "status": "empty",
            "message": "No text or image data to analyze.",
            "web": {"nodes": [], "edges": []},
            "exposure_map": user_footprint.exposure_map_stats(),
        }

    # Extract entities from the new post
    all_text = f"{draft_text} {ocr_text}".strip()
    new_entities = extract_entities(all_text)
    new_time_ctx = infer_time_context(metadata, new_entities)

    baseline = user_footprint.entries
    if len(baseline) == 0:
        return {
            "status": "initializing",
            "message": "No footprint data yet. Use /audit-ingest to build your exposure map first.",
            "detected_entities": {
                "streets": new_entities["streets"],
                "businesses": new_entities["businesses"],
                "times": new_entities["times"],
                "coordinates": new_entities["coordinates"],
            },
            "vulnerability_map": [],
            "breach_probability": 0.0,
            "web": {"nodes": [{"id": "new_post", "label": "Your Draft Post", "type": "post", "color": "#666"}], "edges": []},
            "exposure_map": user_footprint.exposure_map_stats(),
        }

    # Build temporary entry dict for category similarity
    new_entry = {
        "id": "new_post",
        "text": merged,
        "entities": new_entities,
        "metadata": metadata,
        "time_context": new_time_ctx,
    }

    # Category-specific similarity
    category_sims = compute_category_similarity(new_entry, baseline)

    # Entity correlations
    static_landmarks = detect_static_landmarks(user_footprint)
    routine_correlations = detect_routine_correlations(new_entities, new_time_ctx, user_footprint)

    # Vulnerability map
    vuln_map = generate_vulnerability_map(
        new_entities, new_time_ctx, ocr_entities, metadata,
        category_sims, static_landmarks, routine_correlations, user_footprint,
    )

    # Breach probability from evidence
    severity_weights = {"critical": 25.0, "high": 15.0, "medium": 8.0, "low": 3.0}
    raw_score = sum(severity_weights.get(f["severity"], 0) for f in vuln_map)
    breach_probability = round(min(raw_score, 100.0), 1)

    # Build graph
    web = build_exposure_map(new_entities, ocr_entities, metadata, category_sims, static_landmarks, user_footprint)

    # Category similarity summaries
    cat_summaries = {}
    for cat in ["locations", "timestamps", "activities"]:
        sims = category_sims.get(cat, [])
        if sims:
            top_sim = max(s["similarity"] for s in sims)
            cat_summaries[cat] = round(top_sim, 4)

    return {
        "status": "analyzed",
        "detected_entities": {
            "streets": new_entities["streets"],
            "businesses": new_entities["businesses"],
            "times": new_entities["times"],
            "coordinates": new_entities["coordinates"],
        },
        "category_similarity": cat_summaries,
        "breach_probability": breach_probability,
        "vulnerability_map": vuln_map,
        "static_landmarks": static_landmarks,
        "signals": {
            "draft_text_length": len(draft_text),
            "ocr_text": ocr_text if ocr_text else None,
            "ocr_high_value": ocr_entities.get("high_value_ocr") if ocr_entities else None,
            "exif_metadata": metadata if metadata else None,
            "time_context": new_time_ctx,
            "merged_length": len(merged),
        },
        "web": web,
        "exposure_map": user_footprint.exposure_map_stats(),
    }
