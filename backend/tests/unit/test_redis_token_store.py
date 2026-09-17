from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from redis.asyncio import Redis

from kosmo.contracts.auth import IssuedToken, RefreshConsumeResult, TokenPair, TokenType
from kosmo.infrastructure.persistence.redis.token_store import RedisTokenRevocationStore


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_token_store_store_and_get_grace_period() -> None:
    # Arrange
    mock_redis = MagicMock(spec=Redis)
    mock_redis.set = AsyncMock()
    mock_redis.get = AsyncMock()

    store = RedisTokenRevocationStore(mock_redis)

    now = datetime.now(UTC)
    pair = TokenPair(
        access=IssuedToken(
            token="access_token_123",
            jti="jti_access",
            expires_at=now,
            token_type=TokenType.ACCESS,
            family_id="fam_1",
        ),
        refresh=IssuedToken(
            token="refresh_token_456",
            jti="jti_refresh",
            expires_at=now,
            token_type=TokenType.REFRESH,
            family_id="fam_1",
        ),
    )

    # Act 1: Store grace period
    await store.store_grace_period(old_jti="old_jti_01", token_pair=pair, ttl_seconds=30)
    mock_redis.set.assert_awaited_once()
    call_args = mock_redis.set.call_args
    assert call_args[0][0] == "auth:grace:old_jti_01"
    assert call_args[1]["ex"] == 30

    # Act 2: Get grace period
    payload = json.dumps(
        {
            "access_token": pair.access.token,
            "access_jti": pair.access.jti,
            "access_expires_at": pair.access.expires_at.isoformat(),
            "access_family_id": pair.access.family_id,
            "refresh_token": pair.refresh.token,
            "refresh_jti": pair.refresh.jti,
            "refresh_expires_at": pair.refresh.expires_at.isoformat(),
            "refresh_family_id": pair.refresh.family_id,
        }
    )
    mock_redis.get.return_value = payload.encode("utf-8")

    result = await store.get_grace_period(old_jti="old_jti_01")

    # Assert
    assert result is not None
    assert result.access.token == pair.access.token
    assert result.access.jti == pair.access.jti
    assert result.refresh.token == pair.refresh.token
    assert result.refresh.family_id == "fam_1"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_token_store_consume_refresh_success() -> None:
    # Arrange
    mock_redis = MagicMock(spec=Redis)
    mock_pipe = MagicMock()
    mock_pipe.execute = AsyncMock(return_value=[b"usr-1|fam-1", 1, True])
    mock_redis.pipeline.return_value.__aenter__ = AsyncMock(return_value=mock_pipe)
    mock_redis.pipeline.return_value.__aexit__ = AsyncMock(return_value=None)

    store = RedisTokenRevocationStore(mock_redis)

    # Act
    res = await store.consume_refresh(jti="jti_test")

    # Assert
    assert res == RefreshConsumeResult(subject="usr-1", family_id="fam-1")
    mock_pipe.get.assert_called_once_with("auth:refresh:jti_test")
    mock_pipe.delete.assert_called_once_with("auth:refresh:jti_test")
    mock_pipe.set.assert_called_once_with("auth:grace:jti_test", "ROTATING", ex=30)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_token_store_consume_refresh_returns_none_when_missing() -> None:
    # Arrange
    mock_redis = MagicMock(spec=Redis)
    mock_redis.delete = AsyncMock()
    mock_pipe = MagicMock()
    mock_pipe.execute = AsyncMock(return_value=[None, 0, True])
    mock_redis.pipeline.return_value.__aenter__ = AsyncMock(return_value=mock_pipe)
    mock_redis.pipeline.return_value.__aexit__ = AsyncMock(return_value=None)

    store = RedisTokenRevocationStore(mock_redis)

    # Act
    res = await store.consume_refresh(jti="jti_missing")

    # Assert
    assert res is None
    mock_redis.delete.assert_awaited_once_with("auth:grace:jti_missing")
