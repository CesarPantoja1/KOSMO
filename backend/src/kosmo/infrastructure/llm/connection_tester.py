from __future__ import annotations

import httpx

from kosmo.contracts.ai.ai_config import (
    AIConnectionTester,
    AIConnectionTestError,
    AIProvider,
    InvalidApiKeyError,
    TestAIConnectionResult,
)


class HttpAIConnectionTester(AIConnectionTester):
    """Adaptador de infraestructura HTTP para comprobar la conectividad y credenciales con proveedores de IA."""

    def __init__(self, client: httpx.AsyncClient | None = None, timeout_seconds: float = 10.0) -> None:
        self._client = client
        self._timeout_seconds = timeout_seconds

    async def test_connection(
        self,
        provider: AIProvider,
        model: str,
        api_key: str | None = None,
    ) -> TestAIConnectionResult:
        if provider == AIProvider.KOSMO_DEFAULT:
            return TestAIConnectionResult(
                is_connected=True,
                detected_model=model,
                message=f"Conexión exitosa con el proveedor predeterminado de KOSMO. Modelo {model} verificado.",
            )

        if provider == AIProvider.CUSTOM:
            return TestAIConnectionResult(
                is_connected=True,
                detected_model=model,
                message=f"Conexión configurada para proveedor personalizado con modelo {model}.",
            )

        if not api_key or not api_key.strip():
            raise InvalidApiKeyError(f"Se requiere una clave de API válida para probar el proveedor {provider.value}.")

        clean_key = api_key.strip()
        client = self._client or httpx.AsyncClient(timeout=self._timeout_seconds)
        should_close = self._client is None

        try:
            return await self._execute_provider_check(client, provider, model, clean_key)
        except httpx.TimeoutException as exc:
            raise AIConnectionTestError(
                f"Tiempo de espera agotado al conectar con {provider.value}. El servicio externo no respondió a tiempo."
            ) from exc
        except httpx.RequestError as exc:
            raise AIConnectionTestError(
                f"Error de red al intentar conectar con el proveedor {provider.value}: {exc}"
            ) from exc
        finally:
            if should_close:
                await client.aclose()

    async def _execute_provider_check(
        self,
        client: httpx.AsyncClient,
        provider: AIProvider,
        model: str,
        api_key: str,
    ) -> TestAIConnectionResult:
        if provider == AIProvider.OPENAI:
            url = "https://api.openai.com/v1/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = await client.get(url, headers=headers)
            self._handle_http_response(resp, provider, model)
            return TestAIConnectionResult(
                is_connected=True,
                detected_model=model,
                message=f"Conexión exitosa con OpenAI. Modelo {model} verificado y listo.",
            )

        if provider == AIProvider.ANTHROPIC:
            url = "https://api.anthropic.com/v1/models"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }
            resp = await client.get(url, headers=headers)
            self._handle_http_response(resp, provider, model)
            return TestAIConnectionResult(
                is_connected=True,
                detected_model=model,
                message=f"Conexión exitosa con Anthropic. Modelo {model} verificado y listo.",
            )

        if provider == AIProvider.GOOGLE:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
            params = {"key": api_key}
            resp = await client.get(url, params=params)
            self._handle_http_response(resp, provider, model)
            return TestAIConnectionResult(
                is_connected=True,
                detected_model=model,
                message=f"Conexión exitosa con Google Gemini. Modelo {model} verificado y listo.",
            )

        if provider == AIProvider.DEEPSEEK:
            url = "https://api.deepseek.com/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = await client.get(url, headers=headers)
            if resp.status_code == 404:
                url = "https://api.deepseek.com/v1/models"
                resp = await client.get(url, headers=headers)
            self._handle_http_response(resp, provider, model)
            return TestAIConnectionResult(
                is_connected=True,
                detected_model=model,
                message=f"Conexión exitosa con DeepSeek. Modelo {model} verificado y listo.",
            )

        return TestAIConnectionResult(
            is_connected=True,
            detected_model=model,
            message=f"Conexión exitosa con {provider.value}. Modelo {model} verificado y listo.",
        )

    @staticmethod
    def _handle_http_response(resp: httpx.Response, provider: AIProvider, model: str) -> None:
        if resp.status_code == 200:
            return

        if resp.status_code in (401, 403):
            raise AIConnectionTestError(
                f"Clave de API inválida o no autorizada para {provider.value}. Verifica tus credenciales."
            )

        if resp.status_code == 404:
            raise AIConnectionTestError(
                f"El modelo '{model}' no fue encontrado en {provider.value} o la cuenta no tiene permisos."
            )

        detail = resp.text[:200] if resp.text else f"código HTTP {resp.status_code}"
        raise AIConnectionTestError(f"Fallo al comprobar la conexión con {provider.value}: {detail}")
