import os
import json
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from engine import analyze_threat

load_dotenv()

HEX_API_TOKEN = os.getenv("HEX_API_TOKEN", "")
HEX_PROJECT_ID = os.getenv("HEX_PROJECT_ID", "")
HEX_API_URL = f"https://app.hex.tech/api/v1/projects/{HEX_PROJECT_ID}/runs"

app = FastAPI(title="Aegis API")

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


@app.post("/api/simulate")
async def simulate(
    text: str = Form(""),
    image: UploadFile | None = File(None),
):
    image_bytes = None
    if image and image.filename:
        image_bytes = await image.read()

    result = analyze_threat(draft_text=text, image_bytes=image_bytes)

    # Trigger Hex run with the graph data
    if result.get("status") == "analyzed":
        hex_result = await trigger_hex_run(result["web"])
        result["hex"] = hex_result

    return result
