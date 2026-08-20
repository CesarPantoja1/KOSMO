from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, Self, cast

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
        server_username: str = "opencode",
        server_password: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 600.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._server_username = server_username
        self._server_password = server_password
        self._model = model
        self._timeout_seconds = timeout_seconds

        if client is not None:
            self._client = client
            self._owns_client = False
        else:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self._timeout_seconds, connect=10.0),
                headers=self._get_auth_headers(),
            )
            self._owns_client = True

    def _get_auth_headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        """Obtiene las cabeceras requeridas incluyendo autenticación si está configurada."""
        headers: dict[str, str] = {}
        if self._server_password:
            credentials = f"{self._server_username}:{self._server_password}"
            encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {encoded}"
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
        payload: dict[str, object] = {"title": title}
        try:
            response = await self._client.post(
                "/session",
                params={"directory": workspace_dir},
                json=payload,
                headers=headers,
            )
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

    def _model_payload(self) -> dict[str, str] | None:
        """Convierte el modelo configurado (provider/model) al objeto que espera la API."""
        if not self._model:
            return None
        if "/" in self._model:
            provider, _, model_id = self._model.partition("/")
            return {"providerID": provider, "modelID": model_id}
        return {"modelID": self._model}

    def _progress_event_type(self, agent: str) -> OpenCodeEventType | str:
        """Tipo de evento de progreso según el agente."""
        if agent == "plan":
            return OpenCodeEventType.PLAN_PROGRESS
        if agent == "build":
            return OpenCodeEventType.BUILD_PROGRESS
        return f"{agent}_progress"

    def _complete_event_type(self, agent: str) -> OpenCodeEventType | str:
        """Tipo de evento de completitud según el agente."""
        if agent == "plan":
            return OpenCodeEventType.PLAN_COMPLETE
        if agent == "build":
            return OpenCodeEventType.BUILD_COMPLETE
        return f"{agent}_complete"

    async def send_prompt(
        self,
        session_id: str,
        prompt: str,
        *,
        agent: str = "plan",
    ) -> AsyncIterator[OpenCodeEvent]:
        """Envía una instrucción al agente en OpenCode (POST /session/{id}/message) y
        traduce el mensaje final de respuesta al vocabulario de eventos KOSMO."""
        headers = self._get_auth_headers({"Accept": "application/json"})
        payload: dict[str, object] = {"parts": [{"type": "text", "text": prompt}], "agent": agent}
        model_payload = self._model_payload()
        if model_payload:
            payload["model"] = model_payload
        url = f"/session/{session_id}/message"

        try:
            response = await self._client.post(url, json=payload, headers=headers)
            if not response.is_success:
                yield OpenCodeEvent(
                    event_type=OpenCodeEventType.ERROR,
                    session_id=session_id,
                    data={
                        "error": f"HTTP {response.status_code}",
                        "detail": response.text[:500],
                    },
                    timestamp=datetime.now(UTC),
                )
                return

            raw_json = response.json()
            message: dict[str, Any] = cast(dict[str, Any], raw_json) if isinstance(raw_json, dict) else {}
            raw_info = message.get("info")
            info: dict[str, Any] = cast(dict[str, Any], raw_info) if isinstance(raw_info, dict) else {}
            raw_parts = message.get("parts")
            parts: list[object] = cast(list[object], raw_parts) if isinstance(raw_parts, list) else []

            error_info: object = info.get("error")
            if error_info is not None:
                error_text = error_info if isinstance(error_info, str) else str(error_info)
                yield OpenCodeEvent(
                    event_type=OpenCodeEventType.ERROR,
                    session_id=session_id,
                    data={"error": error_text},
                    timestamp=datetime.now(UTC),
                )
                return

            files: list[str] = []
            for part in parts:
                if not isinstance(part, dict):
                    continue
                part_dict: dict[str, Any] = cast(dict[str, Any], part)
                part_type: object = part_dict.get("type")
                if part_type == "file":
                    raw_file = part_dict.get("file")
                    file_obj: dict[str, Any] = cast(dict[str, Any], raw_file) if isinstance(raw_file, dict) else {}
                    raw_path: object = part_dict.get("path") or file_obj.get("path")
                    if raw_path is not None:
                        path_str = str(raw_path)
                        files.append(path_str)
                        content_val: object = (
                            part_dict.get("content") or part_dict.get("text") or file_obj.get("content")
                        )
                        yield OpenCodeEvent(
                            event_type=OpenCodeEventType.FILE_EDIT,
                            session_id=session_id,
                            data={
                                "path": path_str,
                                "content": content_val,
                            },
                            timestamp=datetime.now(UTC),
                        )
                elif part_type == "text":
                    raw_text: object = part_dict.get("text")
                    text = str(raw_text or "").strip()
                    if text:
                        yield OpenCodeEvent(
                            event_type=self._progress_event_type(agent),
                            session_id=session_id,
                            data={"delta": text},
                            timestamp=datetime.now(UTC),
                        )

            yield OpenCodeEvent(
                event_type=self._complete_event_type(agent),
                session_id=session_id,
                data={"files": files},
                timestamp=datetime.now(UTC),
            )

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
