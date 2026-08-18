"""Nominatim (OpenStreetMap) geocoding with a Postgres-backed cache.

Replaces the old hardcoded 10-entry LOCATION_COORDS dict. Nominatim's usage
policy caps unauthenticated use at 1 request/second and requires a
descriptive User-Agent -- both handled here. A Postgres cache table (not
Redis -- this app's infra scope is demo-scale, and an indexed primary-key
lookup on a shared table is plenty for this call volume) means a repeated
query never hits Nominatim twice; a small in-process dict sits in front of
that for the common case of the same location coming up multiple times
within one process's lifetime.

Known limitation: a bare street name extracted from caption text (e.g.
"Market Street") has no city/region context, so geocoding it is inherently
ambiguous -- Nominatim will return *a* match, not necessarily the right
one. Solving that needs richer context than the current entity extractor
captures; flagged here rather than silently producing misleading pins.
"""

from __future__ import annotations

import time
from threading import Lock

import httpx
from sqlalchemy.orm import Session

from app.models.orm import GeocodeCache

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "aegis-privacy-scanner/1.0 (+https://github.com/danielkwan-dev/aegis)"
MIN_INTERVAL_SECONDS = 1.05  # Nominatim policy: max 1 req/sec, small buffer

_memory_cache: dict[str, tuple[float, float]] = {}
_last_call_at = 0.0
_rate_limit_lock = Lock()


def _normalize(query: str) -> str:
    return " ".join(query.strip().lower().split())


def _throttled_nominatim_call(client: httpx.Client, query: str) -> tuple[float, float] | None:
    global _last_call_at

    with _rate_limit_lock:
        elapsed = time.monotonic() - _last_call_at
        if elapsed < MIN_INTERVAL_SECONDS:
            time.sleep(MIN_INTERVAL_SECONDS - elapsed)

        try:
            resp = client.get(
                NOMINATIM_URL,
                params={"q": query, "format": "json", "limit": 1},
                headers={"User-Agent": USER_AGENT},
                timeout=10.0,
            )
            resp.raise_for_status()
            results = resp.json()
        except (httpx.HTTPError, ValueError):
            results = None
        finally:
            _last_call_at = time.monotonic()

    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])


def geocode(db: Session, query: str, *, client: httpx.Client | None = None) -> tuple[float, float] | None:
    """Resolve free-text `query` to (lat, lon), or None if it can't be resolved.

    `client` is injectable for testing (pass an httpx.Client with a
    MockTransport) -- production code can just omit it.
    """
    key = _normalize(query)
    if not key:
        return None

    if key in _memory_cache:
        return _memory_cache[key]

    row = db.get(GeocodeCache, key)
    if row:
        coords = (row.lat, row.lon)
        _memory_cache[key] = coords
        return coords

    owns_client = client is None
    if owns_client:
        client = httpx.Client()
    try:
        coords = _throttled_nominatim_call(client, key)
    finally:
        if owns_client:
            client.close()

    if coords is None:
        return None

    db.merge(GeocodeCache(query_text=key, lat=coords[0], lon=coords[1]))
    db.commit()
    _memory_cache[key] = coords
    return coords
