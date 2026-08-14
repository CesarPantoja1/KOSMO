from __future__ import annotations

from kosmo.contracts.persistence import OutboxPort
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.sdd.traceability_tracer import trace_downstream_phases


async def trigger_downstream_evaluation(
    outbox: OutboxPort | None,
    *,
    project_id: ProjectId,
    source_phase: SpecPhase,
    changes: list[dict[str, str]],
) -> None:
    """Encoda la evaluación de consistencia de todas las fases a la derecha
    de la fase fuente. No-op sin outbox o sin fases downstream."""
    if outbox is None:
        return
    if not trace_downstream_phases(source_phase):
        return
    await outbox.enqueue(
        "consistency_evaluate",
        {
            "project_id": str(project_id),
            "source_phase": source_phase.value,
            "changes": changes,
        },
    )
