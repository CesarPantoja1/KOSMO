import sys
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.infrastructure.api.dependencies.rate_limit import IpRateLimiter  # noqa: E402


class _MockRedis:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}
        self._ttls: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        self._ttls[key] = seconds

    async def ttl(self, key: str) -> int:
        return self._ttls.get(key, -1)


def _build_app(limit: int) -> tuple[FastAPI, _MockRedis]:
    mock_redis = _MockRedis()
    limiter = IpRateLimiter(limit)
    app = FastAPI()
    app.state.redis = mock_redis

    @app.get("/probe", dependencies=[Depends(limiter)])
    async def probe() -> dict[str, bool]:
        return {"ok": True}

    return app, mock_redis


def test_requests_within_limit_are_allowed() -> None:
    app, _ = _build_app(3)
    with TestClient(app) as client:
        for _ in range(3):
            assert client.get("/probe").status_code == 200


def test_request_exceeding_limit_returns_429() -> None:
    app, _ = _build_app(3)
    with TestClient(app) as client:
        for _ in range(3):
            client.get("/probe")
        response = client.get("/probe")
        assert response.status_code == 429


def test_429_includes_retry_after_header() -> None:
    app, _ = _build_app(2)
    with TestClient(app) as client:
        for _ in range(2):
            client.get("/probe")
        response = client.get("/probe")
        assert "retry-after" in response.headers
        assert int(response.headers["retry-after"]) >= 1


def test_429_error_message_is_in_spanish() -> None:
    app, _ = _build_app(1)
    with TestClient(app) as client:
        client.get("/probe")
        response = client.get("/probe")
        assert response.status_code == 429
        assert "Demasiadas solicitudes" in response.json()["detail"]
        assert "segundos" in response.json()["detail"]


def test_rate_limiter_skips_when_redis_unavailable() -> None:
    limiter = IpRateLimiter(1)
    app = FastAPI()

    @app.get("/probe", dependencies=[Depends(limiter)])
    async def probe() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as client:
        for _ in range(5):
            assert client.get("/probe").status_code == 200
