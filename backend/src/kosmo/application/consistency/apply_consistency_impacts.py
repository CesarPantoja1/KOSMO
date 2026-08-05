from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

from kosmo.contracts.sdd.activity_diagram import DiagramaActividad
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)
from kosmo.domain.sdd.plan_diffs import apply_change_diff
from kosmo.domain.sdd.requirements_markdown import parse_requirements_markdown

_log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class AppliedImpact:
    target_id: str
    artifact_type: str


@dataclass(frozen=True)
class FailedImpact:
    target_id: str
    artifact_type: str
    reason: str


@dataclass(frozen=True)
class ApplyConsistencyImpactsOutput:
    applied: list[AppliedImpact] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    failed: list[FailedImpact] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


class ApplyConsistencyImpactsUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
        diagram_repo: ActivityDiagramRepository,
        traceability_repo: object | None = None,
    ) -> None:
        self._project_repo = project_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._diagram_repo = diagram_repo
        self._traceability_repo = traceability_repo

    async def execute(
        self,
        project_id: ProjectId,
        impacts: list[dict[str, object]],
    ) -> ApplyConsistencyImpactsOutput:
        project = await self._project_repo.by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(project_id),
                instance=f"/api/v1/projects/{project_id}/consistency/apply",
            )

        applied: list[AppliedImpact] = []
        failed: list[FailedImpact] = []

        for impact in impacts:
            artifact_type = str(impact.get("artifact_type", ""))
            target_id = str(impact.get("target_id", ""))
            action = str(impact.get("action", "update"))
            field = str(impact.get("field", "description"))
            before = str(impact.get("before", ""))
            after = str(impact.get("after", ""))

            if not artifact_type or not target_id:
                failed.append(
                    FailedImpact(target_id=target_id, artifact_type=artifact_type, reason="Datos incompletos")
                )
                continue

            if action == "update" and not before and not after:
                failed.append(
                    FailedImpact(target_id=target_id, artifact_type=artifact_type, reason="Sin sugerencia de cambio")
                )
                continue

            try:
                result = await self._apply_impact(artifact_type, target_id, action, field, before, after)
            except Exception as exc:
                _log.warning(
                    "consistency.apply_impact_failed",
                    target_id=target_id,
                    artifact_type=artifact_type,
                    exc_info=True,
                )
                failed.append(FailedImpact(target_id=target_id, artifact_type=artifact_type, reason=str(exc)))
                continue

            if result is None:
                applied.append(AppliedImpact(target_id=target_id, artifact_type=artifact_type))
            else:
                failed.append(FailedImpact(target_id=target_id, artifact_type=artifact_type, reason=result))

        return ApplyConsistencyImpactsOutput(applied=applied, failed=failed)

    async def _apply_impact(
        self,
        artifact_type: str,
        target_id: str,
        action: str,
        field: str,
        before: str,
        after: str,
    ) -> str | None:
        feature_id = FeatureId(target_id)

        if artifact_type == "EARSRequirement":
            if action == "delete":
                return None  # cascada BD: la feature padre ya se eliminó
            return await self._apply_requirement(feature_id, before, after)

        if artifact_type == "Feature":
            if action == "delete":
                return await self._delete_feature(feature_id)
            return await self._update_feature(feature_id, field, before, after)

        if artifact_type == "ActivityDiagram":
            if action == "delete":
                return None  # cascada BD: la feature padre ya se eliminó
            return await self._update_diagram(feature_id, before, after)

        return f"Tipo de artefacto desconocido: {artifact_type}"

    async def _apply_requirement(self, feature_id: FeatureId, before: str, after: str) -> str | None:
        markdown = await self._requirement_repo.by_feature_id(feature_id)
        if markdown is None:
            return "El documento de requisitos no existe"

        result = apply_change_diff(markdown, before=before, after=after)
        if result is None:
            return "El texto original no se encontro en los requisitos"

        await self._requirement_repo.save(feature_id, result)

        feature = await self._feature_repo.by_id(feature_id)
        if feature is not None:
            try:
                parsed = parse_requirements_markdown(result, feature_id, feature.number)
                items = [
                    {
                        "id": str(r.id),
                        "feature_id": str(r.feature_id),
                        "requirement_number": r.requirement_number,
                        "display_id": r.display_id,
                        "title": r.title,
                        "pattern": r.pattern.name if hasattr(r.pattern, "name") else str(r.pattern),
                        "statement": r.statement,
                        "origin": r.origin,
                        "acceptance_criteria": [
                            {"scenario": ac.scenario, "given": ac.given, "when": ac.when, "then": ac.then}
                            for ac in r.acceptance_criteria
                        ],
                    }
                    for r in parsed
                ]
                await self._requirement_repo.save_items(feature_id, items)  # type: ignore[reportArgumentType]

                if self._traceability_repo is not None:
                    await self._traceability_repo.delete_by_entity_id(str(feature_id))  # type: ignore[reportAttributeAccessIssue]
                    for r in parsed:
                        await self._traceability_repo.add_edge(  # type: ignore[reportAttributeAccessIssue]
                            source_type="feature",
                            source_id=str(feature_id),
                            target_type="requirement",
                            target_id=str(r.id),
                        )
            except Exception:
                _log.warning(
                    "consistency.reparse_failed",
                    feature_id=str(feature_id),
                    exc_info=True,
                )

        return None

    async def _update_feature(self, feature_id: FeatureId, field: str, before: str, after: str) -> str | None:
        feature = await self._feature_repo.by_id(feature_id)
        if feature is None:
            return "La caracteristica no existe"

        valid_fields = {"title", "description", "origin"}
        if field not in valid_fields:
            return f"Campo no modificable: {field}"

        current: str = str(getattr(feature, field, ""))
        result = apply_change_diff(current, before=before, after=after)
        if result is None:
            return f"El texto original no se encontro en {field} de la caracteristica"

        setattr(feature, field, result)
        if field == "title":
            feature.slug = result.lower().replace(" ", "-")
        feature.updated_at = datetime.now(UTC)
        await self._feature_repo.save(feature)
        return None

    async def _delete_feature(self, feature_id: FeatureId) -> str | None:
        feature = await self._feature_repo.by_id(feature_id)
        if feature is None:
            return "La caracteristica no existe"

        await self._feature_repo.delete(feature_id)

        if self._traceability_repo is not None:
            try:
                await self._traceability_repo.delete_by_entity_id(str(feature_id))  # type: ignore[reportAttributeAccessIssue]
            except Exception:
                _log.warning(
                    "consistency.delete_feature.traceability_cleanup_failed",
                    feature_id=str(feature_id),
                    exc_info=True,
                )

        _log.info(
            "consistency.delete_feature.success",
            feature_id=str(feature_id),
            display_id=feature.display_id,
        )
        return None

    async def _update_diagram(self, feature_id: FeatureId, before: str, after: str) -> str | None:
        diagram = await self._diagram_repo.by_feature_id(feature_id)
        if diagram is None:
            return "El diagrama no existe"

        result = apply_change_diff(diagram.diagram_syntax, before=before, after=after)
        if result is None:
            return "El texto original no se encontro en el diagrama"

        updated = DiagramaActividad(
            id=diagram.id,
            feature_id=diagram.feature_id,
            diagram_syntax=result,
            created_at=diagram.created_at,
            updated_at=datetime.now(UTC),
        )
        await self._diagram_repo.save(updated)
        return None
