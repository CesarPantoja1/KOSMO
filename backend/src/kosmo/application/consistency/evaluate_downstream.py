from __future__ import annotations

import asyncio

import structlog

from kosmo.application.consistency.enrich_impact import enrich_impact_items, impact_item_to_dict
from kosmo.contracts.chat import PlanCambio
from kosmo.contracts.consistency import DOWNSTREAM_TARGETS, ConsistencyEvaluator
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    FeatureRepository,
    RequirementRepository,
)

_log = structlog.get_logger(__name__)


async def evaluate_downstream_impacts(
    evaluator: ConsistencyEvaluator,
    *,
    source_phase: SpecPhase,
    project_id: ProjectId,
    applied_changes: list[PlanCambio],
    feature_repo: FeatureRepository,
    requirement_repo: RequirementRepository,
    diagram_repo: ActivityDiagramRepository,
) -> list[dict[str, object]]:
    """Evalua la consistencia solo hacia la derecha (trazabilidad descendente).

    Los fallos de un par fuente→destino no impiden evaluar los demas destinos.
    """
    targets = DOWNSTREAM_TARGETS.get(source_phase, [])

    async def _eval(target_spec: SpecPhase) -> list[dict[str, object]]:
        try:
            result = await evaluator.evaluate(
                source_phase=source_phase,
                target_phase=target_spec,
                project_id=project_id,
                applied_changes=applied_changes,
            )
        except Exception:
            _log.warning(
                "downstream.evaluate_failed",
                project_id=str(project_id),
                source=source_phase.value,
                target=target_spec.value,
                exc_info=True,
            )
            return []

        if not result.affected_artifact_ids:
            return []

        try:
            items = await enrich_impact_items(
                result,
                target_spec,
                source_phase,
                feature_repo,
                requirement_repo,
                diagram_repo,
            )
        except Exception:
            _log.warning(
                "downstream.enrich_failed",
                project_id=str(project_id),
                target=target_spec.value,
                exc_info=True,
            )
            return []

        return [impact_item_to_dict(item) for item in items]

    gathered = await asyncio.gather(*[_eval(t) for t in targets], return_exceptions=True)

    impacts: list[dict[str, object]] = []
    for items in gathered:
        if isinstance(items, list):
            impacts.extend(items)
    return impacts
