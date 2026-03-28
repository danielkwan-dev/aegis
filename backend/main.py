import os
import json
import asyncio
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from engine import analyze_threat, ingest_data_point, user_footprint
from instagram import scrape_instagram
from demo import get_demo_sync_result, get_demo_analysis_result, DEMO_BASELINE_POSTS, DEMO_DRAFT_POST

DEMO_USERNAME = "aegis_yhack"

load_dotenv()

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


async def trigger_hex_run(graph_data: dict) -> dict | None:
    """POST the graph data to Hex and return run metadata."""
    if not HEX_API_TOKEN or not HEX_PROJECT_ID:
        return None

    headers = {
        "Authorization": f"Bearer {HEX_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputParams": {
            "input_data": json.dumps(graph_data),
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(HEX_API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return {
                "runId": data.get("runId"),
                "runUrl": data.get("runUrl"),
                "runStatusUrl": data.get("runStatusUrl"),
                "projectId": HEX_PROJECT_ID,
            }
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

    return result
