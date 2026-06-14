from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.sdd.document_converters import markdown_to_document

router = APIRouter(prefix="/api/v1/projects/{project_id}/discovery", tags=["discovery"])


class SaveDiscoveryRequest(BaseModel):
    markdown: str


@router.post("/generate")
async def generate_discovery(
    project_id: str,
    request: Request,
) -> dict:
    uc = request.app.state.pipeline_components.generate_discovery_uc
    output = await uc.execute(project_id=ProjectId(project_id))
    from kosmo.domain.sdd.document_converters import document_to_markdown

    return {
        "document_markdown": document_to_markdown(output.discovery_document),
    }


@router.put("")
async def save_discovery(
    project_id: str,
    body: SaveDiscoveryRequest,
    request: Request,
) -> dict:
    uc = request.app.state.pipeline_components.save_discovery_uc
    doc = markdown_to_document(body.markdown)
    state = await uc.execute(project_id=ProjectId(project_id), document=doc)
    return {
        "project_id": str(state.project_id),
        "current_phase": state.current_phase.value,
        "updated_at": state.updated_at.isoformat(),
    }
