from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kosmo.contracts.sdd.constitution import Constitution
from kosmo.contracts.sdd.discovery import DiscoveryDocument, ProjectRoadmap
from kosmo.contracts.sdd.domain_model import DomainModel
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.contracts.sdd.ids import ProjectId, SpecId, TaskId
from kosmo.contracts.sdd.spec import SpecDocument, SpecPhase
from kosmo.contracts.sdd.tasks import Task
from kosmo.infrastructure.persistence.postgres.models.sdd import (
    RequirementModel,
    SpecModel,
    TaskModel,
)


class SqlAlchemySpecRepository:
    def __init__(self, session_factory: object) -> None:  # type: ignore[override]
        self._session_factory = session_factory  # type: ignore[assignment]

    async def add(self, spec: SpecDocument) -> None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            model = SpecModel(  # type: ignore[call-arg]
                id=spec.id,
                project_id=spec.project_id,
                phase=spec.phase.value,
                discovery_data=spec.discovery.model_dump() if spec.discovery else None,
                roadmap_data=spec.roadmap.model_dump() if spec.roadmap else None,
                design_data=spec.design.model_dump() if spec.design else None,
                constitution_data=spec.constitution.model_dump() if spec.constitution else None,
                created_by=spec.created_by,
            )
            session.add(model)
            await session.commit()

    async def get(self, spec_id: SpecId) -> SpecDocument | None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            result = await session.execute(
                select(SpecModel).where(SpecModel.id == spec_id)  # type: ignore[arg-type,union-attr]
            )
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return await self._to_document(model, session)

    async def update(self, spec: SpecDocument) -> None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            result = await session.execute(
                select(SpecModel).where(SpecModel.id == spec.id)  # type: ignore[arg-type,union-attr]
            )
            model = result.scalar_one_or_none()
            if model is None:
                return
            model.phase = spec.phase.value  # type: ignore[union-attr]
            model.discovery_data = spec.discovery.model_dump() if spec.discovery else None  # type: ignore[union-attr]
            model.roadmap_data = spec.roadmap.model_dump() if spec.roadmap else None  # type: ignore[union-attr]
            model.design_data = spec.design.model_dump() if spec.design else None  # type: ignore[union-attr]
            model.constitution_data = (  # type: ignore[union-attr]
                spec.constitution.model_dump() if spec.constitution else None
            )
            await session.commit()

    async def list_by_project(self, project_id: ProjectId) -> list[SpecDocument]:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            result = await session.execute(
                select(SpecModel)
                .where(SpecModel.project_id == project_id)  # type: ignore[arg-type,union-attr]
                .order_by(SpecModel.created_at.desc())  # type: ignore[arg-type,union-attr]
            )
            models = result.scalars().all()
            docs: list[SpecDocument] = []
            for m in models:
                try:
                    doc = await self._to_document(m, session)
                    if doc:
                        docs.append(doc)
                except Exception:
                    continue
            return docs

    async def _to_document(  # type: ignore[no-untyped-def]
        self, model: object, session: AsyncSession
    ) -> SpecDocument:
        reqs_result = await session.execute(  # type: ignore[union-attr]
            select(RequirementModel).where(RequirementModel.spec_id == model.id)  # type: ignore[arg-type,union-attr]
        )
        req_models = reqs_result.scalars().all()

        tasks_result = await session.execute(  # type: ignore[union-attr]
            select(TaskModel).where(TaskModel.spec_id == model.id)  # type: ignore[arg-type,union-attr]
        )
        task_models = tasks_result.scalars().all()

        import json as _json

        def _ensure_list(value: object) -> list[object]:
            if value is None:
                return []
            if isinstance(value, str):
                parsed = _json.loads(value)
                return parsed if isinstance(parsed, list) else [parsed]
            if isinstance(value, list):
                return value
            return [value]

        requirements: list[EARSRequirement] = []
        for rm in req_models:  # type: ignore[assignment]
            requirements.append(
                EARSRequirement(
                    id=rm.id,  # type: ignore[arg-type,union-attr]
                    pattern=rm.pattern,  # type: ignore[arg-type,union-attr]
                    trigger=rm.trigger,  # type: ignore[arg-type,union-attr]
                    system=rm.system,  # type: ignore[arg-type,union-attr]
                    response=rm.response,  # type: ignore[arg-type,union-attr]
                    acceptance_criteria=_ensure_list(rm.acceptance_criteria),  # type: ignore[arg-type,union-attr]
                    source_statement=rm.source_statement,  # type: ignore[arg-type,union-attr]
                    traceability=_ensure_list(rm.traceability),  # type: ignore[arg-type,union-attr]
                )
            )

        tasks: list[Task] = []
        for tm in task_models:  # type: ignore[assignment]
            tasks.append(
                Task(
                    id=TaskId(tm.id),  # type: ignore[arg-type,union-attr]
                    title=tm.title,  # type: ignore[arg-type,union-attr]
                    description=tm.description,  # type: ignore[arg-type,union-attr]
                    boundary=tm.boundary,  # type: ignore[arg-type,union-attr]
                    depends_on=_ensure_list(tm.depends_on),  # type: ignore[arg-type,union-attr]
                    requirements=_ensure_list(tm.requirements),  # type: ignore[arg-type,union-attr]
                    acceptance_criteria=_ensure_list(tm.acceptance_criteria),  # type: ignore[arg-type,union-attr]
                    status=tm.status,  # type: ignore[arg-type,union-attr]
                    parallelizable=tm.parallelizable,  # type: ignore[arg-type,union-attr]
                )
            )

        discovery: DiscoveryDocument | None = None
        if model.discovery_data:  # type: ignore[union-attr]
            discovery = DiscoveryDocument.model_validate(model.discovery_data)  # type: ignore[union-attr]

        return SpecDocument(
            id=SpecId(model.id),  # type: ignore[arg-type,union-attr]
            project_id=ProjectId(model.project_id),  # type: ignore[arg-type,union-attr]
            discovery=discovery,
            roadmap=ProjectRoadmap.model_validate(model.roadmap_data)  # type: ignore[union-attr]
            if model.roadmap_data  # type: ignore[union-attr]
            else None,
            requirements=requirements,
            design=DomainModel.model_validate(model.design_data) if model.design_data else None,  # type: ignore[union-attr]
            tasks=tasks,
            phase=SpecPhase(model.phase),  # type: ignore[arg-type,union-attr]
            created_by=model.created_by,  # type: ignore[arg-type,union-attr]
            created_at=model.created_at,  # type: ignore[arg-type,union-attr]
            updated_at=model.updated_at,  # type: ignore[arg-type,union-attr]
            constitution=Constitution.model_validate(model.constitution_data)  # type: ignore[union-attr]
            if model.constitution_data  # type: ignore[union-attr]
            else None,
        )
