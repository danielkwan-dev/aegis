"""
Aegis -- Preset Demo Data
──────────────────────────
3 real Instagram posts + preset threat analysis result.

DEMO SCRIPT:
  Step 1: Enter @username, click "Scan Profile"
  Step 2: Paste the demo draft, click "Run Threat Analysis"

INSTAGRAM POSTS TO MAKE:

  Post 1 (photo of a coffee shop / city street):
    "There's something about a 7am coffee that just hits different. Found this
     little Starbucks spot on Market Street a few months ago and now I literally
     can't start my day without it. Oat milk latte, window seat, watch the city
     wake up. It's become my whole morning personality at this point"

  Post 2 (photo that shows a Market St street sign or storefront in background):
    "Running out of ways to say I love my morning routine without sounding like
     a broken record. Grabbed my usual order, caught the 7:15 bus, made it to
     my desk before anyone else. Consistency is underrated honestly"

  Post 3 (photo of city at night / food / downtown area):
    "Post-work walk through the Financial District tonight. Grabbed dinner at
     this amazing taco spot on Broadway then just wandered around downtown for
     a bit. I swear I know every block of this neighborhood by heart at this
     point. The city is so much better at night"

DEMO THREAT DRAFT (what to type in Step 2):
  "Heading to Market Street for my morning coffee before work. Love my little routine!"
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

now = datetime.now(timezone.utc)

# ══════════════════════════════════════════════
# The 3 Instagram posts
# ══════════════════════════════════════════════

DEMO_BASELINE_POSTS = [
    {
        "caption": (
            "There's something about a 7am coffee that just hits different. "
            "Found this little Starbucks spot on Market Street a few months ago "
            "and now I literally can't start my day without it. Oat milk latte, "
            "window seat, watch the city wake up. It's become my whole morning "
            "personality at this point"
        ),
        "location": "Starbucks Market St",
        "timestamp": (now - timedelta(days=3)).replace(hour=7, minute=12),
    },
    {
        "caption": (
            "Running out of ways to say I love my morning routine without "
            "sounding like a broken record. Grabbed my usual order, caught the "
            "7:15 bus, made it to my desk before anyone else. Consistency is "
            "underrated honestly"
        ),
        "location": "",
        "timestamp": (now - timedelta(days=8)).replace(hour=7, minute=34),
        "ocr_note": "Image contains Market St street sign (OCR detected)",
    },
    {
        "caption": (
            "Post-work walk through the Financial District tonight. Grabbed "
            "dinner at this amazing taco spot on Broadway then just wandered "
            "around downtown for a bit. I swear I know every block of this "
            "neighborhood by heart at this point. The city is so much better "
            "at night"
        ),
        "location": "Financial District, SF",
        "timestamp": (now - timedelta(days=14)).replace(hour=19, minute=45),
    },
]

DEMO_DRAFT_POST = "Heading to Market Street for my morning coffee before work. Love my little routine!"


# ══════════════════════════════════════════════
# Preset sync result
# ══════════════════════════════════════════════

def get_demo_sync_result(username: str) -> dict:
    posts = []
    for i, p in enumerate(DEMO_BASELINE_POSTS):
        words = p["caption"].split()
        label = " ".join(words[:8])
        if len(words) > 8:
            label += "..."

        entities = _extract_demo_entities(p["caption"], p.get("location", ""))
        # Post 2: OCR detected Market St from the image
        if i == 1:
            entities["streets"].append("Market Street")
            entities["ocr_detected"] = ["Market St (street sign)"]

        posts.append({
            "index": i + 1,
            "label": label,
            "timestamp": p["timestamp"].isoformat(),
            "entities_found": entities,
            "has_location": bool(p.get("location")),
        })

    return {
        "status": "synced",
        "username": username,
        "posts_scraped": 3,
        "posts": posts,
        "exposure_map": {
            "total_data_points": 3,
            "unique_streets": 2,
            "known_locations": 1,
            "unique_businesses": 2,
            "tracked_activities": 4,
            "day_patterns": 3,
        },
        "final_conclusion": (
            "You get coffee on Market Street almost every morning around 7 AM — "
            "that showed up in 2 out of 3 posts. In the evenings, you're walking "
            "around Broadway and the Financial District. That's enough to map "
            "out your entire daily corridor."
        ),
    }


def _extract_demo_entities(caption: str, location: str) -> dict:
    streets = []
    places = []
    businesses = []
    times = []

    text = f"{caption} {location}".lower()

    for s in ["market street", "broadway"]:
        if s in text:
            streets.append(s.title())
    for b in ["starbucks"]:
        if b in text:
            businesses.append(b.title())
    for p in ["financial district"]:
        if p in text:
            places.append(p.title())
    for t in ["morning", "7am", "7:15", "evening", "tonight", "night"]:
        if t in text:
            times.append(t)

    return {"streets": streets, "places": places, "businesses": businesses, "times": times}


# ══════════════════════════════════════════════
# Preset threat analysis result
# ══════════════════════════════════════════════

def get_demo_analysis_result() -> dict:
    return {
        "status": "analyzed",
        "detected_entities": {
            "streets": ["Market Street"],
            "places": [],
            "businesses": [],
            "times": ["morning"],
            "coordinates": [],
        },
        "category_similarity": {
            "locations": 0.8714,
            "timestamps": 0.7843,
            "activities": 0.6217,
        },
        "breach_probability": 95.0,
        "vulnerability_map": [
            {
                "category": "Identity Leak",
                "severity": "critical",
                "finding": (
                    "Market Street matches your daily commute cluster. "
                    "This street appears in 2 of 3 scraped posts, including "
                    "one where it was detected via OCR from a street sign in "
                    "the background of your photo."
                ),
                "evidence_count": 3,
            },
            {
                "category": "Routine Leak",
                "severity": "critical",
                "finding": (
                    "Time + Location + Activity triplet confirmed: Morning "
                    "(7:00-7:30 AM) + Market Street + coffee. This pattern "
                    "appears across multiple posts. A stalker could predict "
                    "your exact location at 7:15 AM on any given weekday."
                ),
                "evidence_count": 2,
            },
            {
                "category": "Routine Leak",
                "severity": "high",
                "finding": (
                    "Draft uses the word 'routine' explicitly, confirming "
                    "habitual behavior. Combined with recurring morning "
                    "timestamps and consistent location data, this post "
                    "validates the pattern rather than just adding to it."
                ),
                "evidence_count": 3,
            },
            {
                "category": "Geographic Corridor",
                "severity": "high",
                "finding": (
                    "Market Street (morning commute) and Broadway/Financial "
                    "District (evening activity) form a predictable daily "
                    "corridor. An adversary can infer your approximate work "
                    "location within this zone."
                ),
                "evidence_count": 3,
            },
            {
                "category": "Temporal Exposure",
                "severity": "medium",
                "finding": (
                    "Morning time window (7:00-7:30 AM) is consistent across "
                    "posts. This draft reinforces the timestamp, narrowing "
                    "the window for physical surveillance."
                ),
                "evidence_count": 2,
            },
        ],
        "static_landmarks": [
            {
                "type": "street",
                "value": "market street",
                "classification": "Daily Commute",
                "appearances": 2,
                "percentage": 67,
            },
            {
                "type": "street",
                "value": "broadway",
                "classification": "Evening Activity",
                "appearances": 1,
                "percentage": 33,
            },
        ],
        "entity_triplets": [
            {
                "time": "morning (7:00-7:30)",
                "location": "Market Street",
                "activity": "coffee / commute",
                "confidence": 0.94,
            },
        ],
        "final_conclusion": (
            "[SIGNAL DETECTED]: We grouped your past posts into 3 routines "
            "using K-Means clustering. This draft matches your \"Morning "
            "Market Street\" routine with 94% confidence.\n\n"
            "[LEAK SOURCE]: 2 of your previous posts follow the same pattern — "
            "keywords like morning, market, coffee, starbucks, commute keep "
            "appearing together. You get coffee every morning around 7 AM at "
            "the Starbucks on Market Street, then catch the 7:15 bus. That's "
            "in 2 out of 3 posts. OCR also picked up a Market St street sign "
            "in the background of Post 2's photo, so even when you didn't "
            "mention the street, your image gave it away.\n\n"
            "[FORECAST]: Someone studying your posts would know exactly where "
            "you are at 7:15 AM on any weekday — Starbucks, Market Street, "
            "window seat. Your evening routine on Broadway and the Financial "
            "District fills in the rest of your day. Posting this draft "
            "confirms the pattern and makes it even easier to predict your "
            "location. Remove the street name, time of day, and the word "
            "'routine' before posting."
        ),
        "signals": {
            "draft_text_length": len(DEMO_DRAFT_POST),
            "ocr_text": None,
            "ocr_high_value": None,
            "exif_metadata": None,
            "time_context": {
                "source": "text_keyword",
                "keyword": "morning",
                "window": ("06:00", "11:59"),
                "period": "morning",
            },
            "merged_length": len(DEMO_DRAFT_POST),
        },
        "web": {
            "nodes": [
                # Draft post (center)
                {"id": "new_post", "label": "Your Draft: morning, coffee, Market St", "type": "post", "color": "#ff2222", "weight": 1.0, "risk_level": 0.95, "cluster_id": 0, "cluster_name": "Morning Market Street",
                 "detail": "Your draft mentions morning + coffee + Market Street. All three match your highest-risk routine."},
                # Extracted entities from draft
                {"id": "ent_market", "label": "Market Street", "type": "extraction", "color": "#06b6d4", "category": "street", "weight": 0.95, "risk_level": 0.9,
                 "detail": "Street name extracted from your draft text. Appears in 67% of your post history."},
                {"id": "ent_morning", "label": "morning", "type": "extraction", "color": "#06b6d4", "category": "time", "weight": 0.7, "risk_level": 0.6,
                 "detail": "Time-of-day keyword. Narrows your location window to 6:00-11:59 AM."},
                {"id": "ent_coffee", "label": "coffee", "type": "extraction", "color": "#06b6d4", "category": "activity", "weight": 0.5, "risk_level": 0.4,
                 "detail": "Activity keyword. Combined with location + time, pins you to a specific coffee shop."},
                # Landmarks
                {"id": "lm_market", "label": "Market St (67%)", "type": "metadata", "color": "#f43f5e", "risk_level": 1.0, "weight": 1.0,
                 "detail": "Market Street appears in 2 of 3 posts (67%). Classified as daily commute route. Highest-risk anchor."},
                {"id": "lm_broadway", "label": "Broadway (33%)", "type": "metadata", "color": "#f43f5e", "risk_level": 0.6, "weight": 0.5,
                 "detail": "Broadway appears in 1 of 3 posts. Evening activity zone in the Financial District."},
                # OCR detection
                {"id": "ocr_sign", "label": "OCR: Market St sign", "type": "metadata", "color": "#f43f5e", "risk_level": 0.9, "weight": 0.8,
                 "detail": "Street sign reading 'Market St' detected via OCR in Post 2's background photo. You didn't type it — your image leaked it."},
                # Scraped posts with descriptive labels
                {"id": "h1", "label": "7am coffee, Starbucks, Market St", "type": "history", "color": "#c084fc", "similarity": 0.87, "weight": 0.85, "risk_level": 0.7, "cluster_id": 0, "cluster_name": "Morning Market Street",
                 "detail": "Post 1: '7am coffee at Starbucks on Market Street, oat milk latte, window seat.' Mentions exact time, business, street, and seating habit."},
                {"id": "h2", "label": "morning routine, 7:15 bus", "type": "history", "color": "#c084fc", "similarity": 0.78, "weight": 0.75, "risk_level": 0.65, "cluster_id": 0, "cluster_name": "Morning Market Street",
                 "detail": "Post 2: 'Morning routine, caught the 7:15 bus.' No street name in text, but OCR found a Market St sign in the photo background."},
                {"id": "h3", "label": "evening walk, Broadway, Financial Dist", "type": "history", "color": "#555", "similarity": 0.31, "weight": 0.35, "risk_level": 0.25, "cluster_id": 1, "cluster_name": "Evening Downtown",
                 "detail": "Post 3: 'Post-work walk through the Financial District, dinner on Broadway.' Establishes your evening routine and work area."},
            ],
            "edges": [
                # Draft -> extracted entities
                {"source": "new_post", "target": "ent_market", "type": "leaks", "weight": 0.95, "connection_strength": "text", "label": "leaks street name"},
                {"source": "new_post", "target": "ent_morning", "type": "leaks", "weight": 0.8, "connection_strength": "text", "label": "leaks time of day"},
                {"source": "new_post", "target": "ent_coffee", "type": "leaks", "weight": 0.6, "connection_strength": "text", "label": "leaks activity"},
                # Entity -> landmark (OCR + Text)
                {"source": "ent_market", "target": "lm_market", "type": "confirms", "weight": 0.95, "connection_strength": "ocr+text", "label": "text + OCR confirm"},
                # OCR connections
                {"source": "ocr_sign", "target": "lm_market", "type": "confirms", "weight": 0.9, "connection_strength": "ocr+text", "label": "photo confirms location"},
                {"source": "ocr_sign", "target": "h2", "type": "detected_in", "weight": 0.85, "connection_strength": "ocr", "label": "sign found in photo"},
                # Entity -> matching posts
                {"source": "ent_market", "target": "h1", "type": "similarity", "weight": 0.87, "connection_strength": "text", "label": "both mention Market St"},
                {"source": "ent_market", "target": "h2", "type": "similarity", "weight": 0.78, "connection_strength": "ocr+text", "label": "OCR + text match"},
                {"source": "ent_morning", "target": "h1", "type": "similarity", "weight": 0.82, "connection_strength": "text", "label": "both mention morning"},
                {"source": "ent_morning", "target": "h2", "type": "similarity", "weight": 0.75, "connection_strength": "text", "label": "same time window"},
                # Post 3 geographic cluster
                {"source": "lm_broadway", "target": "h3", "type": "confirms", "weight": 0.6, "connection_strength": "text", "label": "mentions Broadway"},
                {"source": "lm_market", "target": "lm_broadway", "type": "corridor", "weight": 0.5, "connection_strength": "inference", "label": "daily commute corridor"},
                # Pattern links between history posts
                {"source": "h1", "target": "h2", "type": "pattern", "weight": 0.8, "connection_strength": "text", "label": "same morning routine"},
            ],
        },
        "exposure_map": {
            "total_data_points": 3,
            "unique_streets": 2,
            "known_locations": 1,
            "unique_businesses": 2,
            "tracked_activities": 4,
            "day_patterns": 3,
        },
        "clustering": {
            "n_clusters": 3,
            "draft_cluster_id": 0,
            "draft_cluster_name": "Morning Market Street",
            "draft_hits_target": True,
            "cluster_confidence": 0.94,
            "clusters": [
                {
                    "id": 0,
                    "name": "Morning Market Street",
                    "size": 2,
                    "risk_score": 0.87,
                    "top_terms": ["market", "morning", "coffee", "starbucks", "7am"],
                    "is_target": True,
                },
                {
                    "id": 1,
                    "name": "Evening Downtown",
                    "size": 1,
                    "risk_score": 0.31,
                    "top_terms": ["broadway", "downtown", "financial", "night", "dinner"],
                    "is_target": False,
                },
                {
                    "id": 2,
                    "name": "Uncategorized",
                    "size": 0,
                    "risk_score": 0.0,
                    "top_terms": [],
                    "is_target": False,
                },
            ],
        },
    }
