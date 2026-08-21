from __future__ import annotations

from typing import Any, cast

import httpx

from kosmo.contracts.sdd.ids import ProjectId

_API_BASE_URL = "https://api.cloudflare.com/client/v4"


class CloudflarePreviewError(RuntimeError):
    """Fallo al publicar o retirar una preview en Cloudflare."""


class CloudflareTunnelPreviewPublisher:
    """Gestiona hostnames exactos de previews en un Tunnel remoto.

    Cada proyecto recibe un CNAME exacto, que prevalece sobre el wildcard de
    Producción y permite que Staging use el certificado Universal existente.
    """

    def __init__(
        self,
        *,
        api_token: str,
        account_id: str,
        zone_id: str,
        tunnel_id: str,
        host_suffix: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        suffix = host_suffix.strip(".").lower()
        if not suffix or "." not in suffix:
            raise ValueError("El sufijo público de preview debe ser un hostname válido")
        self._account_id = account_id
        self._zone_id = zone_id
        self._tunnel_id = tunnel_id
        self._host_suffix = suffix
        self._client = client
        self._headers = {"Authorization": f"Bearer {api_token}"}

    def hostname_for(self, project_id: ProjectId) -> str:
        project_label = str(project_id).replace("_", "-").lower()
        return f"{project_label}-{self._host_suffix}"

    @property
    def _tunnel_target(self) -> str:
        return f"{self._tunnel_id}.cfargotunnel.com"

    async def publish(self, project_id: ProjectId) -> None:
        hostname = self.hostname_for(project_id)
        client, should_close = self._get_client()
        try:
            await self._upsert_tunnel_ingress(client, hostname)
            try:
                await self._ensure_dns_record(client, hostname, project_id)
            except Exception:
                await self._remove_tunnel_ingress(client, hostname)
                raise
        except httpx.HTTPError as exc:
            raise CloudflarePreviewError(f"No se pudo publicar la preview {hostname}") from exc
        finally:
            if should_close:
                await client.aclose()

    async def unpublish(self, project_id: ProjectId) -> None:
        hostname = self.hostname_for(project_id)
        client, should_close = self._get_client()
        try:
            await self._remove_tunnel_ingress(client, hostname)
            await self._remove_dns_record(client, hostname)
        except httpx.HTTPError as exc:
            raise CloudflarePreviewError(f"No se pudo retirar la preview {hostname}") from exc
        finally:
            if should_close:
                await client.aclose()

    def _get_client(self) -> tuple[httpx.AsyncClient, bool]:
        if self._client is not None:
            return self._client, False
        return httpx.AsyncClient(base_url=_API_BASE_URL, headers=self._headers, timeout=15.0), True

    async def _api_json(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> object:
        response = await client.request(method, path, headers=self._headers, **kwargs)
        response.raise_for_status()
        payload = cast(dict[str, object], response.json())
        if payload.get("success") is not True:
            errors = payload.get("errors", [])
            raise CloudflarePreviewError(f"Cloudflare rechazó la operación: {errors}")
        return payload.get("result")

    async def _tunnel_config(self, client: httpx.AsyncClient) -> dict[str, object]:
        result = await self._api_json(
            client,
            "GET",
            f"/accounts/{self._account_id}/cfd_tunnel/{self._tunnel_id}/configurations",
        )
        response = cast(dict[str, object], result)
        config = response.get("config")
        if not isinstance(config, dict):
            raise CloudflarePreviewError("Cloudflare devolvió una configuración de Tunnel inválida")
        return cast(dict[str, object], config)

    async def _put_tunnel_config(self, client: httpx.AsyncClient, config: dict[str, object]) -> None:
        await self._api_json(
            client,
            "PUT",
            f"/accounts/{self._account_id}/cfd_tunnel/{self._tunnel_id}/configurations",
            json={"config": config},
        )

    @staticmethod
    def _ingress_without_hostname(ingress: list[object], hostname: str) -> list[dict[str, object]]:
        rules: list[dict[str, object]] = []
        for rule in ingress:
            if not isinstance(rule, dict):
                continue
            normalized_rule = cast(dict[str, object], rule)
            if str(normalized_rule.get("hostname", "")).lower() != hostname:
                rules.append(normalized_rule)
        return rules

    async def _upsert_tunnel_ingress(self, client: httpx.AsyncClient, hostname: str) -> None:
        config = await self._tunnel_config(client)
        current = config.get("ingress", [])
        if not isinstance(current, list):
            raise CloudflarePreviewError("El ingress del Tunnel no es una lista")
        current_ingress = cast(list[object], current)
        ingress = self._ingress_without_hostname(current_ingress, hostname)
        rule: dict[str, object] = {"hostname": hostname, "service": "http://nginx:80"}
        catch_all_index = next(
            (index for index, item in enumerate(ingress) if "hostname" not in item),
            len(ingress),
        )
        ingress.insert(catch_all_index, rule)
        config["ingress"] = ingress
        await self._put_tunnel_config(client, config)

    async def _remove_tunnel_ingress(self, client: httpx.AsyncClient, hostname: str) -> None:
        config = await self._tunnel_config(client)
        current = config.get("ingress", [])
        if not isinstance(current, list):
            raise CloudflarePreviewError("El ingress del Tunnel no es una lista")
        current_ingress = cast(list[object], current)
        ingress = self._ingress_without_hostname(current_ingress, hostname)
        if len(ingress) == len(current_ingress):
            return
        config["ingress"] = ingress
        await self._put_tunnel_config(client, config)

    async def _dns_records(self, client: httpx.AsyncClient, hostname: str) -> list[dict[str, object]]:
        result = await self._api_json(
            client,
            "GET",
            f"/zones/{self._zone_id}/dns_records",
            params={"name": hostname, "per_page": 100},
        )
        if not isinstance(result, list):
            raise CloudflarePreviewError("Cloudflare devolvió registros DNS inválidos")
        records: list[dict[str, object]] = []
        for record in cast(list[object], result):
            if isinstance(record, dict):
                records.append(cast(dict[str, object], record))
        return records

    async def _ensure_dns_record(
        self,
        client: httpx.AsyncClient,
        hostname: str,
        project_id: ProjectId,
    ) -> None:
        records = await self._dns_records(client, hostname)
        expected_target = self._tunnel_target.lower()
        matching = [
            record
            for record in records
            if str(record.get("type", "")).upper() == "CNAME"
            and str(record.get("content", "")).lower() == expected_target
        ]
        if matching:
            return
        if records:
            raise CloudflarePreviewError(f"Ya existe un registro DNS ajeno para {hostname}")
        await self._api_json(
            client,
            "POST",
            f"/zones/{self._zone_id}/dns_records",
            json={
                "type": "CNAME",
                "name": hostname,
                "content": self._tunnel_target,
                "proxied": True,
                "ttl": 1,
                "comment": f"KOSMO staging preview for {project_id}",
            },
        )

    async def _remove_dns_record(self, client: httpx.AsyncClient, hostname: str) -> None:
        expected_target = self._tunnel_target.lower()
        for record in await self._dns_records(client, hostname):
            if (
                str(record.get("type", "")).upper() == "CNAME"
                and str(record.get("content", "")).lower() == expected_target
                and isinstance(record.get("id"), str)
            ):
                await self._api_json(
                    client,
                    "DELETE",
                    f"/zones/{self._zone_id}/dns_records/{record['id']}",
                )
