from __future__ import annotations

from kosmo.contracts.ai.consistency import DOWNSTREAM_TARGETS
from kosmo.contracts.sdd.document import SpecPhase


def trace_downstream_phases(source: SpecPhase) -> list[SpecPhase]:
    """Fases a la derecha del flujo de trazabilidad para una fase fuente."""
    return list(DOWNSTREAM_TARGETS.get(source, []))
