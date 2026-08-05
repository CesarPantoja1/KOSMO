from __future__ import annotations

import structlog
from ulid import ULID

from kosmo.contracts.chat import DiffCambio, PlanCambio
from kosmo.contracts.consistency import (
    ArtifactAction,
    ConsistencyEvaluationOutput,
    ConsistencyStatus,
)
from kosmo.contracts.pipeline.consistency_phase_context import (
    ConsistencyPhaseContext,
    DownstreamArtifact,
)
from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.contracts.pipeline.phase_outputs import ConsistencyReport
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import PlanChangeId, ProjectId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    DocumentRepository,
    FeatureRepository,
    RequirementRepository,
)
from kosmo.domain.sdd.discovery_diff import ChangeClass, ChangeType, SectionChange, diff_discovery_versions
from kosmo.domain.sdd.document_converters import document_to_markdown

_log = structlog.get_logger(__name__)


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
            return ConsistencyEvaluationOutput(report_id=report_id, status=ConsistencyStatus.ANALIZADO_SIN_IMPACTO)

        if not applied_changes:
            return ConsistencyEvaluationOutput(report_id=report_id, status=ConsistencyStatus.ANALIZADO_SIN_IMPACTO)

        source_content = await self._fetch_source_content(source_phase, project_id)

        applied_changes = await self._resolve_changes(source_phase, project_id, applied_changes)

        context = ConsistencyPhaseContext(
            source_phase=source_phase,
            target_phase=target_phase,
            applied_changes=applied_changes,
            downstream_artifacts=artifacts,
            source_content=source_content,
        )

        skill_name = (
            "consistency_evaluate_upstream" if target_phase == SpecPhase.DESCUBRIMIENTO else "consistency_evaluate"
        )
        try:
            raw_output = await self._agent.execute_with_skill(
                skill_name=skill_name,
                context=context,
                project_id=project_id,
            )
        except Exception:
            _log.warning(
                "consistency.evaluate_failed",
                source=source_phase.value,
                target=target_phase.value,
                project_id=str(project_id),
                exc_info=True,
            )
            return ConsistencyEvaluationOutput(
                report_id=report_id,
                status=ConsistencyStatus.ANALISIS_FALLIDO,
                failure_reason=f"El agente LLM fallo al evaluar {source_phase.value} → {target_phase.value}",
            )

        return self._parse_output(report_id, raw_output, artifacts)

    def _parse_output(  # type: ignore[reportUnknownParameterType]
        self,
        report_id: str,
        raw_output: object,
        artifacts: list[DownstreamArtifact],
    ) -> ConsistencyEvaluationOutput:
        if isinstance(raw_output, ConsistencyReport):
            return self._parse_consistency_report(report_id, raw_output, artifacts)
        if isinstance(raw_output, dict):
            return self._parse_dict_output(report_id, raw_output, artifacts)  # type: ignore[reportUnknownArgumentType]
        return ConsistencyEvaluationOutput(
            report_id=report_id,
            status=ConsistencyStatus.ANALISIS_FALLIDO,
            failure_reason="La respuesta del LLM no se pudo interpretar",
        )

    def _parse_consistency_report(
        self,
        report_id: str,
        report: ConsistencyReport,
        artifacts: list[DownstreamArtifact],
    ) -> ConsistencyEvaluationOutput:
        artifact_ids_set = {a.artifact_id for a in artifacts}
        actions: list[ArtifactAction] = []
        affected_ids: list[str] = []

        for item in report.actions:
            if item.artifact_id not in artifact_ids_set:
                continue
            if item.action not in ("update", "delete"):
                continue

            actions.append(
                ArtifactAction(
                    artifact_id=item.artifact_id,
                    action=item.action,
                    rationale=item.rationale,
                    suggested_field=item.suggested_field,
                    suggested_before=item.suggested_before,
                    suggested_after=item.suggested_after,
                )
            )
            affected_ids.append(item.artifact_id)

        status = ConsistencyStatus.ANALIZADO_CON_IMPACTO if affected_ids else ConsistencyStatus.ANALIZADO_SIN_IMPACTO
        return ConsistencyEvaluationOutput(
            report_id=report_id,
            status=status,
            affected_artifact_ids=affected_ids,
            rationale=report.overall_rationale,
            actions=actions,
        )

    def _parse_dict_output(
        self,
        report_id: str,
        raw_output: dict[str, object],
        artifacts: list[DownstreamArtifact],
    ) -> ConsistencyEvaluationOutput:
        overall_rationale: str = str(raw_output.get("overall_rationale", ""))

        actions_raw: object = raw_output.get("actions", [])
        if not isinstance(actions_raw, list):
            return ConsistencyEvaluationOutput(
                report_id=report_id,
                status=ConsistencyStatus.ANALISIS_FALLIDO,
                rationale=overall_rationale,
            )

        artifact_ids_set = {a.artifact_id for a in artifacts}
        actions: list[ArtifactAction] = []
        affected_ids: list[str] = []

        for item in actions_raw:  # type: ignore[reportUnknownVariableType]
            if not isinstance(item, dict):
                continue
            item_dict: dict[str, object] = item  # type: ignore[reportUnknownVariableType]
            artifact_id: str = str(item_dict.get("artifact_id", ""))
            if artifact_id not in artifact_ids_set:
                continue

            action_type: str = str(item_dict.get("action", ""))
            if action_type not in ("update", "delete"):
                continue

            actions.append(
                ArtifactAction(
                    artifact_id=artifact_id,
                    action=action_type,
                    rationale=str(item_dict.get("rationale", "")),
                    suggested_field=str(item_dict.get("suggested_field", "")),
                    suggested_before=str(item_dict.get("suggested_before", "")),
                    suggested_after=str(item_dict.get("suggested_after", "")),
                )
            )
            affected_ids.append(artifact_id)

        status = ConsistencyStatus.ANALIZADO_CON_IMPACTO if affected_ids else ConsistencyStatus.ANALIZADO_SIN_IMPACTO
        return ConsistencyEvaluationOutput(
            report_id=report_id,
            status=status,
            affected_artifact_ids=affected_ids,
            rationale=overall_rationale,
            actions=actions,
        )

    async def _fetch_source_content(self, source_phase: SpecPhase, project_id: ProjectId) -> str:
        if source_phase == SpecPhase.DESCUBRIMIENTO:
            doc = await self._document_repo.get_discovery(project_id)
            if doc is not None:
                return document_to_markdown(doc)
        elif source_phase == SpecPhase.CARACTERISTICAS:
            features = await self._feature_repo.list_by_project(project_id)
            if features:
                items: list[str] = []
                for f in features:
                    item_str = f"### Feature: {f.title} (ID: {f.id})\n- Descripción: {f.description}"
                    if f.origin:
                        item_str += f"\n- Origen: {f.origin}"
                    items.append(item_str)
                return "\n\n".join(items)
        return ""

    async def _resolve_changes(
        self,
        source_phase: SpecPhase,
        project_id: ProjectId,
        plan_changes: list[PlanCambio],
    ) -> list[PlanCambio]:
        if source_phase != SpecPhase.DESCUBRIMIENTO:
            return plan_changes

        try:
            previous_md = await self._document_repo.get_latest_version(project_id, SpecPhase.DESCUBRIMIENTO)
        except Exception:
            previous_md = None

        if previous_md is None:
            return plan_changes

        current_doc = await self._document_repo.get_discovery(project_id)
        if current_doc is None:
            return plan_changes
        current_md = document_to_markdown(current_doc)

        section_changes = diff_discovery_versions(previous_md, current_md)
        if not section_changes:
            return plan_changes

        return self._merge_changes(plan_changes, section_changes)

    @staticmethod
    def _merge_changes(originals: list[PlanCambio], diffs: list[SectionChange]) -> list[PlanCambio]:
        desc_by_section: dict[str, str] = {}
        for pc in originals:
            section = (pc.section or "").strip()
            if section and pc.description and pc.description != section:
                desc_by_section[section.lower()] = pc.description

        result: list[PlanCambio] = []
        for sc in diffs:
            section_key = sc.section.strip().lower()
            description = desc_by_section.get(section_key)
            if not description:
                for orig_section, desc in desc_by_section.items():
                    if orig_section in section_key or section_key in orig_section:
                        description = desc
                        break
            if not description:
                if sc.change_type == ChangeType.ADDED:
                    description = f"Seccion nueva: {sc.section}"
                elif sc.change_type == ChangeType.REMOVED:
                    description = f"Seccion eliminada: {sc.section}"
                elif sc.change_class == ChangeClass.COSMETIC:
                    description = f"Cambio cosmetico en {sc.section}"
                else:
                    description = f"Seccion modificada: {sc.section}"
            result.append(
                PlanCambio(
                    id=PlanChangeId(f"chg_diff_{ULID().hex}"),
                    section=sc.section,
                    description=description,
                    diff=DiffCambio(before=sc.before, after=sc.after),
                )
            )
        return result

    async def _fetch_downstream_artifacts(
        self, target_phase: SpecPhase, project_id: ProjectId
    ) -> list[DownstreamArtifact]:
        if target_phase == SpecPhase.DESCUBRIMIENTO:
            doc = await self._document_repo.get_discovery(project_id)
            if doc is not None:
                return [
                    DownstreamArtifact(
                        artifact_id=str(project_id),
                        artifact_type="DiscoveryDocument",
                        title="Documento de Descubrimiento",
                        description=document_to_markdown(doc)[:8000],
                    )
                ]
            return []
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
                        description=req_md[:8000],
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
                syntax = diagram.diagram_syntax[:8000] if diagram else ""
                artifacts.append(
                    DownstreamArtifact(
                        artifact_id=str(f.id),
                        artifact_type="ActivityDiagram",
                        title=f"Diagrama de {f.title}",
                        description=syntax,
                    )
                )
        return artifacts
