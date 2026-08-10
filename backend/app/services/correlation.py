"""Static landmark detection, routine correlation, and entity-triplet scanning.

Operates against anything exposing the FootprintRepository shape
(entries, count, all_coordinates) — see app/db/repository.py.
"""

from __future__ import annotations

from collections import Counter
from typing import Protocol

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.services.entity_extraction import ACTIVITY_KEYWORDS


class FootprintLike(Protocol):
    @property
    def entries(self) -> list[dict]: ...
    @property
    def count(self) -> int: ...
    def all_coordinates(self) -> list[dict]: ...


def detect_static_landmarks(footprint: FootprintLike) -> list[dict]:
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


def _infer_associated_entities(keyword: str, category: str, footprint: FootprintLike) -> dict:
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
    footprint: FootprintLike,
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

        inferred_streets = {s for s, c in assoc["streets"].items() if c >= 1} - new_streets
        inferred_biz = {b for b, c in assoc["businesses"].items() if c >= 1} - new_businesses
        inferred_times = {t for t, c in assoc["times"].items() if c >= 1} - new_time_kws

        inferred_locs = inferred_streets | inferred_biz
        if not inferred_locs and not inferred_times:
            continue

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

        if ocr_terms:
            entry_lower = entry_activity_text.lower()
            overlap = sum(1 for t in ocr_terms if t in entry_lower)
            if overlap > 0:
                base_sim = min(base_sim + (overlap * 0.15 * ocr_boost), 1.0)

        return round(base_sim, 4)
    except ValueError:
        return 0.0


def scan_entity_triplets(footprint: FootprintLike, ocr_terms: set[str] | None = None) -> list[dict]:
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

        shared_times = {t: c for t, c in time_signals.items() if c >= 2}
        shared_days = {d: c for d, c in day_signals.items() if c >= 2}

        if not shared_times and not shared_days:
            continue

        activity_texts = []
        for idx in indices:
            e = entries[idx]
            acts = e["entities"].get("activities", [])
            act_text = " ".join(acts) if acts else ""
            act_text += " " + " ".join(
                w for w in e["text"].lower().split()
                if w in set(ACTIVITY_KEYWORDS)
            )
            activity_texts.append(act_text.strip())

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

    triplets.sort(key=lambda t: t["entry_count"], reverse=True)
    return triplets
