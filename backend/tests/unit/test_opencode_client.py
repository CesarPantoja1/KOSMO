from __future__ import annotations

import json

import httpx
import pytest

from kosmo.contracts.codegen import (
    OpenCodeClientPort,
    OpenCodeEvent,
    OpenCodeEventType,
    OpenCodeSession,
)
from kosmo.infrastructure.codegen.opencode_client import (
    OpenCodeClientError,
    OpenCodeHttpClient,
)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_opencode_http_client_implements_protocol() -> None:
    # Arrange
    client: OpenCodeClientPort = OpenCodeHttpClient(base_url="http://127.0.0.1:4096")

    # Act & Assert
    assert hasattr(client, "health_check")
    assert hasattr(client, "create_session")
    assert hasattr(client, "send_prompt")
    assert hasattr(client, "close_session")
    assert callable(client.health_check)
    assert callable(client.create_session)
    assert callable(client.send_prompt)
    assert callable(client.close_session)
    if hasattr(client, "aclose"):
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_health_check_returns_true_when_healthy() -> None:
    # Arrange
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        assert request.method == "GET"
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(client=http_client)

    # Act
    is_healthy = await client.health_check()

    # Assert
    assert is_healthy is True
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_health_check_returns_false_on_server_error() -> None:
    # Arrange
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "internal_error"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(client=http_client)

    # Act
    is_healthy = await client.health_check()

    # Assert
    assert is_healthy is False
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_health_check_returns_false_on_connection_error() -> None:
    # Arrange
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(client=http_client)

    # Act
    is_healthy = await client.health_check()

    # Assert
    assert is_healthy is False
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_session_success() -> None:
    # Arrange
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/session"
        assert request.method == "POST"
        body = json.loads(request.content.decode("utf-8"))
        assert body["workspace_dir"] == "/workspaces/prj_01"
        assert body["title"] == "Feature 1 implementation"
        return httpx.Response(
            201,
            json={
                "id": "oc_sess_12345",
                "workspace_dir": "/workspaces/prj_01",
                "title": "Feature 1 implementation",
            },
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(client=http_client)

    # Act
    session = await client.create_session("/workspaces/prj_01", title="Feature 1 implementation")

    # Assert
    assert isinstance(session, OpenCodeSession)
    assert session.session_id == "oc_sess_12345"
    assert session.workspace_dir == "/workspaces/prj_01"
    assert session.title == "Feature 1 implementation"
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_session_supports_session_id_field() -> None:
    # Arrange
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "session_id": "oc_sess_alt_999",
                "workspace_dir": "/workspaces/prj_alt",
                "title": "Alt session",
            },
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(client=http_client)

    # Act
    session = await client.create_session("/workspaces/prj_alt", title="Alt session")

    # Assert
    assert session.session_id == "oc_sess_alt_999"
    assert session.workspace_dir == "/workspaces/prj_alt"
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_session_raises_on_http_error() -> None:
    # Arrange
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"detail": "Invalid workspace path"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(client=http_client)

    # Act & Assert
    with pytest.raises(OpenCodeClientError) as exc_info:
        await client.create_session("/invalid/path")

    assert "400" in str(exc_info.value) or "Invalid workspace" in str(exc_info.value)
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_session_raises_on_missing_id_in_response() -> None:
    # Arrange
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"workspace_dir": "/workspaces/prj_01"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(client=http_client)

    # Act & Assert
    with pytest.raises(OpenCodeClientError) as exc_info:
        await client.create_session("/workspaces/prj_01")

    assert "id" in str(exc_info.value).lower()
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_prompt_sse_streaming_events() -> None:
    # Arrange
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/session/oc_sess_100/prompt"
        assert request.method == "POST"
        body = json.loads(request.content.decode("utf-8"))
        assert body["prompt"] == "Planifica la feature"
        assert body["agent"] == "plan"

        sse_content = (
            b"event: plan_progress\n"
            b'data: {"delta": "Analizando requisitos EARS..."}\n\n'
            b"event: plan_progress\n"
            b'data: {"delta": "Identificando archivos a crear..."}\n\n'
            b"event: plan_complete\n"
            b'data: {"plan": "CREATE src/lib/calc.ts"}\n\n'
        )
        return httpx.Response(
            200,
            content=sse_content,
            headers={"content-type": "text/event-stream"},
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(client=http_client)

    # Act
    events: list[OpenCodeEvent] = []
    async for event in client.send_prompt("oc_sess_100", "Planifica la feature", agent="plan"):
        events.append(event)

    # Assert
    assert len(events) == 3
    assert events[0].event_type == OpenCodeEventType.PLAN_PROGRESS
    assert events[0].session_id == "oc_sess_100"
    assert events[0].data.get("delta") == "Analizando requisitos EARS..."

    assert events[1].event_type == OpenCodeEventType.PLAN_PROGRESS
    assert events[1].session_id == "oc_sess_100"

    assert events[2].event_type == OpenCodeEventType.PLAN_COMPLETE
    assert events[2].session_id == "oc_sess_100"
    assert events[2].data.get("plan") == "CREATE src/lib/calc.ts"
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_prompt_handles_json_event_data_format() -> None:
    # Arrange
    def handler(_request: httpx.Request) -> httpx.Response:
        sse_content = (
            b'data: {"type": "build_progress", "message": "Generando src/lib/calc.ts"}\n\n'
            b'data: {"type": "file_edit", "path": "src/lib/calc.ts", "action": "create"}\n\n'
            b'data: {"type": "build_complete", "status": "success"}\n\n'
        )
        return httpx.Response(200, content=sse_content, headers={"content-type": "text/event-stream"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(client=http_client)

    # Act
    events: list[OpenCodeEvent] = []
    async for event in client.send_prompt("oc_sess_200", "Implementa el código", agent="build"):
        events.append(event)

    # Assert
    assert len(events) == 3
    assert events[0].event_type == OpenCodeEventType.BUILD_PROGRESS
    assert events[1].event_type == OpenCodeEventType.FILE_EDIT
    assert events[1].data.get("path") == "src/lib/calc.ts"
    assert events[2].event_type == OpenCodeEventType.BUILD_COMPLETE
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_prompt_emits_error_event_on_http_failure() -> None:
    # Arrange
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Session oc_sess_missing not found"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(client=http_client)

    # Act
    events: list[OpenCodeEvent] = []
    async for event in client.send_prompt("oc_sess_missing", "Hola"):
        events.append(event)

    # Assert
    assert len(events) == 1
    assert events[0].event_type == OpenCodeEventType.ERROR
    assert events[0].session_id == "oc_sess_missing"
    assert "404" in str(events[0].data) or "not found" in str(events[0].data).lower()
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_send_prompt_emits_error_event_on_connection_error() -> None:
    # Arrange
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection timed out")

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(client=http_client)

    # Act
    events: list[OpenCodeEvent] = []
    async for event in client.send_prompt("oc_sess_timeout", "Prompt"):
        events.append(event)

    # Assert
    assert len(events) == 1
    assert events[0].event_type == OpenCodeEventType.ERROR
    assert events[0].session_id == "oc_sess_timeout"
    assert "Connection" in str(events[0].data) or "timed out" in str(events[0].data)
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_close_session_success() -> None:
    # Arrange
    deleted_sessions: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path == "/session/oc_sess_to_close"
        deleted_sessions.append("oc_sess_to_close")
        return httpx.Response(204)

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(client=http_client)

    # Act
    await client.close_session("oc_sess_to_close")

    # Assert
    assert deleted_sessions == ["oc_sess_to_close"]
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_close_session_idempotent_on_404() -> None:
    # Arrange
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Session already closed"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(client=http_client)

    # Act (debe completar sin lanzar excepción)
    await client.close_session("oc_sess_non_existent")

    # Assert
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_close_session_raises_on_server_error() -> None:
    # Arrange
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "Internal server crash"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(client=http_client)

    # Act & Assert
    with pytest.raises(OpenCodeClientError) as exc_info:
        await client.close_session("oc_sess_err")

    assert "500" in str(exc_info.value) or "crash" in str(exc_info.value)
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_authentication_header_sent_when_password_configured() -> None:
    # Arrange
    captured_auth_headers: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_auth_headers.append(request.headers.get("authorization", ""))
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(
        client=http_client,
        server_password="secret_opencode_password_123",
    )

    # Act
    await client.health_check()

    # Assert
    assert len(captured_auth_headers) == 1
    assert captured_auth_headers[0] == "Basic b3BlbmNvZGU6c2VjcmV0X29wZW5jb2RlX3Bhc3N3b3JkXzEyMw=="
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_authentication_header_uses_configured_username() -> None:
    # Arrange
    captured_auth_headers: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_auth_headers.append(request.headers.get("authorization", ""))
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(
        client=http_client,
        server_username="kosmo-agent",
        server_password="tok",
    )

    # Act
    await client.health_check()

    # Assert
    assert len(captured_auth_headers) == 1
    assert captured_auth_headers[0] == "Basic a29zbW8tYWdlbnQ6dG9r"
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_no_authentication_header_when_no_password() -> None:
    # Arrange
    captured_auth_headers: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_auth_headers.append(request.headers.get("authorization", ""))
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client = OpenCodeHttpClient(client=http_client)

    # Act
    await client.health_check()

    # Assert
    assert captured_auth_headers == [""]
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_context_manager_lifecycle() -> None:
    # Arrange
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")

    # Act & Assert
    async with OpenCodeHttpClient(client=http_client) as client:
        is_healthy = await client.health_check()
        assert is_healthy is True
