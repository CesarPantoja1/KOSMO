from __future__ import annotations

import logging
from typing import Self, cast

import httpx

from kosmo.contracts.integrations.deployment import (
    DeploymentApiError,
    DeploymentAuthenticationError,
    DeploymentConfigurationError,
    DeploymentOAuthToken,
    DeploymentPermissionError,
    DeploymentProviderPort,
    DeploymentRateLimitError,
    DeploymentResourceNotFoundError,
    DeploymentStatus,
    EnvironmentVariable,
    PortSpec,
    VolumeConfig,
)

logger = logging.getLogger(__name__)

_DEFAULT_USER_AGENT = "KOSMO-App"


class RailwayHttpClient(DeploymentProviderPort):
    """Adaptador de infraestructura para interactuar con la API de Railway vía HTTP."""

    def __init__(
        self,
        base_url: str = "https://backboard.railway.com",
        oauth_url: str = "https://backboard.railway.com/oauth/token",
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout_seconds: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._oauth_url = oauth_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout_seconds = timeout_seconds

        if client is not None:
            self._client = client
            self._owns_client = False
        else:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self._timeout_seconds, connect=10.0),
            )
            self._owns_client = True

    def _headers_for_token(self, token: str | None = None) -> dict[str, str]:
        """Construye las cabeceras estándar requeridas por la API de Railway."""
        headers = {
            "Accept": "application/json",
            "User-Agent": _DEFAULT_USER_AGENT,
        }
        if token and token.strip():
            headers["Authorization"] = f"Bearer {token.strip()}"
        return headers

    def _handle_response_error(self, response: httpx.Response, action_description: str) -> None:
        """Mapea códigos de error HTTP de Railway a excepciones de dominio tipadas."""
        status = response.status_code

        if status == 401:
            raise DeploymentAuthenticationError(
                "Token de acceso de Railway inválido o expirado. Reconecta tu cuenta en KOSMO."
            )

        if status == 403:
            is_rate_limit = (
                response.headers.get("x-ratelimit-remaining") == "0"
                or "rate limit" in response.text.lower()
                or "secondary rate limit" in response.text.lower()
            )
            if is_rate_limit:
                raise DeploymentRateLimitError(
                    "Límite de solicitudes de la API de Railway excedido. Intenta nuevamente más tarde."
                )
            raise DeploymentPermissionError(
                f"Permisos insuficientes en Railway para {action_description}: {response.text[:200]}"
            )

        if status == 404:
            raise DeploymentResourceNotFoundError(
                f"El recurso solicitado en Railway no fue encontrado ({action_description}): {response.text[:200]}"
            )

        if status in (400, 422):
            raise DeploymentConfigurationError(
                f"Configuración inválida en Railway al {action_description} ({status}): {response.text[:200]}"
            )

        detail = response.text[:300] if response.text else f"código HTTP {status}"
        raise DeploymentApiError(f"Error en la API de Railway al {action_description} ({status}): {detail}")

    async def aclose(self) -> None:
        """Cierra el cliente HTTP subyacente si fue creado internamente."""
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

    async def exchange_oauth_code(self, code: str) -> DeploymentOAuthToken:
        """Intercambia un código de autorización OAuth por un token de acceso o usa el token directo."""
        cleaned_code = code.strip()
        if not self._client_id and not self._client_secret and (
            cleaned_code.startswith(("rly_", "railway_", "rw_")) or len(cleaned_code) >= 20
        ):
            return DeploymentOAuthToken(
                access_token=cleaned_code,
                token_type="bearer",
            )

        headers = {
            "Accept": "application/json",
            "User-Agent": _DEFAULT_USER_AGENT,
        }
        payload: dict[str, str] = {
            "code": cleaned_code,
            "grant_type": "authorization_code",
        }
        if self._client_id:
            payload["client_id"] = self._client_id
        if self._client_secret:
            payload["client_secret"] = self._client_secret

        try:
            response = await self._client.post(self._oauth_url, json=payload, headers=headers)
            if not response.is_success:
                self._handle_response_error(response, "intercambiar código OAuth")

            data = cast(dict[str, object], response.json())

            if "error" in data:
                error_code = str(data.get("error") or "error_oauth")
                error_desc = str(data.get("error_description") or error_code)
                raise DeploymentAuthenticationError(
                    f"Fallo en autorización OAuth de Railway: {error_desc} ({error_code})"
                )

            access_token = str(data.get("access_token") or "")
            if not access_token:
                raise DeploymentAuthenticationError(
                    "Railway no devolvió un token de acceso válido en la respuesta de OAuth."
                )

            raw_expires_in = data.get("expires_in")
            expires_in = int(str(raw_expires_in)) if raw_expires_in is not None else None
            refresh_token = str(data["refresh_token"]) if data.get("refresh_token") is not None else None

            return DeploymentOAuthToken(
                access_token=access_token,
                token_type=str(data.get("token_type") or "bearer"),
                refresh_token=refresh_token,
                expires_in=expires_in,
            )
        except (DeploymentApiError, DeploymentAuthenticationError):
            raise
        except httpx.TimeoutException as exc:
            raise DeploymentApiError(f"Tiempo de espera agotado al conectar con Railway OAuth: {exc}") from exc
        except httpx.RequestError as exc:
            raise DeploymentApiError(f"Error de red al conectar con Railway OAuth: {exc}") from exc

    async def create_service(
        self,
        token: str,
        repo_url: str,
        env_vars: list[EnvironmentVariable],
        ports: list[PortSpec],
    ) -> str:
        """Crea un nuevo servicio en Railway vinculado a un repositorio remoto."""
        headers = self._headers_for_token(token)
        payload = {
            "repo_url": repo_url,
            "env_vars": [
                {
                    "key": ev.key,
                    "value": ev.value,
                    "is_secret": ev.is_secret,
                }
                for ev in env_vars
            ],
            "ports": [
                {
                    "port": p.port,
                    "protocol": p.protocol,
                }
                for p in ports
            ],
        }

        try:
            response = await self._client.post("/v1/services", json=payload, headers=headers)
            if not response.is_success:
                self._handle_response_error(response, f"crear servicio para repositorio {repo_url}")

            data = cast(dict[str, object], response.json())
            service_id: str | None = None

            if "id" in data and data["id"]:
                service_id = str(data["id"])
            elif "service_id" in data and data["service_id"]:
                service_id = str(data["service_id"])
            elif "data" in data and isinstance(data["data"], dict):
                inner_data = cast(dict[str, object], data["data"])
                if "serviceCreate" in inner_data and isinstance(inner_data["serviceCreate"], dict):
                    sc_data = cast(dict[str, object], inner_data["serviceCreate"])
                    if sc_data.get("id"):
                        service_id = str(sc_data["id"])
                elif "service" in inner_data and isinstance(inner_data["service"], dict):
                    srv_data = cast(dict[str, object], inner_data["service"])
                    if srv_data.get("id"):
                        service_id = str(srv_data["id"])

            if not service_id:
                raise DeploymentApiError("Railway no devolvió un ID de servicio válido al crear el servicio.")

            return service_id
        except (
            DeploymentApiError,
            DeploymentAuthenticationError,
            DeploymentPermissionError,
            DeploymentRateLimitError,
            DeploymentConfigurationError,
            DeploymentResourceNotFoundError,
        ):
            raise
        except httpx.TimeoutException as exc:
            raise DeploymentApiError(f"Tiempo de espera agotado al conectar con Railway: {exc}") from exc
        except httpx.RequestError as exc:
            raise DeploymentApiError(f"Error de red al conectar con Railway: {exc}") from exc

    async def configure_volume(self, token: str, service_id: str, volume: VolumeConfig) -> None:
        """Configura un volumen de almacenamiento persistente para el servicio."""
        headers = self._headers_for_token(token)
        payload = {
            "mount_path": volume.mount_path,
            "size_mb": volume.size_mb,
        }

        try:
            response = await self._client.post(
                f"/v1/services/{service_id}/volumes",
                json=payload,
                headers=headers,
            )
            if not response.is_success:
                self._handle_response_error(response, f"configurar volumen para el servicio {service_id}")
        except (
            DeploymentApiError,
            DeploymentAuthenticationError,
            DeploymentPermissionError,
            DeploymentRateLimitError,
            DeploymentConfigurationError,
            DeploymentResourceNotFoundError,
        ):
            raise
        except httpx.TimeoutException as exc:
            raise DeploymentApiError(f"Tiempo de espera agotado al conectar con Railway: {exc}") from exc
        except httpx.RequestError as exc:
            raise DeploymentApiError(f"Error de red al conectar con Railway: {exc}") from exc

    async def trigger_deployment(self, token: str, service_id: str) -> None:
        """Dispara la construcción y despliegue del servicio en Railway."""
        headers = self._headers_for_token(token)
        payload = {"service_id": service_id}

        try:
            response = await self._client.post(
                f"/v1/services/{service_id}/deploy",
                json=payload,
                headers=headers,
            )
            if not response.is_success:
                self._handle_response_error(response, f"disparar despliegue para el servicio {service_id}")
        except (
            DeploymentApiError,
            DeploymentAuthenticationError,
            DeploymentPermissionError,
            DeploymentRateLimitError,
            DeploymentConfigurationError,
            DeploymentResourceNotFoundError,
        ):
            raise
        except httpx.TimeoutException as exc:
            raise DeploymentApiError(f"Tiempo de espera agotado al conectar con Railway: {exc}") from exc
        except httpx.RequestError as exc:
            raise DeploymentApiError(f"Error de red al conectar con Railway: {exc}") from exc

    async def get_service_status(
        self,
        token: str,
        service_id: str,
    ) -> tuple[DeploymentStatus, str | None, str | None]:
        """
        Consulta el estado actual de publicación del servicio en Railway.
        Retorna (status, public_url, build_logs_url_or_error)
        """
        headers = self._headers_for_token(token)

        try:
            response = await self._client.get(f"/v1/services/{service_id}", headers=headers)
            if response.status_code == 404:
                return (DeploymentStatus.NOT_CREATED, None, None)

            if not response.is_success:
                self._handle_response_error(response, f"consultar estado del servicio {service_id}")

            data = cast(dict[str, object], response.json())
            if "data" in data and isinstance(data["data"], dict):
                inner_data = cast(dict[str, object], data["data"])
                if "service" in inner_data and isinstance(inner_data["service"], dict):
                    data = cast(dict[str, object], inner_data["service"])

            raw_status = str(data.get("status") or data.get("state") or "").lower()

            if raw_status in ("published", "ready", "success", "deployed", "live", "active"):
                status = DeploymentStatus.PUBLISHED
            elif raw_status in ("building", "pending", "deploying", "initializing", "queued", "in_progress"):
                status = DeploymentStatus.BUILDING
            elif raw_status in ("failed", "error", "crashed", "cancelled", "removed"):
                status = DeploymentStatus.FAILED
            else:
                status = DeploymentStatus.NOT_CREATED

            raw_public_url = data.get("public_url") or data.get("deploy_url") or data.get("url")
            public_url = str(raw_public_url) if raw_public_url is not None else None

            raw_logs = (
                data.get("build_logs_url")
                or data.get("error_log_url")
                or data.get("logs_url")
                or data.get("error_message")
            )
            build_logs_url = str(raw_logs) if raw_logs is not None else None

            return (status, public_url, build_logs_url)
        except (
            DeploymentApiError,
            DeploymentAuthenticationError,
            DeploymentPermissionError,
            DeploymentRateLimitError,
            DeploymentConfigurationError,
            DeploymentResourceNotFoundError,
        ):
            raise
        except httpx.TimeoutException as exc:
            raise DeploymentApiError(f"Tiempo de espera agotado al conectar con Railway: {exc}") from exc
        except httpx.RequestError as exc:
            raise DeploymentApiError(f"Error de red al conectar con Railway: {exc}") from exc
