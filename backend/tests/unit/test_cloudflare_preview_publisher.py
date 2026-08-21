from __future__ import annotations

import json

import httpx
import pytest

from kosmo.contracts.sdd.ids import ProjectId
from kosmo.infrastructure.cloudflare.preview import (
    CloudflarePreviewError,
    CloudflareTunnelPreviewPublisher,
)

ACCOUNT_ID = "account-id"
ZONE_ID = "zone-id"
TUNNEL_ID = "12345678-1234-1234-1234-123456789012"
HOSTNAME = "prj-01abc-preview-staging-kosmo.cespan.dev"
TARGET = f"{TUNNEL_ID}.cfargotunnel.com"


def _response(result: object) -> httpx.Response:
    return httpx.Response(200, json={"success": True, "result": result})


def _publisher(handler: httpx.MockTransport) -> CloudflareTunnelPreviewPublisher:
    return CloudflareTunnelPreviewPublisher(
        api_token="test-token",
        account_id=ACCOUNT_ID,
        zone_id=ZONE_ID,
        tunnel_id=TUNNEL_ID,
        host_suffix="preview-staging-kosmo.cespan.dev",
        client=httpx.AsyncClient(base_url="https://api.cloudflare.com/client/v4", transport=handler),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_creates_exact_ingress_and_cname_before_enabling_preview() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET" and request.url.path.endswith("/configurations"):
            return _response(
                {
                    "config": {
                        "ingress": [
                            {"hostname": "staging-kosmo.cespan.dev", "service": "http://nginx:80"},
                            {"service": "http_status:404"},
                        ]
                    }
                }
            )
        if request.method == "PUT" and request.url.path.endswith("/configurations"):
            return _response({"config": {}})
        if request.method == "GET" and request.url.path.endswith("/dns_records"):
            assert request.url.params["name"] == HOSTNAME
            return _response([])
        if request.method == "POST" and request.url.path.endswith("/dns_records"):
            return _response({"id": "dns-record-id"})
        raise AssertionError(f"Unexpected request {request.method} {request.url}")

    publisher = _publisher(httpx.MockTransport(handler))
    try:
        await publisher.publish(ProjectId("prj_01ABC"))
    finally:
        await publisher._client.aclose()  # pyright: ignore[reportOptionalMemberAccess]

    assert [request.method for request in requests] == ["GET", "PUT", "GET", "POST"]
    ingress = json.loads(requests[1].content)["config"]["ingress"]
    assert ingress == [
        {"hostname": "staging-kosmo.cespan.dev", "service": "http://nginx:80"},
        {"hostname": HOSTNAME, "service": "http://nginx:80"},
        {"service": "http_status:404"},
    ]
    dns_payload = json.loads(requests[3].content)
    assert dns_payload["name"] == HOSTNAME
    assert dns_payload["content"] == TARGET
    assert dns_payload["proxied"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_rejects_foreign_dns_record_and_restores_ingress() -> None:
    put_payloads: list[dict[str, object]] = []
    config: dict[str, object] = {"ingress": [{"service": "http_status:404"}]}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path.endswith("/configurations"):
            return _response({"config": config})
        if request.method == "PUT" and request.url.path.endswith("/configurations"):
            payload = json.loads(request.content)
            put_payloads.append(payload)
            config.update(payload["config"])
            return _response({"config": {}})
        if request.method == "GET" and request.url.path.endswith("/dns_records"):
            return _response([{"id": "foreign", "type": "CNAME", "content": "elsewhere.example"}])
        raise AssertionError(f"Unexpected request {request.method} {request.url}")

    publisher = _publisher(httpx.MockTransport(handler))
    try:
        with pytest.raises(CloudflarePreviewError, match="registro DNS ajeno"):
            await publisher.publish(ProjectId("prj_01ABC"))
    finally:
        await publisher._client.aclose()  # pyright: ignore[reportOptionalMemberAccess]

    assert len(put_payloads) == 2
    assert put_payloads[-1]["config"] == {"ingress": [{"service": "http_status:404"}]}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unpublish_removes_only_own_ingress_and_cname() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET" and request.url.path.endswith("/configurations"):
            return _response(
                {
                    "config": {
                        "ingress": [
                            {"hostname": HOSTNAME, "service": "http://nginx:80"},
                            {"hostname": "staging-kosmo.cespan.dev", "service": "http://nginx:80"},
                            {"service": "http_status:404"},
                        ]
                    }
                }
            )
        if request.method == "PUT" and request.url.path.endswith("/configurations"):
            return _response({"config": {}})
        if request.method == "GET" and request.url.path.endswith("/dns_records"):
            return _response(
                [
                    {"id": "ours", "type": "CNAME", "content": TARGET},
                    {"id": "other", "type": "CNAME", "content": "other.cfargotunnel.com"},
                ]
            )
        if request.method == "DELETE" and request.url.path.endswith("/dns_records/ours"):
            return _response({"id": "ours"})
        raise AssertionError(f"Unexpected request {request.method} {request.url}")

    publisher = _publisher(httpx.MockTransport(handler))
    try:
        await publisher.unpublish(ProjectId("prj_01ABC"))
    finally:
        await publisher._client.aclose()  # pyright: ignore[reportOptionalMemberAccess]

    assert [request.method for request in requests] == ["GET", "PUT", "GET", "DELETE"]
    ingress = json.loads(requests[1].content)["config"]["ingress"]
    assert ingress == [
        {"hostname": "staging-kosmo.cespan.dev", "service": "http://nginx:80"},
        {"service": "http_status:404"},
    ]
