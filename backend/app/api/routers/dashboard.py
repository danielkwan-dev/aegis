from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_session_id
from app.db.repository import FootprintRepository
from app.db.session import get_db
from app.models.orm import ScoreHistoryEntry

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/footprint")
def get_footprint(db: Session = Depends(get_db), session_id: str = Depends(get_session_id)):
    footprint = FootprintRepository(db, session_id)
    return {"exposure_map": footprint.exposure_map_stats(), "entries": footprint.entries}


@router.delete("/footprint")
def clear_footprint(db: Session = Depends(get_db), session_id: str = Depends(get_session_id)):
    footprint = FootprintRepository(db, session_id)
    footprint.clear()
    return {"status": "cleared", "exposure_map": footprint.exposure_map_stats()}


@router.get("/score-history")
def get_score_history(db: Session = Depends(get_db), session_id: str = Depends(get_session_id)):
    rows = (
        db.query(ScoreHistoryEntry)
        .filter_by(session_id=session_id)
        .order_by(ScoreHistoryEntry.timestamp)
        .limit(50)
        .all()
    )
    return {"history": [r.to_dict() for r in rows]}
