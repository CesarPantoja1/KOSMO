from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, Self

import httpx

from kosmo.contracts.codegen import (
    OpenCodeClientPort,
    OpenCodeEvent,
    OpenCodeEventType,
    OpenCodeSession,
)


class OpenCodeClientError(RuntimeError):
    """Excepción base para errores en el cliente OpenCode."""


class OpenCodeConnectionError(OpenCodeClientError):
    """Lanzada cuando ocurre un error de conexión con el servidor OpenCode."""


class OpenCodeTimeoutError(OpenCodeClientError):
    """Lanzada cuando se agota el tiempo de espera con el servidor OpenCode."""


class OpenCodeSessionNotFoundError(OpenCodeClientError):
    """Lanzada cuando una sesión no existe en el servidor OpenCode."""


class OpenCodeAuthenticationError(OpenCodeClientError):
    """Lanzada cuando la autenticación con el servidor OpenCode falla."""


class OpenCodeHttpClient(OpenCodeClientPort):
    """Adaptador de infraestructura para comunicación HTTP REST y SSE con opencode serve."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:4096",
        server_password: str | None = None,
        timeout_seconds: float = 600.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._server_password = server_password
        self._timeout_seconds = timeout_seconds

        if client is not None:
            self._client = client
            self._owns_client = False
        else:
            headers: dict[str, str] = {}
            if self._server_password:
                headers["Authorization"] = f"Bearer {self._server_password}"
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self._timeout_seconds, connect=10.0),
                headers=headers,
            )
            self._owns_client = True

    def _get_auth_headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        """Obtiene las cabeceras requeridas incluyendo autenticación si está configurada."""
        headers: dict[str, str] = {}
        if self._server_password:
            headers["Authorization"] = f"Bearer {self._server_password}"
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def aclose(self) -> None:
        """Cierra el cliente HTTP si fue creado internamente."""
        if self._owns_client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self.aclose()

    async def health_check(self) -> bool:
        """Verifica la disponibilidad del servidor OpenCode."""
        try:
            headers = self._get_auth_headers()
            response = await self._client.get("/health", headers=headers)
            return response.is_success
        except Exception:
            return False

    async def create_session(
        self,
        workspace_dir: str,
        *,
        title: str = "",
    ) -> OpenCodeSession:
        """Crea una nueva sesión en el servidor OpenCode para el workspace especificado."""
        headers = self._get_auth_headers()
        payload = {"workspace_dir": workspace_dir, "title": title}
        try:
            response = await self._client.post("/session", json=payload, headers=headers)
            if not response.is_success:
                raise OpenCodeClientError(
                    f"Error al crear sesión en OpenCode (HTTP {response.status_code}): {response.text}"
                )
            data: dict[str, Any] = response.json()
            session_id = data.get("id") or data.get("session_id")
            if not session_id:
                raise OpenCodeClientError(f"La respuesta de OpenCode no contiene 'id' o 'session_id': {data}")

            resolved_dir = str(data.get("workspace_dir") or data.get("directory") or workspace_dir)
            resolved_title = str(data.get("title") or title)

            return OpenCodeSession(
                session_id=str(session_id),
                workspace_dir=resolved_dir,
                title=resolved_title,
                created_at=datetime.now(UTC),
            )
        except OpenCodeClientError:
            raise
        except httpx.TimeoutException as exc:
            raise OpenCodeTimeoutError(f"Tiempo de espera agotado al crear sesión OpenCode: {exc}") from exc
        except httpx.HTTPError as exc:
            raise OpenCodeConnectionError(f"Error HTTP al conectar con OpenCode: {exc}") from exc

    def _normalize_event_type(self, raw_type: str | None, default_agent: str) -> OpenCodeEventType | str:
        """Normaliza el tipo de evento al enum OpenCodeEventType o string."""
        if not raw_type:
            return f"{default_agent}_progress"

        clean_type = raw_type.strip().lower()
        for event_type in OpenCodeEventType:
            if event_type.value == clean_type:
                return event_type
        return clean_type

    def _parse_event(
        self,
        session_id: str,
        event_type_str: str | None,
        data_lines: list[str],
        default_agent: str,
    ) -> OpenCodeEvent | None:
        """Parsea las líneas de datos SSE en un objeto OpenCodeEvent."""
        raw_data = "\n".join(data_lines).strip()
        data_obj: dict[str, Any] = {}

        if raw_data:
            try:
                parsed_json: Any = json.loads(raw_data)
                if isinstance(parsed_json, dict):
                    data_obj = dict(parsed_json)  # type: ignore[reportUnknownVariableType]
                    if not event_type_str and "type" in data_obj:
                        event_type_str = str(data_obj["type"])
                    elif not event_type_str and "event_type" in data_obj:
                        event_type_str = str(data_obj["event_type"])
                else:
                    data_obj = {"content": parsed_json}
            except json.JSONDecodeError:
                data_obj = {"content": raw_data}

        if not event_type_str and not data_obj:
            return None

        event_type = self._normalize_event_type(event_type_str, default_agent)
        return OpenCodeEvent(
            event_type=event_type,
            session_id=session_id,
            data=data_obj,
            timestamp=datetime.now(UTC),
        )

    async def send_prompt(
        self,
        session_id: str,
        prompt: str,
        *,
        agent: str = "plan",
    ) -> AsyncIterator[OpenCodeEvent]:
        """Envía una instrucción al agente en OpenCode y consume el flujo SSE de eventos."""
        headers = self._get_auth_headers({"Accept": "text/event-stream"})
        payload = {"prompt": prompt, "agent": agent}
        url = f"/session/{session_id}/prompt"

        try:
            async with self._client.stream("POST", url, json=payload, headers=headers) as response:
                if not response.is_success:
                    error_bytes = await response.aread()
                    error_detail = error_bytes.decode("utf-8", errors="replace")
                    yield OpenCodeEvent(
                        event_type=OpenCodeEventType.ERROR,
                        session_id=session_id,
                        data={
                            "error": f"HTTP {response.status_code}",
                            "detail": error_detail,
                        },
                        timestamp=datetime.now(UTC),
                    )
                    return

                current_event_type: str | None = None
                current_data_lines: list[str] = []

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        if current_event_type or current_data_lines:
                            event = self._parse_event(
                                session_id,
                                current_event_type,
                                current_data_lines,
                                agent,
                            )
                            if event:
                                yield event
                            current_event_type = None
                            current_data_lines = []
                        continue

                    if line.startswith("event:"):
                        current_event_type = line[6:].strip()
                    elif line.startswith("data:"):
                        current_data_lines.append(line[5:].strip())
                    elif line.startswith("{") and line.endswith("}"):
                        current_data_lines.append(line)

                if current_event_type or current_data_lines:
                    event = self._parse_event(
                        session_id,
                        current_event_type,
                        current_data_lines,
                        agent,
                    )
                    if event:
                        yield event

        except Exception as exc:
            yield OpenCodeEvent(
                event_type=OpenCodeEventType.ERROR,
                session_id=session_id,
                data={"error": str(exc)},
                timestamp=datetime.now(UTC),
            )

    async def close_session(self, session_id: str) -> None:
        """Cierra una sesión de OpenCode de forma idempotente."""
        headers = self._get_auth_headers()
        try:
            response = await self._client.delete(f"/session/{session_id}", headers=headers)
            if response.status_code == 404:
                return
            if not response.is_success:
                raise OpenCodeClientError(
                    f"Error al cerrar la sesión {session_id} en OpenCode (HTTP {response.status_code}): {response.text}"
                )
        except OpenCodeClientError:
            raise
        except httpx.TimeoutException as exc:
            raise OpenCodeTimeoutError(f"Tiempo de espera agotado al cerrar sesión {session_id}: {exc}") from exc
        except httpx.HTTPError as exc:
            raise OpenCodeConnectionError(f"Error HTTP al cerrar sesión {session_id}: {exc}") from exc
