from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_session_id
from app.db.repository import FootprintRepository
from app.db.session import get_db
from app.models.orm import AnalysisResult as AnalysisResultModel
from app.models.orm import ScoreHistoryEntry
from app.services.analysis import analyze_threat

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze-threat")
async def analyze(
    text: str = Form(""),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    """Analyze a draft post for Identity Links against the session's baseline.

    Runs and returns synchronously — with the old Hex.tech round-trip gone,
    there's no more external service in the critical path to hide behind a
    background-task/poll dance.
    """
    image_bytes = await image.read() if image and image.filename else None
    footprint = FootprintRepository(db, session_id)
    result = analyze_threat(footprint, draft_text=text, image_bytes=image_bytes)

    if result.get("status") == "analyzed":
        _persist_result(db, session_id, result)

    return result


def _persist_result(db: Session, session_id: str, result: dict) -> None:
    vuln_map = result.get("vulnerability_map", [])
    severity_counts = {
        sev: sum(1 for v in vuln_map if v.get("severity") == sev)
        for sev in ["critical", "high", "medium", "low"]
    }
    entity_counts = {k: len(v) for k, v in result.get("detected_entities", {}).items()}
    breach_probability = result.get("breach_probability", 0)

    db.add(ScoreHistoryEntry(
        session_id=session_id,
        breach_probability=breach_probability,
        severity_counts=severity_counts,
        entity_counts=entity_counts,
    ))
    db.add(AnalysisResultModel(
        session_id=session_id,
        breach_probability=breach_probability,
        result=result,
    ))
    db.commit()
