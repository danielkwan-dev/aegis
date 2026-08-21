"""Geospatial clustering (DBSCAN + Haversine) for distinguishing routine
locations from one-off anomalous locations, given GPS/geocoded coordinates.

Replaces the old naive coordinate-bucketing that used to live in
detect_static_landmarks() (a nested-loop proximity check against a fixed
degree threshold -- doesn't account for latitude-dependent distance
distortion, and isn't real clustering). DBSCAN is a better fit for this
specific problem than KMeans: it doesn't require pre-specifying a cluster
count, finds arbitrary-shaped clusters, and -- critically for this app's
threat model -- has a native concept of noise points. That maps directly
onto two genuinely different risk categories, not one:

- A dense cluster (you're at the same spot repeatedly) is a Routine
  Exposure: high risk because it's *predictable* -- an adversary can guess
  where you'll be next.
- A noise point (visited once) is not a pattern, so it's not a routine --
  but a single visit to an unusual/sensitive place can still be an
  Anomalous Disclosure: lower-weight, and risky for a different reason
  (informational sensitivity, not predictability). These must not be
  conflated into one score.
"""

from __future__ import annotations

import numpy as np
from sklearn.cluster import DBSCAN

EARTH_RADIUS_METERS = 6_371_000.0
DEFAULT_EPS_METERS = 50.0  # ~city-block radius -- "same location" granularity
MIN_SAMPLES = 2  # 2+ visits to the same spot is what makes it a routine


def cluster_coordinates(
    coords: list[dict],
    *,
    eps_meters: float = DEFAULT_EPS_METERS,
    min_samples: int = MIN_SAMPLES,
) -> dict:
    """Cluster (lat, lon) points into dense clusters (routines) and noise
    points (anomalous one-offs).

    `coords`: list of {"lat": float, "lon": float}.
    Returns {"clusters": [...], "noise_points": [...]}.
    """
    if len(coords) < 2:
        return {
            "clusters": [],
            "noise_points": [{"lat": c["lat"], "lon": c["lon"]} for c in coords],
        }

    points_rad = np.radians([[c["lat"], c["lon"]] for c in coords])
    eps_rad = eps_meters / EARTH_RADIUS_METERS

    labels = DBSCAN(eps=eps_rad, min_samples=min_samples, metric="haversine").fit_predict(points_rad)

    total = len(coords)
    cluster_members: dict[int, list[int]] = {}
    noise_points: list[dict] = []

    for idx, label in enumerate(labels):
        if label == -1:
            noise_points.append({"lat": coords[idx]["lat"], "lon": coords[idx]["lon"]})
        else:
            cluster_members.setdefault(int(label), []).append(idx)

    clusters = []
    for label, member_idxs in cluster_members.items():
        member_coords = [coords[i] for i in member_idxs]
        centroid_lat = sum(c["lat"] for c in member_coords) / len(member_coords)
        centroid_lon = sum(c["lon"] for c in member_coords) / len(member_coords)
        clusters.append({
            "cluster_id": label,
            "centroid": {"lat": round(centroid_lat, 6), "lon": round(centroid_lon, 6)},
            "size": len(member_coords),
            "percentage": round(len(member_coords) / total * 100, 1),
        })

    clusters.sort(key=lambda c: c["size"], reverse=True)
    return {"clusters": clusters, "noise_points": noise_points}
