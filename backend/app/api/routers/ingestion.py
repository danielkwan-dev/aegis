from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_session_id
from app.db.repository import FootprintRepository
from app.db.session import get_db
from app.services.analysis import ingest_data_point

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])


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
    (bulk ingestion from a .zip) is a separate endpoint, added alongside it.
    """
    image_bytes = await image.read() if image and image.filename else None
    footprint = FootprintRepository(db, session_id)
    return ingest_data_point(footprint, text=text, image_bytes=image_bytes, label=label or None)
