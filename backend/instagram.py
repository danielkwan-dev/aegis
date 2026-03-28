"""
Aegis — Instagram OSINT Scraper
────────────────────────────────
Fetches the last N public posts from a profile using instaloader,
downloads each image, and feeds them through the Aegis engine.
"""

from __future__ import annotations

import io
import tempfile
import os
from datetime import datetime
from pathlib import Path

import instaloader
import httpx

from engine import (
    extract_ocr_text,
    extract_entities,
    infer_time_context,
    merge_signals,
    user_footprint,
    scan_entity_triplets,
    detect_static_landmarks,
    generate_conclusion,
)


def _download_image(url: str) -> bytes | None:
    """Download an image from URL and return raw bytes."""
    try:
        resp = httpx.get(url, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        print(f"[Aegis] Image download failed: {e}")
        return None


def scrape_instagram(username: str, max_posts: int = 15) -> dict:
    """
    Scrape public Instagram posts and ingest each into the user footprint.

    Returns a summary dict with per-post results and final exposure map.
    """
    username = username.lstrip("@").strip()
    if not username:
        return {"status": "error", "message": "No username provided."}

    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
    )

    try:
        profile = instaloader.Profile.from_username(loader.context, username)
    except instaloader.exceptions.ProfileNotExistsException:
        return {"status": "error", "message": f"Profile @{username} not found."}
    except instaloader.exceptions.ConnectionException as e:
        return {"status": "error", "message": f"Instagram connection error: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to load profile: {e}"}

    post_results = []
    count = 0

    try:
        for post in profile.get_posts():
            if count >= max_posts:
                break

            caption = post.caption or ""
            timestamp = post.date_utc

            # Build time metadata from post timestamp
            metadata = {}
            if timestamp:
                metadata["datetime_original"] = timestamp.strftime("%Y:%m:%d %H:%M:%S")

            # Location from post geotag
            location_text = ""
            if post.location:
                loc_name = post.location.name or ""
                location_text = loc_name
                if hasattr(post.location, "lat") and post.location.lat:
                    metadata["gps_lat"] = post.location.lat
                    metadata["gps_lon"] = post.location.lng

            # Download and OCR the image
            ocr_text = ""
            image_bytes = None
            image_url = post.url  # main image URL
            if image_url:
                image_bytes = _download_image(image_url)
                if image_bytes:
                    ocr_text = extract_ocr_text(image_bytes)

            # Merge all text signals
            all_caption = f"{caption} {location_text}".strip()
            all_text = f"{all_caption} {ocr_text}".strip()

            if not all_text.strip():
                count += 1
                continue

            # Entity extraction
            entities = extract_entities(all_text)
            time_ctx = infer_time_context(metadata, entities)

            # Merge for footprint text
            from engine import metadata_to_text
            metadata_text = metadata_to_text(metadata)
            merged = merge_signals(all_caption, ocr_text, metadata_text)

            # Build label from caption preview
            words = caption.split()
            label = " ".join(words[:6])
            if len(words) > 6:
                label += "..."
            if not label:
                label = f"Post {count + 1}"

            # Ingest into footprint
            entry = user_footprint.ingest(
                text=merged,
                entities=entities,
                metadata=metadata if metadata else None,
                time_context=time_ctx,
                label=label,
            )

            post_results.append({
                "index": count + 1,
                "label": label,
                "timestamp": timestamp.isoformat() if timestamp else None,
                "entities_found": {
                    "streets": entities["streets"],
                    "places": entities["places"],
                    "businesses": entities["businesses"],
                    "times": entities["times"],
                },
                "ocr_text": ocr_text[:200] if ocr_text else None,
                "has_location": bool(location_text),
            })

            count += 1

    except instaloader.exceptions.ConnectionException as e:
        # Rate limited mid-scrape — return what we have so far
        print(f"[Aegis] Instagram rate limited after {count} posts: {e}")
    except Exception as e:
        print(f"[Aegis] Scrape error after {count} posts: {e}")

    # Run conclusion engine on the full footprint
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
