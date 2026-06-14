from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.sdd.document_converters import markdown_to_document
from kosmo.infrastructure.api.routers.helpers import resolve_project

router = APIRouter(prefix="/api/v1/projects/{project_id}/discovery", tags=["discovery"])


class SaveDiscoveryRequest(BaseModel):
    markdown: str


async def _get_project_id(request: Request, id_or_slug: str) -> ProjectId:
    project = await resolve_project(request, id_or_slug)
    return project.id


@router.post("/generate")
async def generate_discovery(
    project_id: str,
    request: Request,
) -> dict:
    pid = await _get_project_id(request, project_id)
    uc = request.app.state.pipeline_components.generate_discovery_uc
    output = await uc.execute(project_id=pid)
    from kosmo.domain.sdd.document_converters import document_to_markdown

    return {
        "document_markdown": document_to_markdown(output.discovery_document),
    }


@router.get("")
async def get_discovery(
    project_id: str,
    request: Request,
) -> dict:
    from kosmo.contracts.sdd.errors import DocumentNotFoundError

    pid = await _get_project_id(request, project_id)
    uc = request.app.state.pipeline_components.get_discovery_uc
    doc = await uc.execute(project_id=pid)
    if doc is None:
        raise DocumentNotFoundError(
            document_type="discovery",
            instance=f"/api/v1/projects/{project_id}/discovery",
        )
    from kosmo.domain.sdd.document_converters import document_to_markdown

    return {
        "document_markdown": document_to_markdown(doc),
    }


@router.put("")
async def save_discovery(
    project_id: str,
    body: SaveDiscoveryRequest,
    request: Request,
) -> dict:
    pid = await _get_project_id(request, project_id)
    uc = request.app.state.pipeline_components.save_discovery_uc
    doc = markdown_to_document(body.markdown)
    await uc.execute(project_id=pid, document=doc)
    return {"project_id": str(pid), "message": "ok"}
