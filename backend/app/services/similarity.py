"""Category-specific TF-IDF cosine similarity between a draft post and the baseline footprint."""

from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


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
