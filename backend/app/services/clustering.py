"""K-Means routine clustering.

NOTE: this is the pre-DBSCAN baseline, ported as-is. Checklist item "Implement
DBSCAN+Haversine spatial clustering with dual risk signals" replaces the
geospatial clustering step with DBSCAN — this text-based routine clustering
stays (it's a different axis: TF-IDF over caption text, not lat/lon).
"""

from __future__ import annotations

from collections import Counter
from typing import Protocol

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

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


class FootprintLike(Protocol):
    @property
    def entries(self) -> list[dict]: ...


def cluster_routines(
    footprint: FootprintLike,
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

    actual_k = min(n_clusters, len(baseline))
    model = KMeans(n_clusters=actual_k, random_state=42, n_init=10)
    model.fit(historical_vectors)

    cluster_labels = model.labels_
    cluster_profiles: list[dict] = []

    for cid in range(actual_k):
        member_indices = [i for i, lbl in enumerate(cluster_labels) if lbl == cid]
        member_entries = [baseline[i] for i in member_indices]
        member_texts = " ".join(e["text"] for e in member_entries).lower()

        anchor_hits = [a for a in HIGH_RISK_ANCHORS if a in member_texts]
        risk_score = len(anchor_hits) / max(len(HIGH_RISK_ANCHORS), 1)

        centroid = model.cluster_centers_[cid]
        top_term_indices = centroid.argsort()[-8:][::-1]
        top_terms = [str(feature_names[i]) for i in top_term_indices]

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

    target_cluster = max(cluster_profiles, key=lambda c: c["risk_score"])

    draft_cluster_id = int(model.predict(draft_vector)[0])
    draft_cluster = cluster_profiles[draft_cluster_id]

    distances = model.transform(draft_vector)[0]
    draft_distance = float(distances[draft_cluster_id])
    max_distance = float(distances.max())
    cluster_confidence = round(1.0 - (draft_distance / max(max_distance, 0.001)), 3)

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
