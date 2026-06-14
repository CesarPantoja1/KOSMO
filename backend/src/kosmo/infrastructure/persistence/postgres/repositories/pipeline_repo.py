from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.memory.user_preference import UserPreference
from kosmo.contracts.pipeline.pipeline_ports import PipelineRepository
from kosmo.contracts.pipeline.pipeline_state import KOSMOPipelineState, PhaseTransitionRecord
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, PipelineId, ProjectId, UserId
from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.persistence.postgres.models import PipelineStateModel


class SqlAlchemyPipelineRepository(PipelineRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, project_id: ProjectId) -> KOSMOPipelineState | None:
        async with self._session_factory() as session:
            stmt = select(PipelineStateModel).where(
                PipelineStateModel.project_id == str(project_id)
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._to_entity(model)

    async def save(self, state: KOSMOPipelineState) -> KOSMOPipelineState:
        async with self._session_factory() as session:
            stmt = select(PipelineStateModel).where(
                PipelineStateModel.project_id == str(state.project_id)
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            state_json = self._serialize_state(state)

            if model is None:
                model = PipelineStateModel(
                    id=IdGenerator.generate("pipeline"),
                    project_id=str(state.project_id),
                    user_id=str(state.user_id),
                    pipeline_id=str(state.pipeline_id),
                    current_phase=state.current_phase.value,
                    state_json=state_json,
                )
                session.add(model)
            else:
                model.current_phase = state.current_phase.value
                model.state_json = state_json
                model.updated_at = datetime.now(UTC)

            await session.commit()
            return state

    async def get_by_id(self, pipeline_id: PipelineId) -> KOSMOPipelineState | None:
        async with self._session_factory() as session:
            model = await session.get(PipelineStateModel, str(pipeline_id))
            if model is None:
                return None
            return self._to_entity(model)

    async def delete(self, project_id: ProjectId) -> None:
        async with self._session_factory() as session:
            stmt = select(PipelineStateModel).where(
                PipelineStateModel.project_id == str(project_id)
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model:
                await session.delete(model)
                await session.commit()

    def _to_entity(self, model: PipelineStateModel) -> KOSMOPipelineState:
        state_data = model.state_json if isinstance(model.state_json, dict) else {}

        features = []
        for f_data in state_data.get("features", []):
            features.append(
                Feature(
                    id=FeatureId(f_data.get("id", IdGenerator.generate("feature"))),
                    number=f_data.get("number", 0),
                    title=f_data.get("title", ""),
                    slug=f_data.get("slug", ""),
                    description=f_data.get("description", ""),
                    rationale=f_data.get("rationale", ""),
                    inferred_from=f_data.get("inferred_from", []),
                )
            )

        user_prefs = []
        for p_data in state_data.get("user_preferences", []):
            user_prefs.append(
                UserPreference(
                    id=p_data.get("id", ""),
                    user_id=p_data.get("user_id", ""),
                    rule_text=p_data.get("rule_text", ""),
                    category=p_data.get("category", "general"),
                    priority=p_data.get("priority", 0),
                )
            )

        phase_history = []
        for ph_data in state_data.get("phase_history", []):
            phase_history.append(
                PhaseTransitionRecord(
                    from_phase=SpecPhase(ph_data.get("from_phase", "descubrimiento")),
                    to_phase=SpecPhase(ph_data.get("to_phase", "descubrimiento")),
                    human_approved=ph_data.get("human_approved", False),
                    validation_passed=ph_data.get("validation_passed", False),
                    notes=ph_data.get("notes"),
                )
            )

        return KOSMOPipelineState(
            project_id=ProjectId(model.project_id),
            user_id=UserId(model.user_id),
            pipeline_id=PipelineId(model.pipeline_id),
            current_phase=SpecPhase(model.current_phase),
            features=features,
            requirements_by_feature={},
            user_preferences=user_prefs,
            phase_history=phase_history,
            errors=state_data.get("errors", []),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _serialize_state(self, state: KOSMOPipelineState) -> dict:
        result: dict = {
            "features": [],
            "requirements_by_feature": {},
            "user_preferences": [],
            "phase_history": [],
            "errors": state.errors,
        }

        for f in state.features:
            result["features"].append(
                {
                    "id": str(f.id),
                    "number": f.number,
                    "title": f.title,
                    "slug": f.slug,
                    "description": f.description,
                    "rationale": f.rationale,
                    "inferred_from": f.inferred_from,
                }
            )

        for p in state.user_preferences:
            result["user_preferences"].append(
                {
                    "id": p.id,
                    "user_id": p.user_id,
                    "rule_text": p.rule_text,
                    "category": p.category,
                    "priority": p.priority,
                }
            )

        for ph in state.phase_history:
            result["phase_history"].append(
                {
                    "from_phase": ph.from_phase.value,
                    "to_phase": ph.to_phase.value,
                    "human_approved": ph.human_approved,
                    "validation_passed": ph.validation_passed,
                    "notes": ph.notes,
                }
            )

        return result
