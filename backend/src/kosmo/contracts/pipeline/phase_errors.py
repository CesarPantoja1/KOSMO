from __future__ import annotations

from kosmo.contracts.sdd.errors import ProblemDetail, SpecError


class PhaseTransitionError(SpecError):
    def __init__(
        self,
        *,
        detail: str,
        instance: str = "/api/v1/pipeline",
    ) -> None:
        problem = ProblemDetail(
            type="urn:kosmo:pipeline:phase-transition-error",
            title="Transicion de fase invalida",
            status=409,
            detail=detail,
            instance=instance,
        )
        super().__init__(problem)


class PhaseNotSupportedError(SpecError):
    def __init__(
        self,
        *,
        phase: str,
        instance: str = "/api/v1/pipeline",
    ) -> None:
        problem = ProblemDetail(
            type="urn:kosmo:pipeline:phase-not-supported",
            title="Fase no soportada",
            status=400,
            detail=f"La fase {phase} no esta implementada en el pipeline actual",
            instance=instance,
        )
        super().__init__(problem)