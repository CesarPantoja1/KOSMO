from __future__ import annotations

from ulid import ULID

from kosmo.contracts.chat import PlanCambio
from kosmo.contracts.consistency import ConsistencyEvaluationOutput
from kosmo.contracts.pipeline.consistency_phase_context import (
    ConsistencyPhaseContext,
    DownstreamArtifact,
)
from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    DocumentRepository,
    FeatureRepository,
    RequirementRepository,
)


class EvaluateConsistencyUseCase:
    def __init__(
        self,
        agent: AgentPort,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
        diagram_repo: ActivityDiagramRepository,
        document_repo: DocumentRepository,
    ) -> None:
        self._agent = agent
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._diagram_repo = diagram_repo
        self._document_repo = document_repo

    async def evaluate(
        self,
        *,
        source_phase: SpecPhase,
        target_phase: SpecPhase,
        project_id: ProjectId,
        applied_changes: list[PlanCambio],
    ) -> ConsistencyEvaluationOutput:
        report_id = f"cnr_{ULID().hex}"
        artifacts = await self._fetch_downstream_artifacts(target_phase, project_id)

        if not artifacts:
            return ConsistencyEvaluationOutput(report_id=report_id, affected_artifact_ids=[])

        if not applied_changes:
            return ConsistencyEvaluationOutput(report_id=report_id, affected_artifact_ids=[])

        context = ConsistencyPhaseContext(
            source_phase=source_phase,
            target_phase=target_phase,
            applied_changes=applied_changes,
            downstream_artifacts=artifacts,
        )

        try:
            raw_output = await self._agent.execute_with_skill(
                skill_name="consistency_evaluate",
                context=context,
                project_id=project_id,
            )
        except Exception:
            return ConsistencyEvaluationOutput(report_id=report_id, affected_artifact_ids=[])

        if not isinstance(raw_output, dict):
            return ConsistencyEvaluationOutput(report_id=report_id, affected_artifact_ids=[])

        affected_ids_raw: list[object] = raw_output.get("affected_artifact_ids", [])  # type: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if not isinstance(affected_ids_raw, list):
            return ConsistencyEvaluationOutput(report_id=report_id, affected_artifact_ids=[])

        valid_ids: list[str] = []
        for aid in affected_ids_raw:  # type: ignore[reportUnknownVariableType]
            if isinstance(aid, str) and any(a.artifact_id == aid for a in artifacts):
                valid_ids.append(aid)
        return ConsistencyEvaluationOutput(report_id=report_id, affected_artifact_ids=valid_ids)

    async def _fetch_downstream_artifacts(
        self, target_phase: SpecPhase, project_id: ProjectId
    ) -> list[DownstreamArtifact]:
        if target_phase == SpecPhase.CARACTERISTICAS:
            return await self._fetch_features(project_id)
        if target_phase == SpecPhase.REQUISITOS:
            return await self._fetch_requirements(project_id)
        if target_phase == SpecPhase.MODELO:
            return await self._fetch_models(project_id)
        return []

    async def _fetch_features(self, project_id: ProjectId) -> list[DownstreamArtifact]:
        features = await self._feature_repo.list_by_project(project_id)
        return [
            DownstreamArtifact(
                artifact_id=str(f.id),
                artifact_type="Feature",
                title=f.title,
                description=f.description,
            )
            for f in features
        ]

    async def _fetch_requirements(self, project_id: ProjectId) -> list[DownstreamArtifact]:
        features = await self._feature_repo.list_by_project(project_id)
        artifacts: list[DownstreamArtifact] = []
        for f in features:
            req_md = await self._requirement_repo.by_feature_id(f.id)
            if req_md is not None:
                artifacts.append(
                    DownstreamArtifact(
                        artifact_id=str(f.id),
                        artifact_type="EARSRequirement",
                        title=f"Requisitos de {f.title}",
                        description=req_md[:500],
                    )
                )
        return artifacts

    async def _fetch_models(self, project_id: ProjectId) -> list[DownstreamArtifact]:
        features = await self._feature_repo.list_by_project(project_id)
        artifacts: list[DownstreamArtifact] = []
        for f in features:
            diagram_exists = await self._diagram_repo.exists(f.id)
            if diagram_exists:
                diagram = await self._diagram_repo.by_feature_id(f.id)
                syntax = diagram.diagram_syntax[:500] if diagram else ""
                artifacts.append(
                    DownstreamArtifact(
                        artifact_id=str(f.id),
                        artifact_type="ActivityDiagram",
                        title=f"Diagrama de {f.title}",
                        description=syntax,
                    )
                )
        return artifacts
