"""Regex/keyword-list entity extraction.

This is the original hackathon extractor. It's kept intentionally — once the
fine-tuned NER model lands, this becomes the baseline it gets benchmarked
against (see ml_training/benchmark.py), not dead code.
"""

from __future__ import annotations

import re

STREET_SUFFIXES = [
    "st", "street", "ave", "avenue", "blvd", "boulevard", "rd", "road",
    "dr", "drive", "ln", "lane", "ct", "court", "pl", "place", "way",
    "pkwy", "parkway", "cir", "circle", "hwy", "highway",
]

# Well-known street names that don't follow "Name + Suffix" pattern
KNOWN_STREETS = [
    "broadway", "wall street", "fifth avenue", "main street",
    "market street", "market st", "king street", "queen street",
    "high street", "lombard street", "mission street", "embarcadero",
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

# Regex: "123 Main St" or "Market Street" or "4th and Market"
STREET_PATTERN = re.compile(
    r'\b(\d+\s+\w+\s+(?:' + '|'.join(STREET_SUFFIXES) + r'))\b'
    r'|'
    r'\b([A-Z]\w+\s+(?:' + '|'.join(STREET_SUFFIXES) + r'))\b'
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
    # Common words that match street patterns but aren't streets
    street_noise = {"ago and now", "out and about", "up and down", "here and there",
                    "now and then", "back and forth", "come and go", "in and out",
                    "over and over", "on and on", "more and more", "day and night",
                    "hot and cold", "left and right", "this and that", "me and my",
                    "you and i", "love and hate", "try and get", "sit and watch",
                    "grab and go", "stop and go", "rise and shine", "wait and see",
                    "hit and miss", "give and take", "lost and found", "pros and cons",
                    "the street", "a street", "my street", "any street", "one street",
                    "this street", "that street", "the road", "a road", "my road",
                    "the drive", "the lane", "the way", "the place", "the court",
                    "every way", "any way", "some way", "another way"}
    for m in STREET_PATTERN.finditer(text):
        val = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        if len(val) > 4 and val.lower() not in street_noise:
            streets.append(val)

    # Check for well-known street names (deduplicated)
    # Normalize: "Market St" and "Market Street" are the same
    def _normalize_street(s: str) -> str:
        s = s.lower().strip().replace(".", "")
        for suffix in STREET_SUFFIXES:
            if s.endswith(" " + suffix):
                s = s[:-(len(suffix))].strip()
                break
        return s

    existing_normalized = {_normalize_street(s) for s in streets}
    for known in KNOWN_STREETS:
        if known in text_lower and _normalize_street(known) not in existing_normalized:
            streets.append(known.title())
            existing_normalized.add(_normalize_street(known))

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
