from __future__ import annotations

import uuid

from fastapi import Request, Response

from app.core.config import get_settings


def get_session_id(request: Request, response: Response) -> str:
    """Read the visitor's session cookie, creating one if it's missing.

    No auth system by design (demo-scale, single-visitor-per-browser is
    enough) — this is just what scopes one visitor's footprint data from
    everyone else's in the shared Postgres tables.
    """
    settings = get_settings()
    cookie_name = settings.session_cookie_name
    session_id = request.cookies.get(cookie_name)
    if not session_id:
        session_id = uuid.uuid4().hex
        response.set_cookie(
            cookie_name,
            session_id,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 30,
        )
    return session_id
