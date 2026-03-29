import asyncio
import json
import os
from datetime import datetime, timezone

import httpx
from demo import (
    DEMO_BASELINE_POSTS,
    get_demo_analysis_result,
    get_demo_sync_result,
)
from dotenv import load_dotenv
from engine import (
    analyze_threat,
    extract_entities,
    infer_time_context,
    ingest_data_point,
    merge_signals,
    user_footprint,
)
from fastapi import BackgroundTasks, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from instagram import scrape_instagram

DEMO_USERNAME = "aegis_yhack"

load_dotenv()

# ── jsonblob.com: cloud JSON store so Hex can read analysis data ──
JSONBLOB_ID: str | None = os.getenv("JSONBLOB_ID", None)
HISTORY_BLOB_ID: str | None = os.getenv("HISTORY_BLOB_ID", None)
JSONBLOB_BASE = "https://jsonblob.com/api/jsonBlob"

HEX_API_TOKEN = os.getenv("HEX_API_TOKEN", "")
HEX_PROJECT_ID = os.getenv("HEX_PROJECT_ID", "")
HEX_API_URL = f"https://app.hex.tech/api/v1/projects/{HEX_PROJECT_ID}/runs"
HEX_APP_BASE = "https://app.hex.tech/019d3274-b978-7110-8122-c30aea21a224/app/Aegis-032pYjM1wOXFrsi6nXOwag/latest"

# In-memory store for the most recent Hex run result so the frontend can poll it
_latest_hex_run: dict | None = None

app = FastAPI(title="Aegis — Personal Security Audit")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://app.hex.tech",
        "https://*.hex.tech",
    ],
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
                markers.append(
                    {
                        "lat": lat,
                        "lon": lon,
                        "name": lm["value"].title(),
                        "type": "landmark",
                        "risk": lm.get("percentage", 0) / 100.0,
                        "detail": f"Appears in {lm.get('percentage', 0)}% of posts. {lm.get('classification', '')}",
                    }
                )
                seen_coords.add((lat, lon))

    # From vulnerability map
    for vuln in analysis_result.get("vulnerability_map", []):
        finding = vuln.get("finding", "").lower()
        for loc_name, (lat, lon) in LOCATION_COORDS.items():
            if loc_name in finding and (lat, lon) not in seen_coords:
                markers.append(
                    {
                        "lat": lat,
                        "lon": lon,
                        "name": loc_name.title(),
                        "type": "vulnerability",
                        "risk": 0.9 if vuln["severity"] == "critical" else 0.6,
                        "detail": vuln["finding"][:120],
                    }
                )
                seen_coords.add((lat, lon))

    # From entity triplets
    for triplet in analysis_result.get("entity_triplets", []):
        loc = triplet.get("location", "").lower()
        if loc in LOCATION_COORDS:
            lat, lon = LOCATION_COORDS[loc]
            if (lat, lon) not in seen_coords:
                markers.append(
                    {
                        "lat": lat,
                        "lon": lon,
                        "name": triplet["location"],
                        "type": "routine",
                        "risk": triplet.get("confidence", 0.5),
                        "detail": f"{triplet.get('time', '')} — {triplet.get('activity', '')}",
                    }
                )
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
        reductions.append(
            {
                "action": "Remove street names",
                "detail": f"Remove: {', '.join(detected['streets'])}",
                "current_risk": round(breach_prob, 1),
                "reduced_risk": round(max(breach_prob - drop, 5), 1),
                "risk_drop": round(drop, 1),
                "category": "location",
            }
        )

    # Scenario: remove time references
    if detected.get("times"):
        time_sim = cat_sim.get("timestamps", 0)
        drop = min(time_sim * 30, 25)
        reductions.append(
            {
                "action": "Remove time references",
                "detail": f"Remove: {', '.join(detected['times'])}",
                "current_risk": round(breach_prob, 1),
                "reduced_risk": round(max(breach_prob - drop, 5), 1),
                "risk_drop": round(drop, 1),
                "category": "temporal",
            }
        )

    # Scenario: remove activity keywords
    act_sim = cat_sim.get("activities", 0)
    if act_sim > 0.1:
        drop = min(act_sim * 20, 15)
        reductions.append(
            {
                "action": "Remove activity keywords",
                "detail": "Remove: coffee, routine, commute, gym, etc.",
                "current_risk": round(breach_prob, 1),
                "reduced_risk": round(max(breach_prob - drop, 5), 1),
                "risk_drop": round(drop, 1),
                "category": "activity",
            }
        )

    # Scenario: apply ALL
    total_drop = sum(r["risk_drop"] for r in reductions)
    if reductions:
        reductions.append(
            {
                "action": "Apply ALL recommendations",
                "detail": "Remove all identified location, time, and activity leaks",
                "current_risk": round(breach_prob, 1),
                "reduced_risk": round(max(breach_prob - total_drop, 5), 1),
                "risk_drop": round(total_drop, 1),
                "category": "all",
            }
        )

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
                    print(
                        f"[Aegis] jsonblob update failed ({resp.status_code}), creating new blob"
                    )

            resp = await client.post(JSONBLOB_BASE, headers=headers, json=data)
            if resp.status_code == 201:
                blob_url = resp.headers.get("Location", "")
                new_id = blob_url.rsplit("/", 1)[-1] if blob_url else None
                if new_id:
                    JSONBLOB_ID = new_id
                    print(f"[Aegis] Created jsonblob: {JSONBLOB_BASE}/{JSONBLOB_ID}")
                    print(
                        f"[Aegis] *** Save this in your .env: JSONBLOB_ID={JSONBLOB_ID}"
                    )
                    print(f"[Aegis] *** Hex fetch URL: {JSONBLOB_BASE}/{JSONBLOB_ID}")
            else:
                print(
                    f"[Aegis] jsonblob create failed: {resp.status_code} {resp.text[:200]}"
                )
    except Exception as e:
        print(f"[Aegis] jsonblob error: {e}")


async def _get_score_history() -> list[dict]:
    """Fetch the persistent score history from jsonblob."""
    if not HISTORY_BLOB_ID:
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{JSONBLOB_BASE}/{HISTORY_BLOB_ID}",
                headers={"Accept": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[Aegis] History fetch error: {e}")
    return []


async def _append_score_history(analysis_result: dict) -> list[dict]:
    """Append current run to the persistent score history blob."""
    global HISTORY_BLOB_ID

    vuln_map = analysis_result.get("vulnerability_map", [])
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "breach_probability": round(analysis_result.get("breach_probability", 0), 1),
        "severity_counts": {
            sev: sum(1 for v in vuln_map if v.get("severity") == sev)
            for sev in ["critical", "high", "medium", "low"]
        },
        "entity_counts": {
            k: len(v) for k, v in analysis_result.get("detected_entities", {}).items()
        },
    }

    history = await _get_score_history()
    history.append(entry)
    history = history[-50:]  # cap at 50 runs

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if HISTORY_BLOB_ID:
                resp = await client.put(
                    f"{JSONBLOB_BASE}/{HISTORY_BLOB_ID}",
                    headers=headers,
                    json=history,
                )
                if resp.status_code == 200:
                    return history

            resp = await client.post(JSONBLOB_BASE, headers=headers, json=history)
            if resp.status_code == 201:
                blob_url = resp.headers.get("Location", "")
                new_id = blob_url.rsplit("/", 1)[-1] if blob_url else None
                if new_id:
                    HISTORY_BLOB_ID = new_id
                    print(
                        f"[Aegis] *** Save this in your .env: HISTORY_BLOB_ID={HISTORY_BLOB_ID}"
                    )
    except Exception as e:
        print(f"[Aegis] History write error: {e}")

    return history


def _build_dashboard_data(analysis_result: dict) -> dict:
    """Assemble the full payload that goes to jsonblob + Hex."""
    geo_markers = _build_geo_markers(analysis_result)
    risk_reductions = _build_risk_reductions(analysis_result)

    vuln_map = analysis_result.get("vulnerability_map", [])
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for v in vuln_map:
        sev = v.get("severity", "low")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    return {
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


async def _call_hex_api(dashboard_data: dict) -> dict | None:
    """POST to Hex API to trigger a new run. Returns run metadata or error dict."""
    global _latest_hex_run

    if not HEX_API_TOKEN or not HEX_PROJECT_ID:
        return None

    headers = {
        "Authorization": f"Bearer {HEX_API_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        payload: dict = {"inputParams": {"aegis_data": json.dumps(dashboard_data)}}
    except Exception:
        payload = {}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(HEX_API_URL, headers=headers, json=payload)
            if resp.status_code == 422:
                resp = await client.post(HEX_API_URL, headers=headers, json={})
            resp.raise_for_status()
            data = resp.json()
            run_result = {
                "runId": data.get("runId"),
                "runUrl": data.get("runUrl"),
                "runStatusUrl": data.get("runStatusUrl"),
                "projectId": HEX_PROJECT_ID,
                "appUrl": HEX_APP_BASE,
            }
            _latest_hex_run = run_result
            return run_result
    except httpx.HTTPStatusError as e:
        body = e.response.text[:500] if e.response else ""
        print(f"[Aegis] Hex API {e.response.status_code}: {body}")
        err_result = {
            "error": f"{e.response.status_code}: {body}",
            "projectId": HEX_PROJECT_ID,
            "appUrl": HEX_APP_BASE,
        }
        _latest_hex_run = err_result
        return err_result
    except Exception as e:
        print(f"[Aegis] Hex API error: {e}")
        err_result = {
            "error": str(e),
            "projectId": HEX_PROJECT_ID,
            "appUrl": HEX_APP_BASE,
        }
        _latest_hex_run = err_result
        return err_result


async def trigger_hex_run(analysis_result: dict) -> dict | None:
    """Build dashboard data, then push to jsonblob AND call Hex API in parallel."""
    global _latest_hex_run
    dashboard_data = _build_dashboard_data(analysis_result)

    print(
        f"[Aegis] Dashboard data: {len(dashboard_data['geo_markers'])} geo markers, "
        f"{len(dashboard_data['risk_reductions'])} recommendations, "
        f"breach_prob={dashboard_data['breach_probability']}"
    )

    # Push to jsonblob and trigger Hex run concurrently — saves ~1-2 s
    hex_result, _ = await asyncio.gather(
        _call_hex_api(dashboard_data),
        _push_to_jsonblob(dashboard_data),
        return_exceptions=True,
    )

    if isinstance(hex_result, BaseException):
        print(f"[Aegis] trigger_hex_run error: {hex_result}")
        return {"error": str(hex_result), "appUrl": HEX_APP_BASE}

    return hex_result


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/hex-latest")
def get_hex_latest():
    """Return the most recent Hex run metadata.

    The frontend polls this every 2 s right after analysis completes,
    until pending=False and a real runId is available, then switches
    to the per-run status endpoint.
    """
    if _latest_hex_run:
        return {
            "pending": _latest_hex_run.get("pending", False),
            "runId": _latest_hex_run.get("runId"),
            "runUrl": _latest_hex_run.get("runUrl"),
            "appUrl": _latest_hex_run.get("appUrl", HEX_APP_BASE),
            "error": _latest_hex_run.get("error"),
        }
    return {
        "pending": True,
        "runId": None,
        "runUrl": None,
        "appUrl": HEX_APP_BASE,
        "error": None,
    }


@app.get("/api/hex-url")
def get_hex_url():
    """Return the Hex dashboard URL and the most recent run info."""
    if _latest_hex_run:
        return {
            "appUrl": HEX_APP_BASE,
            "runUrl": _latest_hex_run.get("runUrl"),
            "runId": _latest_hex_run.get("runId"),
            "runStatusUrl": _latest_hex_run.get("runStatusUrl"),
            "projectId": _latest_hex_run.get("projectId"),
            "error": _latest_hex_run.get("error"),
        }
    return {
        "appUrl": HEX_APP_BASE,
        "runUrl": None,
        "runId": None,
        "runStatusUrl": None,
        "projectId": HEX_PROJECT_ID or None,
        "error": None,
    }


@app.get("/api/hex-run-status/{run_id}")
async def get_hex_run_status(run_id: str):
    """Poll Hex API for the status of a specific run.

    Returns status: PENDING | RUNNING | COMPLETED | FAILED | KILLED
    and the runUrl once completed so the frontend can reload the iframe.
    """
    if not HEX_API_TOKEN or not HEX_PROJECT_ID:
        return {
            "status": "UNAVAILABLE",
            "runUrl": None,
            "error": "No Hex credentials configured",
        }

    status_url = f"https://app.hex.tech/api/v1/projects/{HEX_PROJECT_ID}/runs/{run_id}"
    headers = {
        "Authorization": f"Bearer {HEX_API_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(status_url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            run_status = data.get("status", "UNKNOWN")
            run_url = data.get("runUrl") or (_latest_hex_run or {}).get("runUrl")
            return {
                "status": run_status,
                "runUrl": run_url,
                "runId": run_id,
                "elapsedTime": data.get("elapsedTime"),
            }
    except httpx.HTTPStatusError as e:
        body = e.response.text[:300] if e.response else ""
        return {
            "status": "ERROR",
            "runUrl": None,
            "error": f"{e.response.status_code}: {body}",
        }
    except Exception as e:
        return {"status": "ERROR", "runUrl": None, "error": str(e)}


@app.get("/api/score-history")
async def get_score_history():
    """Return the full persistent score history."""
    history = await _get_score_history()
    return {"history": history}


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
    background_tasks: BackgroundTasks,
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

    if result.get("status") == "analyzed":
        result["risk_reductions"] = _build_risk_reductions(result)

        # Pre-build a run_id placeholder so the frontend can start polling immediately.
        # The real run_id is filled in by the background task once Hex responds.
        pending_run: dict = {
            "runId": None,
            "runUrl": None,
            "appUrl": HEX_APP_BASE,
            "pending": True,
        }
        _latest_hex_run = pending_run  # noqa: F841 — intentional module-level write
        result["hex"] = pending_run

        # Capture a snapshot for the background task (result dict may be mutated)
        result_snapshot = dict(result)

        async def _background(snap: dict) -> None:
            global _latest_hex_run
            # Run Hex trigger + score history append concurrently
            hex_res, history = await asyncio.gather(
                trigger_hex_run(snap),
                _append_score_history(snap),
                return_exceptions=True,
            )
            if not isinstance(hex_res, BaseException) and hex_res:
                _latest_hex_run = hex_res
            if not isinstance(history, BaseException):
                pass  # history is persisted inside _append_score_history

        background_tasks.add_task(_background, result_snapshot)

    return result
