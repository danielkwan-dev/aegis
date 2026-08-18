from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_session_id
from app.db.repository import FootprintRepository
from app.db.session import get_db
from app.services.analysis import ingest_data_point
from app.services.ingestion import InstagramExportError, parse_instagram_export

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])

# Each ingested post runs OCR (Tesseract, CPU-bound) — cap how many an export
# import processes in one request so a large export can't hang a demo.
MAX_EXPORT_POSTS_CEILING = 500


@router.post("/manual")
async def ingest_manual(
    text: str = Form(""),
    label: str = Form(""),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    """Ingest a single caption/photo into the session's baseline footprint.

    This is the fast "live demo" path — the Instagram data-export importer
    (bulk ingestion from a .zip) is the endpoint below.
    """
    image_bytes = await image.read() if image and image.filename else None
    footprint = FootprintRepository(db, session_id)
    return ingest_data_point(footprint, text=text, image_bytes=image_bytes, label=label or None)


@router.post("/export")
async def ingest_export(
    file: UploadFile = File(...),
    max_posts: int = Form(50),
    db: Session = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    """Bulk-ingest posts from an official Instagram "Download Your Data" export (.zip).

    ToS-compliant replacement for the old Instaloader live-scrape: the user
    exports their own data from Instagram's settings and uploads it here.
    Most recent `max_posts` posts are ingested (recency matters more than
    completeness for routine detection); anything beyond that is reported
    as skipped, never silently dropped.
    """
    max_posts = max(1, min(max_posts, MAX_EXPORT_POSTS_CEILING))

    def _parse_and_ingest() -> dict:
        posts = parse_instagram_export(file.file)
        posts.sort(
            key=lambda p: p["timestamp"] or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        total_available = len(posts)
        selected = posts[:max_posts]

        footprint = FootprintRepository(db, session_id)
        ingested = 0
        for i, post in enumerate(selected):
            first_line = post["caption"].split("\n")[0][:60]
            label = first_line or f"IG export post {i + 1}"
            result = ingest_data_point(
                footprint,
                text=post["caption"],
                image_bytes=post["image_bytes"],
                label=label,
            )
            if result.get("status") == "secured":
                ingested += 1

        return {
            "status": "synced",
            "posts_available": total_available,
            "posts_ingested": ingested,
            "posts_skipped": max(total_available - len(selected), 0),
            "exposure_map": footprint.exposure_map_stats(),
        }

    try:
        return await asyncio.to_thread(_parse_and_ingest)
    except InstagramExportError as e:
        return {"status": "error", "message": str(e)}
