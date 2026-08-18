import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.services import geocode as geocode_module
from app.services.geocode import geocode


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def _clear_memory_cache():
    geocode_module._memory_cache.clear()
    geocode_module._last_call_at = 0.0
    yield
    geocode_module._memory_cache.clear()
    geocode_module._last_call_at = 0.0


def _mock_client(response_body, status_code=200):
    def handler(request: httpx.Request) -> httpx.Response:
        assert "User-Agent" in request.headers
        return httpx.Response(status_code, json=response_body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_geocode_returns_coordinates_from_api(db_session):
    client = _mock_client([{"lat": "37.7891", "lon": "-122.4009"}])

    result = geocode(db_session, "Market Street, San Francisco", client=client)

    assert result == (37.7891, -122.4009)


def test_geocode_caches_in_postgres(db_session):
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=[{"lat": "1.0", "lon": "2.0"}])

    client = httpx.Client(transport=httpx.MockTransport(handler))

    geocode(db_session, "Broadway", client=client)
    geocode_module._memory_cache.clear()  # force it to hit the DB layer, not the in-process cache
    geocode(db_session, "Broadway", client=client)

    assert call_count == 1  # second call served from the DB cache, not the API


def test_geocode_uses_in_process_cache(db_session):
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=[{"lat": "1.0", "lon": "2.0"}])

    client = httpx.Client(transport=httpx.MockTransport(handler))

    geocode(db_session, "Broadway", client=client)
    geocode(db_session, "  BROADWAY  ", client=client)  # different casing/whitespace, same normalized key

    assert call_count == 1


def test_geocode_returns_none_for_no_results(db_session):
    client = _mock_client([])

    result = geocode(db_session, "asdkfjaslkdfjalskdjf nonsense query", client=client)

    assert result is None


def test_geocode_returns_none_on_http_error(db_session):
    client = _mock_client({"error": "boom"}, status_code=500)

    result = geocode(db_session, "Market Street", client=client)

    assert result is None


def test_geocode_returns_none_for_empty_query(db_session):
    client = _mock_client([{"lat": "1.0", "lon": "2.0"}])

    result = geocode(db_session, "   ", client=client)

    assert result is None
