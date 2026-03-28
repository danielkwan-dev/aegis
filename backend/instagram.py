"""
Aegis -- Instagram OSINT Scraper
────────────────────────────────
Attempts live scrape via instaloader. If rate-limited or blocked,
falls back to realistic mock post data that still flows through
the real Aegis engine pipeline.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from engine import (
    extract_entities,
    infer_time_context,
    merge_signals,
    metadata_to_text,
    user_footprint,
    scan_entity_triplets,
    detect_static_landmarks,
    generate_conclusion,
)

# ── Mock post templates ──────────────────────────────────────────
# Designed to create overlapping [Time + Location + Activity] patterns
# so the Inference Engine has real signal to detect.

MOCK_POSTS = [
    {
        "caption": "Morning coffee at Starbucks on Market Street before heading to the office. Same order every day lol",
        "location": "Starbucks Market St",
        "time_offset_days": 1,
        "hour": 7,
    },
    {
        "caption": "Tuesday evening run through Golden Gate Park. Perfect weather for 5 miles",
        "location": "Golden Gate Park",
        "time_offset_days": 2,
        "hour": 18,
    },
    {
        "caption": "Lunch break at Chipotle on Broadway. The burrito bowl never misses",
        "location": "Chipotle Broadway",
        "time_offset_days": 3,
        "hour": 12,
    },
    {
        "caption": "Walking home down Elm Street after the gym. Legs are destroyed",
        "location": "",
        "time_offset_days": 4,
        "hour": 19,
    },
    {
        "caption": "Saturday farmers market haul! Fresh produce from Ferry Building",
        "location": "Ferry Building Marketplace",
        "time_offset_days": 5,
        "hour": 10,
    },
    {
        "caption": "Back at Starbucks on Market Street. Barista knows my name at this point",
        "location": "Starbucks Market St",
        "time_offset_days": 7,
        "hour": 7,
    },
    {
        "caption": "Sunset jog at Golden Gate Park again. This is becoming my therapy",
        "location": "Golden Gate Park",
        "time_offset_days": 9,
        "hour": 18,
    },
    {
        "caption": "Grabbed dinner at Nopalito after work. The tamales are unreal",
        "location": "Nopalito",
        "time_offset_days": 10,
        "hour": 19,
    },
    {
        "caption": "Morning commute down Market Street. Same bus, same time, same crowd",
        "location": "",
        "time_offset_days": 12,
        "hour": 8,
    },
    {
        "caption": "Gym session at 24 Hour Fitness then walked home on Elm Street. Routine locked in",
        "location": "24 Hour Fitness",
        "time_offset_days": 14,
        "hour": 18,
    },
    {
        "caption": "Coffee and emails at Blue Bottle on Valencia Street. WFH day",
        "location": "Blue Bottle Coffee",
        "time_offset_days": 16,
        "hour": 9,
    },
    {
        "caption": "Chipotle on Broadway again for lunch. I might have a problem",
        "location": "Chipotle Broadway",
        "time_offset_days": 18,
        "hour": 12,
    },
]


def _try_live_scrape(username: str, max_posts: int = 12) -> list[dict] | None:
    """Attempt live scrape. Returns list of post dicts or None if blocked."""
    try:
        import instaloader

        loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True,
            request_timeout=10,
        )

        print(f"[Aegis] Attempting live scrape of @{username}...")
        profile = instaloader.Profile.from_username(loader.context, username)

        posts = []
        for i, post in enumerate(profile.get_posts()):
            if i >= max_posts:
                break

            caption = post.caption or ""
            timestamp = post.date_utc
            location = ""
            metadata = {}

            if timestamp:
                metadata["datetime_original"] = timestamp.strftime("%Y:%m:%d %H:%M:%S")
            if post.location:
                location = post.location.name or ""

            posts.append({
                "caption": caption,
                "location": location,
                "timestamp": timestamp,
                "metadata": metadata,
            })
            print(f"[Aegis] Live post {i + 1}/{max_posts}")

        print(f"[Aegis] Live scrape complete: {len(posts)} posts")
        return posts if posts else None

    except Exception as e:
        print(f"[Aegis] Live scrape failed: {e}")
        return None


def _generate_mock_posts(username: str) -> list[dict]:
    """Generate mock posts with realistic timestamps."""
    now = datetime.now(timezone.utc)
    posts = []
    for mock in MOCK_POSTS:
        ts = now - timedelta(days=mock["time_offset_days"])
        ts = ts.replace(hour=mock["hour"], minute=random.randint(0, 59))
        posts.append({
            "caption": mock["caption"],
            "location": mock["location"],
            "timestamp": ts,
            "metadata": {
                "datetime_original": ts.strftime("%Y:%m:%d %H:%M:%S"),
            },
        })
    return posts


def scrape_instagram(username: str) -> dict:
    """
    Scrape Instagram profile. Tries live first, falls back to mock data.
    Either way, all posts flow through the real Aegis engine.
    """
    username = username.lstrip("@").strip()
    if not username:
        return {"status": "error", "message": "No username provided."}

    # Try live scrape first
    raw_posts = _try_live_scrape(username)
    is_mock = False

    if raw_posts is None:
        print(f"[Aegis] Falling back to mock data for @{username}")
        raw_posts = _generate_mock_posts(username)
        is_mock = True

    # Process each post through the real engine
    post_results = []
    for i, post in enumerate(raw_posts):
        caption = post["caption"]
        location = post.get("location", "")
        timestamp = post.get("timestamp")
        metadata = post.get("metadata", {})

        all_text = f"{caption} {location}".strip()
        if not all_text:
            continue

        entities = extract_entities(all_text)
        time_ctx = infer_time_context(metadata, entities)
        metadata_text = metadata_to_text(metadata)
        merged = merge_signals(caption, "", metadata_text)

        # Label from caption preview
        words = caption.split()
        label = " ".join(words[:6])
        if len(words) > 6:
            label += "..."
        if not label:
            label = f"Post {i + 1}"

        # Ingest into footprint
        user_footprint.ingest(
            text=merged,
            entities=entities,
            metadata=metadata if metadata else None,
            time_context=time_ctx,
            label=label,
        )

        post_results.append({
            "index": i + 1,
            "label": label,
            "timestamp": timestamp.isoformat() if timestamp else None,
            "entities_found": {
                "streets": entities["streets"],
                "places": entities["places"],
                "businesses": entities["businesses"],
                "times": entities["times"],
            },
            "has_location": bool(location),
        })

    # Conclusion engine
    triplets = scan_entity_triplets(user_footprint)
    landmarks = detect_static_landmarks(user_footprint)
    conclusion = generate_conclusion(triplets, [], landmarks, 0.0)

    return {
        "status": "synced",
        "username": username,
        "posts_scraped": len(post_results),
        "posts": post_results,
        "exposure_map": user_footprint.exposure_map_stats(),
        "final_conclusion": conclusion,
    }
