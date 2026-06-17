from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ulid import ULID


@dataclass
class Violation:
    loc: list[str]
    msg: str
    input: Any = None


@dataclass
class ProblemDetail:
    type: str
    title: str
    status: int
    detail: str
    instance: str
    trace_id: str = field(default_factory=lambda: ULID().hex)
    violations: list[Violation] = field(default_factory=lambda: list[Violation]())


class SpecError(Exception):
    def __init__(self, problem: ProblemDetail) -> None:
        self.problem = problem
        super().__init__(problem.detail)


class ProjectNotFoundError(SpecError):
    def __init__(
        self,
        *,
        project_id: str,
        instance: str = "/api/v1/projects",
    ) -> None:
        problem = ProblemDetail(
            type="urn:kosmo:projects:not-found",
            title="Proyecto no encontrado",
            status=404,
            detail=f"El proyecto {project_id} no existe",
            instance=instance,
        )
        super().__init__(problem)


class FeatureNotFoundError(SpecError):
    def __init__(
        self,
        *,
        feature_id: str,
        instance: str = "/api/v1/features",
    ) -> None:
        problem = ProblemDetail(
            type="urn:kosmo:features:not-found",
            title="Feature no encontrada",
            status=404,
            detail=f"La feature {feature_id} no existe en este proyecto",
            instance=instance,
        )
        super().__init__(problem)


class DocumentValidationError(SpecError):
    def __init__(
        self,
        *,
        detail: str,
        violations: list[Violation] | None = None,
        instance: str = "/api/v1/discovery",
    ) -> None:
        problem = ProblemDetail(
            type="urn:kosmo:document:invalid-structure",
            title="Documento inválido",
            status=422,
            detail=detail,
            instance=instance,
            violations=violations or [],
        )
        super().__init__(problem)


class DocumentNotFoundError(SpecError):
    def __init__(
        self,
        *,
        document_type: str,
        instance: str = "/api/v1/discovery",
    ) -> None:
        problem = ProblemDetail(
            type="urn:kosmo:document:not-found",
            title="Documento no encontrado",
            status=404,
            detail=f"El documento de tipo {document_type} no existe",
            instance=instance,
        )
        super().__init__(problem)


class MarkdownParseError(SpecError):
    def __init__(
        self,
        *,
        detail: str,
        instance: str = "/api/v1/discovery",
    ) -> None:
        problem = ProblemDetail(
            type="urn:kosmo:document:parse-error",
            title="Error de parseo Markdown",
            status=422,
            detail=detail,
            instance=instance,
        )
        super().__init__(problem)


class LLMInvocationError(SpecError):
    def __init__(
        self,
        *,
        detail: str,
        instance: str = "/api/v1/pipeline",
    ) -> None:
        problem = ProblemDetail(
            type="urn:kosmo:llm:invocation-error",
            title="Error de invocación al modelo de IA",
            status=502,
            detail=detail,
            instance=instance,
        )
        super().__init__(problem)
