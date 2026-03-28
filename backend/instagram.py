"""
Aegis -- Instagram OSINT Scraper
────────────────────────────────
Live scrape of public Instagram profiles via instaloader.
Fetches last 3 posts, extracts captions + timestamps + geotags,
and ingests everything through the Aegis engine.

Includes a 15s timeout so the frontend never hangs.
"""

from __future__ import annotations

import concurrent.futures

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

SCRAPE_TIMEOUT = 15  # seconds


def _do_scrape(username: str, max_posts: int) -> dict:
    """Inner scrape function that runs in a thread with a timeout."""
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
    )

    print(f"[Aegis] Live scrape: loading @{username}...")
    try:
        profile = instaloader.Profile.from_username(loader.context, username)
    except instaloader.exceptions.ProfileNotExistsException:
        return {"status": "error", "message": f"Profile @{username} not found."}
    except instaloader.exceptions.ConnectionException as e:
        err_str = str(e)
        if "429" in err_str or "Too Many Requests" in err_str:
            return {"status": "error", "message": "Instagram rate limited. Try again in a few minutes."}
        return {"status": "error", "message": f"Instagram connection error: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to load profile: {e}"}

    # Check if profile is private
    if profile.is_private:
        print(f"[Aegis] @{username} is a private account.")
        return {"status": "error", "message": f"@{username} is a private account. Aegis can only scan public profiles."}

    print(f"[Aegis] Profile loaded ({profile.mediacount} posts). Scraping up to {max_posts}...")

    post_results = []
    count = 0

    try:
        for post in profile.get_posts():
            if count >= max_posts:
                break

            print(f"[Aegis] Post {count + 1}/{max_posts}...")
            caption = post.caption or ""
            timestamp = post.date_utc

            metadata = {}
            if timestamp:
                metadata["datetime_original"] = timestamp.strftime("%Y:%m:%d %H:%M:%S")

            location_text = ""
            if post.location:
                location_text = post.location.name or ""

            all_text = f"{caption} {location_text}".strip()
            if not all_text:
                count += 1
                continue

            entities = extract_entities(all_text)
            time_ctx = infer_time_context(metadata, entities)
            metadata_text = metadata_to_text(metadata)
            merged = merge_signals(caption, "", metadata_text)

            words = caption.split()
            label = " ".join(words[:8])
            if len(words) > 8:
                label += "..."
            if not label:
                label = f"Post {count + 1}"

            user_footprint.ingest(
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
                "has_location": bool(location_text),
            })

            count += 1

    except instaloader.exceptions.ConnectionException as e:
        print(f"[Aegis] Rate limited after {count} posts: {e}")
    except Exception as e:
        print(f"[Aegis] Scrape error after {count} posts: {e}")

    if not post_results:
        return {
            "status": "error",
            "message": f"Could not scrape any posts from @{username}. Profile may be empty or rate limited.",
        }

    triplets = scan_entity_triplets(user_footprint)
    landmarks = detect_static_landmarks(user_footprint)
    conclusion = generate_conclusion(triplets, [], landmarks, 0.0)

    print(f"[Aegis] Live scrape complete: {len(post_results)} posts ingested")

    return {
        "status": "synced",
        "username": username,
        "posts_scraped": len(post_results),
        "posts": post_results,
        "exposure_map": user_footprint.exposure_map_stats(),
        "final_conclusion": conclusion,
    }


def scrape_instagram(username: str, max_posts: int = 3) -> dict:
    """
    Live scrape with a timeout. If instaloader hangs on a rate-limit
    retry loop, we kill it after SCRAPE_TIMEOUT seconds.
    """
    username = username.lstrip("@").strip()
    if not username:
        return {"status": "error", "message": "No username provided."}

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_do_scrape, username, max_posts)
            return future.result(timeout=SCRAPE_TIMEOUT)
    except concurrent.futures.TimeoutError:
        print(f"[Aegis] Scrape timed out after {SCRAPE_TIMEOUT}s for @{username}")
        return {
            "status": "error",
            "message": f"Scrape timed out for @{username}. Instagram may be rate limiting. Try again later.",
        }
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {e}"}
