from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.orm import FootprintEntry


def _generate_label(text: str) -> str:
    words = text.split()
    preview = " ".join(words[:6])
    if len(words) > 6:
        preview += "..."
    return preview


class FootprintRepository:
    """Postgres-backed replacement for the old in-memory UserFootprint.

    Exposes the exact same shape the analysis services already expect
    (entries, count, ingest, clear, all_streets, all_coordinates,
    exposure_map_stats) so the ported analysis logic in app/services/
    didn't have to change to gain real persistence.
    """

    def __init__(self, db: Session, session_id: str) -> None:
        self.db = db
        self.session_id = session_id

    @property
    def entries(self) -> list[dict]:
        rows = (
            self.db.query(FootprintEntry)
            .filter_by(session_id=self.session_id)
            .order_by(FootprintEntry.ingested_at)
            .all()
        )
        return [row.to_dict() for row in rows]

    @property
    def count(self) -> int:
        return self.db.query(FootprintEntry).filter_by(session_id=self.session_id).count()

    def ingest(
        self,
        text: str,
        entities: dict,
        metadata: dict | None = None,
        time_context: dict | None = None,
        label: str | None = None,
    ) -> dict:
        has_gps = bool(metadata and "gps_lat" in metadata)
        row = FootprintEntry(
            session_id=self.session_id,
            label=label or _generate_label(text),
            text=text,
            entities=entities,
            image_metadata=metadata or {},
            time_context=time_context,
            has_gps=has_gps,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row.to_dict()

    def clear(self) -> None:
        self.db.query(FootprintEntry).filter_by(session_id=self.session_id).delete()
        self.db.commit()

    def all_streets(self) -> list[str]:
        out: list[str] = []
        for e in self.entries:
            out.extend(e["entities"].get("streets", []))
        return out

    def all_coordinates(self) -> list[dict]:
        out: list[dict] = []
        for e in self.entries:
            out.extend(e["entities"].get("coordinates", []))
            if e["has_gps"]:
                out.append({"lat": e["metadata"]["gps_lat"], "lon": e["metadata"]["gps_lon"]})
        return out

    def exposure_map_stats(self) -> dict:
        entries = self.entries
        all_streets: list[str] = []
        all_coords: list[dict] = []
        all_businesses: list[str] = []
        all_activities: list[str] = []
        all_days: list[str] = []

        for e in entries:
            all_streets.extend(e["entities"].get("streets", []))
            all_coords.extend(e["entities"].get("coordinates", []))
            if e["has_gps"]:
                all_coords.append({"lat": e["metadata"]["gps_lat"], "lon": e["metadata"]["gps_lon"]})
            all_businesses.extend(e["entities"].get("businesses", []))
            all_activities.extend(e["entities"].get("activities", []))
            all_days.extend(e["entities"].get("days", []))

        return {
            "total_data_points": len(entries),
            "unique_streets": len(set(s.lower() for s in all_streets)),
            "known_locations": len(all_coords),
            "unique_businesses": len(set(b.lower() for b in all_businesses)),
            "tracked_activities": len(set(all_activities)),
            "day_patterns": len(set(all_days)),
        }
