from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kosmo.infrastructure.llm.pydantic_ai_adapter import PydanticAILLMClient


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_with_retry_succeeds_first_attempt() -> None:
    client = PydanticAILLMClient(model=MagicMock(), retry_wait_seconds=0.001)
    call_count = 0

    async def _success() -> str:
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await client._run_with_retry(_success)
    assert result == "ok"
    assert call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_with_retry_recovers_after_transient_error() -> None:
    client = PydanticAILLMClient(model=MagicMock(), retry_wait_seconds=0.001)
    call_count = 0

    async def _transient_fail() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("transient network timeout")
        return "recovered"

    result = await client._run_with_retry(_transient_fail)
    assert result == "recovered"
    assert call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_with_retry_exhausts_attempts_and_reraises() -> None:
    client = PydanticAILLMClient(model=MagicMock(), retry_wait_seconds=0.001)
    call_count = 0

    async def _always_fails() -> str:
        nonlocal call_count
        call_count += 1
        raise ConnectionError("downstream service unreachable")

    with pytest.raises(ConnectionError, match="downstream service unreachable"):
        await client._run_with_retry(_always_fails)

    assert call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_with_retry_does_not_retry_value_error() -> None:
    client = PydanticAILLMClient(model=MagicMock(), retry_wait_seconds=0.001)
    call_count = 0

    async def _value_error() -> str:
        nonlocal call_count
        call_count += 1
        raise ValueError("invalid prompt parameters")

    with pytest.raises(ValueError, match="invalid prompt parameters"):
        await client._run_with_retry(_value_error)

    # ValueError no debe reintentarse (falla inmediata)
    assert call_count == 1
