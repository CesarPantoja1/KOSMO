from fastapi import APIRouter, HTTPException, Request

from kosmo.contracts.sdd.discovery import RawIdea
from kosmo.contracts.sdd.ids import ProjectId, SpecId
from kosmo.contracts.sdd.repositories import ProjectRepository
from kosmo.domain.agents.canvas_sync.service import CanvasEdit

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


@specs_router.post("/projects/{project_id}/specs", response_model=dict)
async def create_spec(
    project_id: str,
    raw_idea: RawIdea,
    request: Request,
) -> dict:
    from kosmo.application.sdd.capture import CaptureDiscoveryUseCase

    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    uc = CaptureDiscoveryUseCase(
        spec_repo=request.app.state.spec_repo,
        project_repo=request.app.state.project_repo,
        llm_client=request.app.state.llm_client,
    )
    spec = await uc.execute(
        project_id=pid,
        description=raw_idea.text,
        optional_context=raw_idea.optional_context,
    )
    return spec.model_dump(mode="json")


@specs_router.post("/specs/{spec_id}/advance/requirements", response_model=dict)
async def advance_requirements(
    spec_id: str,
    request: Request,
) -> dict:
    from kosmo.application.sdd.requirements import GenerateRequirementsUseCase

    uc = GenerateRequirementsUseCase(
        spec_repo=request.app.state.spec_repo,
        llm_client=request.app.state.llm_client,
    )
    spec = await uc.execute(SpecId(spec_id))
    return spec.model_dump(mode="json")


@specs_router.post("/specs/{spec_id}/advance/design", response_model=dict)
async def advance_design(
    spec_id: str,
    request: Request,
) -> dict:
    from kosmo.application.sdd.design import GenerateDesignUseCase

    uc = GenerateDesignUseCase(
        spec_repo=request.app.state.spec_repo,
        llm_client=request.app.state.llm_client,
    )
    spec = await uc.execute(SpecId(spec_id))
    return spec.model_dump(mode="json")


@specs_router.post("/specs/{spec_id}/advance/tasks", response_model=dict)
async def advance_tasks(
    spec_id: str,
    request: Request,
) -> dict:
    from kosmo.application.sdd.tasks import DecomposeTasksUseCase

    uc = DecomposeTasksUseCase(
        spec_repo=request.app.state.spec_repo,
        llm_client=request.app.state.llm_client,
    )
    spec = await uc.execute(SpecId(spec_id))
    return spec.model_dump(mode="json")


@specs_router.get("/specs/{spec_id}", response_model=dict)
async def get_spec(
    spec_id: str,
    request: Request,
) -> dict:
    spec = await request.app.state.spec_repo.get(SpecId(spec_id))
    if spec is None:
        raise HTTPException(status_code=404, detail="Especificacion no encontrada")
    return spec.model_dump(mode="json")


@specs_router.post("/specs/{spec_id}/canvas", response_model=dict)
async def sync_canvas(
    spec_id: str,
    edit: CanvasEdit,
    request: Request,
) -> dict:
    from kosmo.application.sdd.canvas import SyncCanvasEditUseCase

    uc = SyncCanvasEditUseCase(
        spec_repo=request.app.state.spec_repo,
        llm_client=request.app.state.llm_client,
    )
    spec, delta = await uc.execute(SpecId(spec_id), edit)
    return {"spec": spec.model_dump(mode="json"), "delta": delta.model_dump()}
