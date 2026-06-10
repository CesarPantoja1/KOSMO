from typing import Annotated

from fastapi import APIRouter, Depends, Request

from kosmo.contracts.auth.principal import Principal
from kosmo.contracts.sdd.errors import SpecNotFoundError
from kosmo.contracts.sdd.ids import ProjectId, SpecId
from kosmo.contracts.sdd.repositories import ProjectRepository
from kosmo.infrastructure.api.dependencies.auth import get_principal

specs_router = APIRouter(prefix="/api/v1", tags=["specs"])


async def _resolve_project_identifier(
    project_repo: ProjectRepository, identifier: str
) -> ProjectId:
    if identifier.startswith("prj_"):
        return ProjectId(identifier)
    project = await project_repo.get_by_slug(identifier)
    if project is not None:
        return project.id
    return ProjectId(identifier)


@specs_router.get("/specs/{spec_id}", response_model=dict)
async def get_spec(
    spec_id: str,
    request: Request,
    _principal: Annotated[Principal, Depends(get_principal)],
) -> dict:
    spec = await request.app.state.spec_repo.get(SpecId(spec_id))
    if spec is None:
        raise SpecNotFoundError(spec_id)
    return spec.model_dump(mode="json")
