"""Orchestrators: ingest_data_point() and analyze_threat().

These are the two entry points the API routers call. Both take a `footprint`
argument (an app.db.repository.FootprintRepository, scoped to the caller's
session) instead of reading a module-level global — that's the one real
behavior change from the original engine.py: state is now per-session and
persisted, not shared across every request for the lifetime of the process.
"""

from __future__ import annotations

from typing import Protocol

from app.services.clustering import cluster_routines
from app.services.conclusion import generate_conclusion
from app.services.correlation import (
    detect_routine_correlations,
    detect_static_landmarks,
    scan_entity_triplets,
)
from app.services.graph import build_exposure_map
from app.services.ner_inference import extract_entities_hybrid
from app.services.similarity import compute_category_similarity
from app.services.vision import (
    extract_exif_metadata,
    extract_ocr_entities,
    infer_time_context,
    merge_signals,
    metadata_to_text,
    run_ocr_cascade,
)
from app.services.vulnerability import generate_vulnerability_map


class FootprintLike(Protocol):
    @property
    def entries(self) -> list[dict]: ...
    @property
    def count(self) -> int: ...
    def ingest(self, text: str, entities: dict, metadata: dict | None,
               time_context: dict | None, label: str | None) -> dict: ...
    def all_coordinates(self) -> list[dict]: ...
    def exposure_map_stats(self) -> dict: ...


def ingest_data_point(
    footprint: FootprintLike,
    text: str,
    image_bytes: bytes | None,
    label: str | None = None,
) -> dict:
    """Ingest a data point into the given session's footprint."""
    ocr_text = ""
    metadata: dict = {}
    if image_bytes:
        ocr_text = run_ocr_cascade(image_bytes)["text"]
        metadata = extract_exif_metadata(image_bytes)

    metadata_text = metadata_to_text(metadata)
    merged = merge_signals(text, ocr_text, metadata_text)

    if not merged.strip():
        return {"status": "empty", "message": "No data to ingest."}

    all_text = f"{text} {ocr_text}".strip()
    entities = extract_entities_hybrid(all_text)
    time_ctx = infer_time_context(metadata, entities)

    entry = footprint.ingest(
        text=merged,
        entities=entities,
        metadata=metadata if metadata else None,
        time_context=time_ctx,
        label=label,
    )

    triplets = scan_entity_triplets(footprint)
    landmarks = detect_static_landmarks(footprint)
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
        "exposure_map": footprint.exposure_map_stats(),
        "final_conclusion": conclusion,
    }


def analyze_threat(
    footprint: FootprintLike,
    draft_text: str,
    image_bytes: bytes | None,
) -> dict:
    """Full evidence-based threat analysis for the given session's footprint."""
    ocr_text = ""
    metadata: dict = {}
    ocr_entities: dict | None = None
    if image_bytes:
        ocr_text = run_ocr_cascade(image_bytes)["text"]
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
            "exposure_map": footprint.exposure_map_stats(),
        }

    all_text = f"{draft_text} {ocr_text}".strip()
    new_entities = extract_entities_hybrid(all_text)
    new_time_ctx = infer_time_context(metadata, new_entities)

    baseline = footprint.entries
    if len(baseline) == 0:
        return {
            "status": "initializing",
            "message": "No footprint data yet. Use /api/ingest/manual to build your exposure map first.",
            "detected_entities": {
                "streets": new_entities["streets"],
                "places": new_entities["places"],
                "businesses": new_entities["businesses"],
                "times": new_entities["times"],
                "coordinates": new_entities["coordinates"],
            },
            "vulnerability_map": [],
            "breach_probability": 0.0,
            "final_conclusion": "Baseline established. No recurring routine detected yet.",
            "web": {"nodes": [{"id": "new_post", "label": "Your Draft Post", "type": "post", "color": "#666"}], "edges": []},
            "exposure_map": footprint.exposure_map_stats(),
        }

    new_entry = {
        "id": "new_post",
        "text": merged,
        "entities": new_entities,
        "metadata": metadata,
        "time_context": new_time_ctx,
    }

    category_sims = compute_category_similarity(new_entry, baseline)

    static_landmarks = detect_static_landmarks(footprint)
    routine_correlations = detect_routine_correlations(new_entities, new_time_ctx, footprint)

    vuln_map = generate_vulnerability_map(
        new_entities, new_time_ctx, ocr_entities, metadata,
        category_sims, static_landmarks, routine_correlations, footprint,
    )

    severity_weights = {"critical": 25.0, "high": 15.0, "medium": 8.0, "low": 3.0}
    raw_score = sum(severity_weights.get(f["severity"], 0) for f in vuln_map)
    breach_probability = round(min(raw_score, 100.0), 1)

    ocr_terms: set[str] | None = None
    if ocr_text:
        ocr_terms = set(w.lower() for w in ocr_text.split() if len(w) > 3)
    triplets = scan_entity_triplets(footprint, ocr_terms=ocr_terms)
    conclusion = generate_conclusion(triplets, vuln_map, static_landmarks, breach_probability)

    # ── K-Means Routine Clustering ──
    clustering = cluster_routines(footprint, merged)

    if clustering and clustering["draft_hits_target"]:
        cluster_boost = clustering["cluster_confidence"] * 20.0
        breach_probability = round(min(breach_probability + cluster_boost, 100.0), 1)

        tc = clustering["target_cluster"]
        anchors = ", ".join(tc["anchor_hits"][:5])
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

    web = build_exposure_map(new_entities, ocr_entities, metadata, category_sims, static_landmarks, footprint)

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
        "exposure_map": footprint.exposure_map_stats(),
    }

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
