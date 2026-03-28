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
from sklearn.cluster import KMeans
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
    "every day", "daily", "tomorrow", "today",
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

# Named places: "Fleetwood Park", "Central Library", "Lincoln Elementary"
PLACE_SUFFIXES = [
    "park", "plaza", "square", "center", "centre", "mall", "station",
    "library", "elementary", "school", "church", "temple", "mosque",
    "hospital", "clinic", "beach", "pier", "wharf", "bridge",
    "market", "garden", "gardens", "field", "arena", "stadium",
]

PLACE_PATTERN = re.compile(
    r'\b((?:\w+\s+){1,3}(?:' + '|'.join(PLACE_SUFFIXES) + r'))\b',
    re.IGNORECASE,
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

    # Named places (parks, stations, schools, etc.)
    places = []
    noise_words = {"the", "a", "an", "at", "to", "in", "on", "my", "for", "and", "or", "is", "was",
                    "heading", "going", "went", "go", "from", "near", "by", "this", "that", "walk"}
    for m in PLACE_PATTERN.finditer(text):
        val = m.group(0).strip()
        # Remove leading noise words: "at Fleetwood Park" → "Fleetwood Park"
        words = val.split()
        while words and words[0].lower() in noise_words:
            words.pop(0)
        cleaned = " ".join(words)
        if len(cleaned) > 3 and len(cleaned.split()) >= 2:
            places.append(cleaned)

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
        "places": places,
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
    location_parts.extend(ents.get("places", []))
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


def _infer_associated_entities(keyword: str, category: str, footprint: UserFootprint) -> dict:
    """
    Given a keyword (e.g. 'coffee') and its category (e.g. 'activities'),
    scan the footprint to find what locations, times, and activities
    co-occur with that keyword. Returns inferred associations.
    """
    co_streets: Counter = Counter()
    co_businesses: Counter = Counter()
    co_times: Counter = Counter()
    co_activities: Counter = Counter()
    match_count = 0

    kw_lower = keyword.lower()

    for entry in footprint.entries:
        ents = entry.get("entities", {})
        text_lower = entry.get("text", "").lower()

        # Check if this entry contains the keyword
        has_keyword = False
        if category == "activities" and kw_lower in [a.lower() for a in ents.get("activities", [])]:
            has_keyword = True
        elif category == "businesses" and kw_lower in [b.lower() for b in ents.get("businesses", [])]:
            has_keyword = True
        elif category == "streets" and kw_lower in [s.lower() for s in ents.get("streets", [])]:
            has_keyword = True
        elif kw_lower in text_lower:
            has_keyword = True

        if not has_keyword:
            continue

        match_count += 1

        for s in ents.get("streets", []):
            co_streets[s.lower()] += 1
        for b in ents.get("businesses", []):
            co_businesses[b.lower()] += 1
        for t in ents.get("times", []):
            co_times[t.lower()] += 1
        tc = entry.get("time_context")
        if tc and tc.get("period"):
            co_times[tc["period"]] += 1
        for a in ents.get("activities", []):
            if a.lower() != kw_lower:
                co_activities[a.lower()] += 1

    return {
        "keyword": keyword,
        "category": category,
        "match_count": match_count,
        "streets": dict(co_streets),
        "businesses": dict(co_businesses),
        "times": dict(co_times),
        "activities": dict(co_activities),
    }


def detect_routine_correlations(
    new_entities: dict,
    new_time_context: dict | None,
    footprint: UserFootprint,
) -> list[dict]:
    """
    Cross-reference new post entities with footprint patterns.
    Detect when location + time patterns form a predictable routine.
    Includes INFERENCE: if the draft mentions 'coffee', and coffee always
    happens at Market Street at 7am, that's an inferred routine leak.
    """
    correlations = []
    fp_entries = footprint.entries

    new_streets = set(s.lower() for s in new_entities.get("streets", []))
    new_businesses = set(b.lower() for b in new_entities.get("businesses", []))
    new_activities = set(a.lower() for a in new_entities.get("activities", []))
    new_period = new_time_context.get("period") if new_time_context else None
    new_days = set(d.lower() for d in new_entities.get("days", []))

    new_time_kws = set(t["keyword"] for t in new_entities.get("time_context", []))
    if new_period:
        new_time_kws.add(new_period)

    # ── Direct correlations (exact keyword matches) ──
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

    # ── INFERENCE: Activity/keyword → associated locations & times ──
    # If the draft mentions "coffee" and coffee always happens at Market St
    # at 7am in the baseline, that's an inferred leak even without the
    # user explicitly typing "Market Street" or "morning".
    all_draft_keywords = new_activities | new_businesses | new_streets
    for kw in all_draft_keywords:
        cat = "activities" if kw in new_activities else "businesses" if kw in new_businesses else "streets"
        assoc = _infer_associated_entities(kw, cat, footprint)

        if assoc["match_count"] < 1:
            continue

        # Find inferred locations the draft didn't mention
        inferred_streets = {s for s, c in assoc["streets"].items() if c >= 1} - new_streets
        inferred_biz = {b for b, c in assoc["businesses"].items() if c >= 1} - new_businesses
        inferred_times = {t for t, c in assoc["times"].items() if c >= 1} - new_time_kws

        inferred_locs = inferred_streets | inferred_biz
        if not inferred_locs and not inferred_times:
            continue

        # Build evidence string
        parts = []
        if inferred_locs:
            loc_list = ", ".join(l.title() for l in list(inferred_locs)[:3])
            parts.append(f"you always do that at {loc_list}")
        if inferred_times:
            time_list = ", ".join(list(inferred_times)[:3])
            parts.append(f"usually in the {time_list}")

        evidence = (
            f"Your draft mentions '{kw}'. Based on your history, "
            + " and ".join(parts)
            + f". Even without naming these directly, a stalker who's studied your "
            f"posts would know exactly where and when you mean."
        )

        correlations.append({
            "type": "inferred_routine",
            "evidence": evidence,
            "keyword": kw,
            "inferred_locations": list(inferred_locs),
            "inferred_times": list(inferred_times),
            "matching_entries": assoc["match_count"],
        })

    # ── Frequent business visits ──
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
        elif corr["type"] == "inferred_routine":
            # Inferred = draft doesn't name the location/time, but baseline
            # shows they always co-occur with the mentioned keyword
            severity = "critical" if corr["matching_entries"] >= 2 else "high"
            findings.append({
                "category": "Inferred Routine",
                "severity": severity,
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
# 8. Conclusion Engine — Pattern Aggregator + NLG
# ══════════════════════════════════════════════

def _compute_ocr_weighted_activity_sim(
    activity_text: str,
    entry_activity_text: str,
    ocr_boost: float = 2.0,
    ocr_terms: set[str] | None = None,
) -> float:
    """
    TF-IDF cosine similarity for activities, with OCR-sourced terms
    receiving a multiplied weight in the TF-IDF vector.
    """
    if not activity_text.strip() or not entry_activity_text.strip():
        return 0.0

    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform([entry_activity_text, activity_text])
        base_sim = float(cosine_similarity(matrix[1:], matrix[:1]).flatten()[0])

        # Boost if OCR terms appear in both texts
        if ocr_terms:
            entry_lower = entry_activity_text.lower()
            overlap = sum(1 for t in ocr_terms if t in entry_lower)
            if overlap > 0:
                base_sim = min(base_sim + (overlap * 0.15 * ocr_boost), 1.0)

        return round(base_sim, 4)
    except ValueError:
        return 0.0


def scan_entity_triplets(footprint: UserFootprint, ocr_terms: set[str] | None = None) -> list[dict]:
    """
    Scan the footprint for recurring Entity Triplets: Time + Location + Activity.
    A triplet forms when:
      - A location appears in >2 entries
      - Those same entries share a time signal
      - Activity similarity across those entries is >0.7 (OCR-weighted)
    """
    entries = footprint.entries
    if len(entries) < 3:
        return []

    triplets: list[dict] = []

    # Build location → entry index mapping
    location_entries: dict[str, list[int]] = {}
    for i, entry in enumerate(entries):
        locs = set()
        for s in entry["entities"].get("streets", []):
            locs.add(s.lower().strip())
        for p in entry["entities"].get("places", []):
            locs.add(p.lower().strip())
        for b in entry["entities"].get("businesses", []):
            locs.add(b.lower().strip())
        if entry["has_gps"]:
            locs.add(f"gps_{entry['metadata']['gps_lat']}_{entry['metadata']['gps_lon']}")
        for loc in locs:
            if loc not in location_entries:
                location_entries[loc] = []
            location_entries[loc].append(i)

    for location, indices in location_entries.items():
        if len(indices) < 2:
            continue

        # Find shared time signals among these entries
        time_signals: Counter = Counter()
        day_signals: Counter = Counter()
        for idx in indices:
            e = entries[idx]
            tc = e.get("time_context")
            if tc and tc.get("period"):
                time_signals[tc["period"]] += 1
            if tc and tc.get("day_of_week"):
                day_signals[tc["day_of_week"]] += 1
            for kw in e["entities"].get("time_context", []):
                time_signals[kw["keyword"]] += 1
            for d in e["entities"].get("days", []):
                day_signals[d.lower()] += 1

        # Need at least 2 entries sharing a time
        shared_times = {t: c for t, c in time_signals.items() if c >= 2}
        shared_days = {d: c for d, c in day_signals.items() if c >= 2}

        if not shared_times and not shared_days:
            continue

        # Check activity similarity across the entries at this location+time
        activity_texts = []
        for idx in indices:
            e = entries[idx]
            acts = e["entities"].get("activities", [])
            act_text = " ".join(acts) if acts else ""
            # Also pull activity-like terms from the full text
            act_text += " " + " ".join(
                w for w in e["text"].lower().split()
                if w in set(ACTIVITY_KEYWORDS)
            )
            activity_texts.append(act_text.strip())

        # Pairwise activity similarity (OCR-weighted)
        if len(activity_texts) >= 2 and any(t for t in activity_texts):
            non_empty = [(i, t) for i, t in enumerate(activity_texts) if t]
            if len(non_empty) >= 2:
                avg_sim = 0.0
                count = 0
                for a_idx in range(len(non_empty)):
                    for b_idx in range(a_idx + 1, len(non_empty)):
                        sim = _compute_ocr_weighted_activity_sim(
                            non_empty[a_idx][1], non_empty[b_idx][1],
                            ocr_terms=ocr_terms,
                        )
                        avg_sim += sim
                        count += 1
                avg_sim = avg_sim / count if count > 0 else 0.0

                # Threshold: activity similarity > 0.7 OR strong location+time pattern (>2 entries)
                activity_match = avg_sim > 0.7
                strong_pattern = len(indices) >= 3
            else:
                avg_sim = 0.0
                activity_match = False
                strong_pattern = len(indices) >= 3
        else:
            avg_sim = 0.0
            activity_match = False
            strong_pattern = len(indices) >= 3

        if activity_match or strong_pattern:
            # Collect representative activities
            all_acts: list[str] = []
            for idx in indices:
                all_acts.extend(entries[idx]["entities"].get("activities", []))
            top_activity = Counter(all_acts).most_common(1)
            activity_name = top_activity[0][0] if top_activity else None

            best_time = max(shared_times, key=shared_times.get) if shared_times else None
            best_day = max(shared_days, key=shared_days.get) if shared_days else None

            triplets.append({
                "location": location,
                "time": best_time,
                "day": best_day,
                "activity": activity_name,
                "entry_count": len(indices),
                "activity_similarity": round(avg_sim, 4),
                "time_matches": dict(shared_times),
                "day_matches": dict(shared_days),
            })

    # Sort by entry count (strongest patterns first)
    triplets.sort(key=lambda t: t["entry_count"], reverse=True)
    return triplets


def generate_conclusion(
    triplets: list[dict],
    vulnerability_map: list[dict],
    static_landmarks: list[dict],
    breach_probability: float,
) -> str:
    """
    Synthesize entity triplets and vulnerability findings into a
    concrete, conversational conclusion that reads like a stalker's notes.
    """
    if not triplets and not vulnerability_map:
        return "Baseline established. No recurring routine detected yet."

    lines: list[str] = []

    # --- Triplet-based: conversational "here's what we know about you" ---
    for triplet in triplets:
        loc = triplet["location"].title()
        time = triplet["time"]
        day = triplet["day"]
        activity = triplet["activity"]
        count = triplet["entry_count"]

        if day and time and activity:
            lines.append(
                f"You {activity} at {loc} every {day.title()} in the {time}. "
                f"This appeared in {count} of your posts."
            )
        elif time and activity:
            lines.append(
                f"You {activity} at {loc} in the {time} — this shows up "
                f"in {count} of your posts."
            )
        elif day and activity:
            lines.append(
                f"Every {day.title()}, you {activity} at {loc}."
            )
        elif time:
            lines.append(
                f"You're regularly at {loc} in the {time}. "
                f"This showed up in {count} of your posts."
            )
        elif activity:
            lines.append(
                f"You frequently {activity} at {loc}."
            )
        else:
            lines.append(
                f"{loc} keeps showing up in your posts — {count} times so far."
            )

    # --- Static landmarks: "you're always at X" ---
    for lm in static_landmarks:
        if lm["type"] == "street":
            name = lm["value"].title()
            pct = lm["percentage"]
            if pct >= 60:
                lines.append(
                    f"You're always at {name} — it appears in {pct}% of your footprint. "
                    f"This is almost certainly near where you live or work."
                )
            else:
                lines.append(
                    f"{name} appears in {pct}% of your posts. "
                    f"Someone watching you would flag this as a regular stop."
                )
        elif lm["type"] == "coordinates":
            lines.append(
                f"Your photos keep pinging the same GPS coordinates "
                f"({lm['value']['lat']}, {lm['value']['lon']}). "
                f"That's in {lm['percentage']}% of your footprint."
            )

    # --- Critical vulnerability callouts ---
    critical = [v for v in vulnerability_map if v["severity"] == "critical"]
    for v in critical:
        if v["category"] == "Routine Leak":
            lines.append(v["finding"])

    # --- Fallback when no triplets but we have vulns ---
    if not triplets and vulnerability_map:
        high = [v for v in vulnerability_map if v["severity"] in ("critical", "high")]
        if high:
            lines.append(
                f"We found {len(high)} high-severity pattern(s) in your posts. "
                f"Your digital footprint reveals exploitable routines."
            )

    # --- Bottom-line risk statement ---
    if breach_probability >= 70:
        lines.append(
            f"Bottom line: a stranger could predict where you'll be and when, "
            f"just from your public posts. Exposure score: {breach_probability}%."
        )
    elif breach_probability >= 40:
        lines.append(
            f"Moderate exposure ({breach_probability}%). Several of your posts "
            f"line up enough to sketch a partial routine."
        )

    if not lines:
        return "Baseline established. No recurring routine detected yet."

    return "\n\n".join(lines)


# ══════════════════════════════════════════════
# 9. Exposure map graph (nodes + edges)
# ══════════════════════════════════════════════

ENTITY_COLORS = {
    "daily_route": "#f59e0b",
    "home": "#ef4444",
    "work": "#3b82f6",
    "family": "#a855f7",
    "general": "#6b7280",
}


# ══════════════════════════════════════════════
# 9. K-Means Routine Clustering
# ══════════════════════════════════════════════

# High-risk anchor terms that flag a cluster as the "Target Cluster"
HIGH_RISK_ANCHORS = {
    # Location anchors (streets, landmarks)
    "market", "elm", "broadway", "4th", "main", "park", "station",
    # Temporal anchors
    "morning", "7am", "7:15", "7:30", "8am", "commute", "daily",
    "monday", "tuesday", "wednesday", "thursday", "friday",
    # Activity anchors
    "coffee", "starbucks", "gym", "office", "bus", "train", "routine",
}


def cluster_routines(
    footprint: UserFootprint,
    draft_text: str,
    n_clusters: int = 3,
) -> dict | None:
    """
    On-the-fly K-Means routine clustering.

    1. Vectorize all historical captions + draft via TF-IDF
    2. Fit KMeans on historical vectors only
    3. Profile each cluster for high-risk anchors
    4. Predict which cluster the draft falls into
    5. Return cluster analysis with threat assessment
    """
    baseline = footprint.entries
    if len(baseline) < n_clusters:
        return None  # Not enough data to form meaningful clusters

    # ── Data Prep ──
    historical_texts = [entry["text"] for entry in baseline]
    all_texts = historical_texts + [draft_text]

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=500,
            ngram_range=(1, 2),
        )
        tfidf_matrix = vectorizer.fit_transform(all_texts)
    except ValueError:
        return None  # Empty vocabulary

    feature_names = vectorizer.get_feature_names_out()
    historical_vectors = tfidf_matrix[:-1]
    draft_vector = tfidf_matrix[-1:]

    # ── Training Step (.fit) ──
    actual_k = min(n_clusters, len(baseline))
    model = KMeans(n_clusters=actual_k, random_state=42, n_init=10)
    model.fit(historical_vectors)

    # ── Cluster Profiling ──
    cluster_labels = model.labels_
    cluster_profiles: list[dict] = []

    for cid in range(actual_k):
        member_indices = [i for i, lbl in enumerate(cluster_labels) if lbl == cid]
        member_entries = [baseline[i] for i in member_indices]
        member_texts = " ".join(e["text"] for e in member_entries).lower()

        # Score cluster by how many high-risk anchors it contains
        anchor_hits = [a for a in HIGH_RISK_ANCHORS if a in member_texts]
        risk_score = len(anchor_hits) / max(len(HIGH_RISK_ANCHORS), 1)

        # Extract top TF-IDF terms for this cluster
        centroid = model.cluster_centers_[cid]
        top_term_indices = centroid.argsort()[-8:][::-1]
        top_terms = [str(feature_names[i]) for i in top_term_indices]

        # Infer a cluster label from content
        all_streets = []
        all_times = []
        all_activities = []
        for entry in member_entries:
            ents = entry.get("entities", {})
            all_streets.extend(ents.get("streets", []))
            all_streets.extend(ents.get("places", []))
            all_times.extend(ents.get("times", []))
            all_activities.extend(ents.get("activities", []))
            tc = entry.get("time_context")
            if tc and isinstance(tc, dict):
                period = tc.get("period", "")
                if period:
                    all_times.append(period)

        # Auto-name the cluster
        top_location = Counter(all_streets).most_common(1)
        top_time = Counter(all_times).most_common(1)
        top_activity = Counter(all_activities).most_common(1)

        name_parts = []
        if top_time:
            name_parts.append(top_time[0][0].title())
        if top_location:
            name_parts.append(top_location[0][0].title())
        if top_activity:
            name_parts.append(top_activity[0][0].title())
        cluster_name = " ".join(name_parts) if name_parts else f"Routine {cid + 1}"

        cluster_profiles.append({
            "cluster_id": cid,
            "name": cluster_name,
            "size": len(member_indices),
            "entry_ids": [baseline[i]["id"] for i in member_indices],
            "risk_score": round(risk_score, 3),
            "anchor_hits": anchor_hits[:6],
            "top_terms": top_terms,
        })

    # ── Identify Target Cluster ──
    target_cluster = max(cluster_profiles, key=lambda c: c["risk_score"])

    # ── Prediction Step (.predict) ──
    draft_cluster_id = int(model.predict(draft_vector)[0])
    draft_cluster = cluster_profiles[draft_cluster_id]

    # Distance from draft to each centroid (lower = closer match)
    distances = model.transform(draft_vector)[0]
    draft_distance = float(distances[draft_cluster_id])
    max_distance = float(distances.max())
    cluster_confidence = round(1.0 - (draft_distance / max(max_distance, 0.001)), 3)

    # ── Threat Assessment ──
    draft_hits_target = draft_cluster_id == target_cluster["cluster_id"]

    return {
        "n_clusters": actual_k,
        "clusters": cluster_profiles,
        "target_cluster": target_cluster,
        "draft_cluster_id": draft_cluster_id,
        "draft_cluster_name": draft_cluster["name"],
        "draft_hits_target": draft_hits_target,
        "cluster_confidence": cluster_confidence,
        "target_risk_score": target_cluster["risk_score"],
    }


def _summarize_entry(entry: dict) -> tuple[str, str]:
    """Build a short label and a longer detail string for a footprint entry."""
    ents = entry.get("entities", {})
    streets = ents.get("streets", [])
    businesses = ents.get("businesses", [])
    times = ents.get("times", [])
    activities = ents.get("activities", [])
    tc = entry.get("time_context") or {}

    # Build a concise label like "7am coffee, Market St"
    parts = []
    if times:
        parts.append(times[0])
    elif tc.get("period"):
        parts.append(tc["period"])
    if activities:
        parts.append(activities[0])
    if businesses:
        parts.append(businesses[0])
    if streets:
        parts.append(streets[0])

    label = ", ".join(parts) if parts else entry.get("label", entry["id"])

    # Build a longer detail string
    detail_parts = []
    if streets:
        detail_parts.append(f"Streets: {', '.join(streets)}")
    if businesses:
        detail_parts.append(f"Places: {', '.join(businesses)}")
    if times:
        detail_parts.append(f"Time: {', '.join(times)}")
    if activities:
        detail_parts.append(f"Activity: {', '.join(activities)}")

    detail = ". ".join(detail_parts) if detail_parts else entry.get("label", "")

    return label, detail


def _edge_label_for_entries(entry_a: dict, entry_b_entities: dict) -> str:
    """Find what two entries have in common for the edge label."""
    ents_a = entry_a.get("entities", {})
    shared = []

    for street in ents_a.get("streets", []):
        if street in entry_b_entities.get("streets", []):
            shared.append(street)
    for biz in ents_a.get("businesses", []):
        if biz in entry_b_entities.get("businesses", []):
            shared.append(biz)
    for time in ents_a.get("times", []):
        if time in entry_b_entities.get("times", []):
            shared.append(time)
    for act in ents_a.get("activities", []):
        if act in entry_b_entities.get("activities", []):
            shared.append(act)

    if shared:
        return "both mention " + ", ".join(shared[:3])
    return "identity link"


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

    # Build a descriptive label for the draft
    draft_parts = []
    if new_entities.get("times"):
        draft_parts.append(new_entities["times"][0])
    if new_entities.get("activities"):
        draft_parts.append(new_entities["activities"][0])
    if new_entities.get("streets"):
        draft_parts.append(new_entities["streets"][0])
    draft_label = "Your Draft: " + ", ".join(draft_parts) if draft_parts else "Your Draft Post"

    nodes.append({
        "id": "new_post",
        "label": draft_label,
        "type": "post",
        "color": "#ef4444" if has_critical else "#f59e0b",
        "detail": f"Entities found: {', '.join(draft_parts)}" if draft_parts else "No specific entities extracted",
    })

    # OCR node
    if ocr_entities and ocr_entities.get("high_value_ocr"):
        ocr_items = [h["value"] for h in ocr_entities["high_value_ocr"]]
        nodes.append({
            "id": "ocr_extract",
            "label": f"OCR: {', '.join(ocr_items[:2])}",
            "type": "extraction",
            "high_value": ocr_entities["high_value_ocr"],
            "color": "#06b6d4",
            "detail": f"OCR detected in image: {', '.join(ocr_items)}",
        })
        edges.append({
            "source": "new_post", "target": "ocr_extract",
            "type": "contains", "weight": 1.0,
            "label": "image scan",
        })

    # EXIF node
    if metadata.get("gps_lat") or metadata.get("datetime_original"):
        exif_parts = []
        if metadata.get("gps_lat"):
            exif_parts.append(f"GPS: {metadata['gps_lat']}, {metadata.get('gps_lon', '?')}")
        if metadata.get("datetime_original"):
            exif_parts.append(f"Taken: {metadata['datetime_original']}")
        nodes.append({
            "id": "exif_metadata",
            "label": "EXIF: " + ", ".join(exif_parts[:1]),
            "type": "metadata",
            "details": metadata,
            "color": "#f43f5e",
            "detail": ". ".join(exif_parts),
        })
        edges.append({
            "source": "new_post", "target": "exif_metadata",
            "type": "leaks", "weight": 1.0,
            "label": "metadata leak",
        })

    # Static landmark nodes
    for i, lm in enumerate(static_landmarks):
        lm_id = f"landmark_{i}"
        val = lm["value"] if isinstance(lm["value"], str) else "GPS cluster"
        nodes.append({
            "id": lm_id,
            "label": f"{val.title()} ({lm['percentage']}%)",
            "type": "landmark",
            "classification": lm["classification"],
            "percentage": lm["percentage"],
            "color": "#ef4444",
            "risk_level": min(lm["percentage"] / 100.0, 1.0),
            "weight": min(lm["percentage"] / 100.0, 1.0),
            "detail": f"{val.title()} appears in {lm['percentage']}% of posts. Classified as: {lm['classification']}",
        })

    # Footprint entries connected by global similarity
    global_sims = {s["entry_id"]: s["similarity"] for s in category_sims.get("global", [])}
    for entry in footprint.entries:
        sim = global_sims.get(entry["id"], 0)
        if sim < 0.02:
            continue

        label, detail = _summarize_entry(entry)
        edge_label = _edge_label_for_entries(entry, new_entities)

        nodes.append({
            "id": entry["id"],
            "label": label,
            "type": "footprint",
            "similarity": sim,
            "color": "#ef4444" if sim >= 0.3 else "#f59e0b" if sim >= 0.15 else "#444",
            "detail": detail,
        })
        edges.append({
            "source": "new_post",
            "target": entry["id"],
            "type": "identity_link",
            "weight": sim,
            "label": edge_label,
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

    # Run conclusion engine on updated footprint
    triplets = scan_entity_triplets(user_footprint)
    landmarks = detect_static_landmarks(user_footprint)
    conclusion = generate_conclusion(triplets, [], landmarks, 0.0)

    return {
        "status": "secured",
        "message": "Data Point Secured",
        "entry": entry,
        "detected_entities": {
            "streets": entities["streets"],
            "places": entities["places"],
            "businesses": entities["businesses"],
            "times": entities["times"],
            "coordinates": entities["coordinates"],
        },
        "exposure_map": user_footprint.exposure_map_stats(),
        "final_conclusion": conclusion,
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
            "final_conclusion": "Baseline established. No recurring routine detected yet.",
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

    # Conclusion Engine — scan for entity triplets with OCR weighting
    ocr_terms: set[str] | None = None
    if ocr_text:
        ocr_terms = set(w.lower() for w in ocr_text.split() if len(w) > 3)
    triplets = scan_entity_triplets(user_footprint, ocr_terms=ocr_terms)
    conclusion = generate_conclusion(triplets, vuln_map, static_landmarks, breach_probability)

    # ── K-Means Routine Clustering ──
    clustering = cluster_routines(user_footprint, merged)

    # If clustering produced results, enhance breach probability and conclusion
    if clustering and clustering["draft_hits_target"]:
        # Boost breach probability when draft matches the target cluster
        cluster_boost = clustering["cluster_confidence"] * 20.0
        breach_probability = round(min(breach_probability + cluster_boost, 100.0), 1)

        # Override conclusion with ML-enriched conversational version
        tc = clustering["target_cluster"]
        anchors = ", ".join(tc["anchor_hits"][:5])
        top_terms = ", ".join(tc["top_terms"][:5])
        conclusion = (
            f"[SIGNAL DETECTED]: We grouped your past posts into "
            f"{clustering['n_clusters']} routines using K-Means clustering. "
            f"This draft matches your \"{clustering['draft_cluster_name']}\" routine "
            f"with {clustering['cluster_confidence']*100:.0f}% confidence.\n\n"
            f"[LEAK SOURCE]: {tc['size']} of your previous posts follow the same "
            f"pattern — keywords like {anchors} keep appearing together. "
            f"{conclusion}\n\n"
            f"[FORECAST]: Someone studying your posts would already know about "
            f"this routine. Posting this draft confirms it and makes the pattern "
            f"even easier to exploit. Remove specific locations, times, and "
            f"habitual language before posting."
        )
    elif clustering:
        # Draft didn't match the target cluster but we still have cluster data
        conclusion = (
            f"[SIGNAL DETECTED]: We found {clustering['n_clusters']} routines "
            f"in your post history. This draft was mapped to your "
            f"\"{clustering['draft_cluster_name']}\" routine "
            f"({clustering['cluster_confidence']*100:.0f}% confidence).\n\n"
            f"[LEAK SOURCE]: {conclusion}\n\n"
            f"[FORECAST]: This draft doesn't expose your highest-risk routine "
            f"(\"{clustering['target_cluster']['name']}\"), but it still leaks "
            f"behavioral patterns. Be careful with location and time references."
        )

    # Build graph
    web = build_exposure_map(new_entities, ocr_entities, metadata, category_sims, static_landmarks, user_footprint)

    # Inject cluster_id into graph nodes
    if clustering:
        cluster_entry_map: dict[str, int] = {}
        for cp in clustering["clusters"]:
            for eid in cp["entry_ids"]:
                cluster_entry_map[eid] = cp["cluster_id"]

        for node in web["nodes"]:
            nid = node["id"]
            if nid in cluster_entry_map:
                node["cluster_id"] = cluster_entry_map[nid]
                node["cluster_name"] = next(
                    (c["name"] for c in clustering["clusters"] if c["cluster_id"] == cluster_entry_map[nid]),
                    None,
                )
            elif nid == "new_post":
                node["cluster_id"] = clustering["draft_cluster_id"]
                node["cluster_name"] = clustering["draft_cluster_name"]

    # Category similarity summaries
    cat_summaries = {}
    for cat in ["locations", "timestamps", "activities"]:
        sims = category_sims.get(cat, [])
        if sims:
            top_sim = max(s["similarity"] for s in sims)
            cat_summaries[cat] = round(top_sim, 4)

    result = {
        "status": "analyzed",
        "detected_entities": {
            "streets": new_entities["streets"],
            "places": new_entities["places"],
            "businesses": new_entities["businesses"],
            "times": new_entities["times"],
            "coordinates": new_entities["coordinates"],
        },
        "category_similarity": cat_summaries,
        "breach_probability": breach_probability,
        "vulnerability_map": vuln_map,
        "static_landmarks": static_landmarks,
        "entity_triplets": triplets,
        "final_conclusion": conclusion,
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

    # Attach clustering metadata
    if clustering:
        result["clustering"] = {
            "n_clusters": clustering["n_clusters"],
            "draft_cluster_id": clustering["draft_cluster_id"],
            "draft_cluster_name": clustering["draft_cluster_name"],
            "draft_hits_target": clustering["draft_hits_target"],
            "cluster_confidence": clustering["cluster_confidence"],
            "clusters": [
                {
                    "id": c["cluster_id"],
                    "name": c["name"],
                    "size": c["size"],
                    "risk_score": c["risk_score"],
                    "top_terms": c["top_terms"],
                    "is_target": c["cluster_id"] == clustering["target_cluster"]["cluster_id"],
                }
                for c in clustering["clusters"]
            ],
        }

    return result
