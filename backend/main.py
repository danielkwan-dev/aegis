import os
import json
import asyncio
from datetime import datetime, timezone
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from engine import analyze_threat, ingest_data_point, user_footprint, extract_entities, infer_time_context, merge_signals
from instagram import scrape_instagram
from demo import get_demo_sync_result, get_demo_analysis_result, DEMO_BASELINE_POSTS, DEMO_DRAFT_POST

DEMO_USERNAME = "aegis_yhack"

load_dotenv()

# ── jsonblob.com: cloud JSON store so Hex can read analysis data ──
JSONBLOB_ID: str | None = os.getenv("JSONBLOB_ID", None)
JSONBLOB_BASE = "https://jsonblob.com/api/jsonBlob"

HEX_API_TOKEN = os.getenv("HEX_API_TOKEN", "")
HEX_PROJECT_ID = os.getenv("HEX_PROJECT_ID", "")
HEX_API_URL = f"https://app.hex.tech/api/v1/projects/{HEX_PROJECT_ID}/runs"

app = FastAPI(title="Aegis — Personal Security Audit")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Known location coordinates for geographic mapping
# Covers common SF landmarks. For a production app you'd use a geocoding API.
LOCATION_COORDS: dict[str, tuple[float, float]] = {
    "market street": (37.7891, -122.4009),
    "market st": (37.7891, -122.4009),
    "broadway": (37.7979, -122.4058),
    "financial district": (37.7946, -122.3999),
    "starbucks": (37.7903, -122.4009),
    "embarcadero": (37.7936, -122.3930),
    "mission street": (37.7873, -122.3965),
    "lombard street": (37.8021, -122.4187),
    "main street": (37.7914, -122.3950),
    "king street": (37.7764, -122.3929),
}


def _build_geo_markers(analysis_result: dict) -> list[dict]:
    """Build geographic markers from analysis data for Hex map."""
    markers = []
    seen_coords: set[tuple[float, float]] = set()

    # From static landmarks
    for lm in analysis_result.get("static_landmarks", []):
        if lm.get("type") == "street":
            name = lm["value"].lower()
            if name in LOCATION_COORDS:
                lat, lon = LOCATION_COORDS[name]
                markers.append({
                    "lat": lat, "lon": lon,
                    "name": lm["value"].title(),
                    "type": "landmark",
                    "risk": lm.get("percentage", 0) / 100.0,
                    "detail": f"Appears in {lm.get('percentage', 0)}% of posts. {lm.get('classification', '')}",
                })
                seen_coords.add((lat, lon))

    # From vulnerability map
    for vuln in analysis_result.get("vulnerability_map", []):
        finding = vuln.get("finding", "").lower()
        for loc_name, (lat, lon) in LOCATION_COORDS.items():
            if loc_name in finding and (lat, lon) not in seen_coords:
                markers.append({
                    "lat": lat, "lon": lon,
                    "name": loc_name.title(),
                    "type": "vulnerability",
                    "risk": 0.9 if vuln["severity"] == "critical" else 0.6,
                    "detail": vuln["finding"][:120],
                })
                seen_coords.add((lat, lon))

    # From entity triplets
    for triplet in analysis_result.get("entity_triplets", []):
        loc = triplet.get("location", "").lower()
        if loc in LOCATION_COORDS:
            lat, lon = LOCATION_COORDS[loc]
            if (lat, lon) not in seen_coords:
                markers.append({
                    "lat": lat, "lon": lon,
                    "name": triplet["location"],
                    "type": "routine",
                    "risk": triplet.get("confidence", 0.5),
                    "detail": f"{triplet.get('time', '')} — {triplet.get('activity', '')}",
                })
                seen_coords.add((lat, lon))

    return markers


def _build_risk_reductions(analysis_result: dict) -> list[dict]:
    """Compute what-if risk reduction scenarios for the dashboard."""
    breach_prob = analysis_result.get("breach_probability", 0)
    detected = analysis_result.get("detected_entities", {})
    cat_sim = analysis_result.get("category_similarity", {})
    reductions = []

    # Scenario: remove street names
    if detected.get("streets"):
        loc_sim = cat_sim.get("locations", 0)
        drop = min(loc_sim * 45, 40)
        reductions.append({
            "action": "Remove street names",
            "detail": f"Remove: {', '.join(detected['streets'])}",
            "current_risk": round(breach_prob, 1),
            "reduced_risk": round(max(breach_prob - drop, 5), 1),
            "risk_drop": round(drop, 1),
            "category": "location",
        })

    # Scenario: remove time references
    if detected.get("times"):
        time_sim = cat_sim.get("timestamps", 0)
        drop = min(time_sim * 30, 25)
        reductions.append({
            "action": "Remove time references",
            "detail": f"Remove: {', '.join(detected['times'])}",
            "current_risk": round(breach_prob, 1),
            "reduced_risk": round(max(breach_prob - drop, 5), 1),
            "risk_drop": round(drop, 1),
            "category": "temporal",
        })

    # Scenario: remove activity keywords
    act_sim = cat_sim.get("activities", 0)
    if act_sim > 0.1:
        drop = min(act_sim * 20, 15)
        reductions.append({
            "action": "Remove activity keywords",
            "detail": "Remove: coffee, routine, commute, gym, etc.",
            "current_risk": round(breach_prob, 1),
            "reduced_risk": round(max(breach_prob - drop, 5), 1),
            "risk_drop": round(drop, 1),
            "category": "activity",
        })

    # Scenario: apply ALL
    total_drop = sum(r["risk_drop"] for r in reductions)
    if reductions:
        reductions.append({
            "action": "Apply ALL recommendations",
            "detail": "Remove all identified location, time, and activity leaks",
            "current_risk": round(breach_prob, 1),
            "reduced_risk": round(max(breach_prob - total_drop, 5), 1),
            "risk_drop": round(total_drop, 1),
            "category": "all",
        })

    return reductions


async def _push_to_jsonblob(data: dict) -> None:
    """Push data to jsonblob.com. Creates a new blob on first run, updates after."""
    global JSONBLOB_ID

    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if JSONBLOB_ID:
                resp = await client.put(
                    f"{JSONBLOB_BASE}/{JSONBLOB_ID}",
                    headers=headers,
                    json=data,
                )
                if resp.status_code == 200:
                    print(f"[Aegis] Updated jsonblob: {JSONBLOB_BASE}/{JSONBLOB_ID}")
                    return
                else:
                    print(f"[Aegis] jsonblob update failed ({resp.status_code}), creating new blob")

            resp = await client.post(JSONBLOB_BASE, headers=headers, json=data)
            if resp.status_code == 201:
                blob_url = resp.headers.get("Location", "")
                new_id = blob_url.rsplit("/", 1)[-1] if blob_url else None
                if new_id:
                    JSONBLOB_ID = new_id
                    print(f"[Aegis] Created jsonblob: {JSONBLOB_BASE}/{JSONBLOB_ID}")
                    print(f"[Aegis] *** Save this in your .env: JSONBLOB_ID={JSONBLOB_ID}")
                    print(f"[Aegis] *** Hex fetch URL: {JSONBLOB_BASE}/{JSONBLOB_ID}")
            else:
                print(f"[Aegis] jsonblob create failed: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        print(f"[Aegis] jsonblob error: {e}")


async def trigger_hex_run(analysis_result: dict) -> dict | None:
    """Build dashboard data, push to jsonblob, and trigger Hex run."""
    geo_markers = _build_geo_markers(analysis_result)
    risk_reductions = _build_risk_reductions(analysis_result)

    # Severity counts for donut chart
    vuln_map = analysis_result.get("vulnerability_map", [])
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for v in vuln_map:
        sev = v.get("severity", "low")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # Full dashboard payload
    dashboard_data = {
        "nodes": analysis_result.get("web", {}).get("nodes", []),
        "edges": analysis_result.get("web", {}).get("edges", []),
        "breach_probability": analysis_result.get("breach_probability", 0),
        "vulnerability_map": vuln_map,
        "clustering": analysis_result.get("clustering", {}),
        "exposure_map": analysis_result.get("exposure_map", {}),
        "final_conclusion": analysis_result.get("final_conclusion", ""),
        "static_landmarks": analysis_result.get("static_landmarks", []),
        "entity_triplets": analysis_result.get("entity_triplets", []),
        "category_similarity": analysis_result.get("category_similarity", {}),
        "detected_entities": analysis_result.get("detected_entities", {}),
        "geo_markers": geo_markers,
        "risk_reductions": risk_reductions,
        "severity_counts": severity_counts,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    print(f"[Aegis] Dashboard data: {len(geo_markers)} geo markers, "
          f"{len(risk_reductions)} recommendations, "
          f"breach_prob={dashboard_data['breach_probability']}")

    # Push to jsonblob so Hex can fetch it
    await _push_to_jsonblob(dashboard_data)

    if not HEX_API_TOKEN or not HEX_PROJECT_ID:
        return None

    headers = {
        "Authorization": f"Bearer {HEX_API_TOKEN}",
        "Content-Type": "application/json",
    }

    input_params = {}
    try:
        input_params = {"aegis_data": json.dumps(dashboard_data)}
    except Exception:
        input_params = {}

    payload: dict = {}
    if input_params:
        payload["inputParams"] = input_params

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(HEX_API_URL, headers=headers, json=payload)
            if resp.status_code == 422:
                resp = await client.post(HEX_API_URL, headers=headers, json={})
            resp.raise_for_status()
            data = resp.json()
            return {
                "runId": data.get("runId"),
                "runUrl": data.get("runUrl"),
                "runStatusUrl": data.get("runStatusUrl"),
                "projectId": HEX_PROJECT_ID,
            }
    except httpx.HTTPStatusError as e:
        body = e.response.text[:500] if e.response else ""
        print(f"[Aegis] Hex API {e.response.status_code}: {body}")
        return {"error": f"{e.response.status_code}: {body}", "projectId": HEX_PROJECT_ID}
    except Exception as e:
        print(f"[Aegis] Hex API error: {e}")
        return {"error": str(e), "projectId": HEX_PROJECT_ID}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/exposure-map")
def get_exposure_map():
    """Return current exposure map stats and all baseline entries."""
    return {
        "exposure_map": user_footprint.exposure_map_stats(),
        "entries": user_footprint.entries,
    }


@app.delete("/api/exposure-map")
def clear_exposure_map():
    """Clear all baseline data (reset for demo)."""
    user_footprint.clear()
    return {"status": "cleared", "exposure_map": user_footprint.exposure_map_stats()}


@app.post("/api/audit-ingest")
async def audit_ingest(
    text: str = Form(""),
    label: str = Form(""),
    image: UploadFile | None = File(None),
):
    """Ingest a data point into the user footprint."""
    image_bytes = None
    if image and image.filename:
        image_bytes = await image.read()

    result = ingest_data_point(
        text=text,
        image_bytes=image_bytes,
        label=label if label else None,
    )
    return result


@app.post("/api/sync-instagram")
async def sync_instagram(username: str = Form("")):
    """Scrape a public Instagram profile and ingest posts into the footprint."""
    username = username.strip().lstrip("@")
    if not username:
        return {"status": "error", "message": "No username provided."}

    if username.lower() == DEMO_USERNAME:
        # Preset demo account -- simulate processing time
        await asyncio.sleep(4)

        # Populate the real footprint so analyze_threat works with any draft
        user_footprint.clear()
        for i, p in enumerate(DEMO_BASELINE_POSTS):
            caption = p["caption"]
            ocr_extra = ""
            if i == 1:
                # Post 2: OCR detected "Market St" from street sign in photo
                ocr_extra = "Market St"
            combined = f"{caption} {ocr_extra}".strip()
            entities = extract_entities(combined)
            time_ctx = infer_time_context({}, entities)
            merged = merge_signals(caption, ocr_extra, "")
            user_footprint.ingest(
                text=merged,
                entities=entities,
                metadata=None,
                time_context=time_ctx,
                label=f"IG post {i + 1}",
            )

        return get_demo_sync_result(username)

    # Live scrape for any other username
    result = scrape_instagram(username)
    return result


@app.post("/api/analyze-threat")
async def analyze(
    text: str = Form(""),
    image: UploadFile | None = File(None),
):
    """Analyze a draft post for Identity Links against the security baseline."""
    # Check for demo draft (fuzzy match on key phrases)
    text_lower = text.strip().lower()
    if "market street" in text_lower and "morning" in text_lower:
        result = get_demo_analysis_result()
    else:
        image_bytes = None
        if image and image.filename:
            image_bytes = await image.read()
        result = analyze_threat(draft_text=text, image_bytes=image_bytes)

    # Trigger Hex run for all analyzed results (demo + live)
    if result.get("status") == "analyzed":
        hex_result = await trigger_hex_run(result)
        result["hex"] = hex_result

    return result
