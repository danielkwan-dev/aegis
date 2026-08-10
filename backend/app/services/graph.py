"""Builds the Stalker's Web graph (nodes + edges) for the frontend force-directed viz."""

from __future__ import annotations

from typing import Protocol

ENTITY_COLORS = {
    "daily_route": "#f59e0b",
    "home": "#ef4444",
    "work": "#3b82f6",
    "family": "#a855f7",
    "general": "#6b7280",
}


class FootprintLike(Protocol):
    @property
    def entries(self) -> list[dict]: ...


def _summarize_entry(entry: dict) -> tuple[str, str]:
    """Build a short label and a longer detail string for a footprint entry."""
    ents = entry.get("entities", {})
    streets = ents.get("streets", [])
    businesses = ents.get("businesses", [])
    times = ents.get("times", [])
    activities = ents.get("activities", [])
    tc = entry.get("time_context") or {}

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
    footprint: FootprintLike,
) -> dict:
    nodes = []
    edges = []

    has_critical = any(
        s["similarity"] >= 0.3
        for sims in category_sims.values()
        for s in sims
    )

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
