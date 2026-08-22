from fastapi import Response
from starlette.requests import Request

from app.api.deps import get_session_id


def _request_without_cookie() -> Request:
    return Request({"type": "http", "headers": []})


def test_session_cookie_allows_cross_site_requests():
    request = _request_without_cookie()
    response = Response()

    get_session_id(request, response)

    set_cookie = response.headers.get("set-cookie", "")
    assert "samesite=none" in set_cookie.lower()
    assert "secure" in set_cookie.lower()


def test_existing_cookie_is_reused_without_setting_a_new_one():
    request = Request({"type": "http", "headers": [(b"cookie", b"aegis_session_id=abc123")]})
    response = Response()

    session_id = get_session_id(request, response)

    assert session_id == "abc123"
    assert "set-cookie" not in response.headers
