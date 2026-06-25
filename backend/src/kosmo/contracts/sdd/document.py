from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from kosmo.contracts.sdd.ids import FeatureId


class MarkType(StrEnum):
    bold = "bold"
    italic = "italic"
    code = "code"
    link = "link"
    underline = "underline"
    strikethrough = "strikethrough"


@dataclass(frozen=True)
class TextMark:
    type: MarkType
    attrs: dict[str, Any] = field(default_factory=dict)  # type: ignore[reportUnknownVariableType]


@dataclass(frozen=True)
class SectionHeading:
    text: str
    level: int = 2
    slug: str = ""


@dataclass(frozen=True)
class DocumentNode:
    type: str
    content: str = ""
    heading: SectionHeading | None = None
    marks: list[TextMark] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    children: list[DocumentNode] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    attrs: dict[str, Any] = field(default_factory=dict)  # type: ignore[reportUnknownVariableType]


@dataclass(frozen=True)
class RichTextDocument:
    nodes: list[DocumentNode] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]

    @property
    def sections(self) -> list[SectionHeading]:
        return [
            node.heading
            for node in self.nodes
            if node.type == "heading" and node.heading is not None
        ]

    @property
    def section_count(self) -> int:
        return len(self.sections)


@dataclass(frozen=True)
class FeatureSelection:
    feature_id: FeatureId
    selected: bool = True


@dataclass(frozen=True)
class SuggestedFeature:
    number: int
    title: str
    description: str
    rationale: str
    inferred_from: list[str] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


@dataclass(frozen=True)
class AcceptanceCriterion:
    given: str
    when: str
    then: str


class EARSPattern(StrEnum):
    ubiquitous = "ubiquitous"
    event_driven = "event_driven"
    state_driven = "state_driven"
    optional = "optional"
    unwanted = "unwanted"
    complex = "complex"


class ProjectPhase(StrEnum):
    descubrimiento = "descubrimiento"
    caracteristicas = "caracteristicas"
    requisitos = "requisitos"
    modelo = "modelo"
    implementacion = "implementacion"


class ProjectStatus(StrEnum):
    en_proceso = "en_proceso"
    finalizado = "finalizado"


class SpecPhase(StrEnum):
    DESCUBRIMIENTO = "descubrimiento"
    CARACTERISTICAS = "caracteristicas"
    REQUISITOS = "requisitos"
    MODELO = "modelo"
    IMPLEMENTACION = "implementacion"


class EARSPatternLabel(StrEnum):
    ubiquitous = "Requisitos Ubicuos"
    event_driven = "Requisitos Basados en Eventos"
    state_driven = "Requisitos Determinados por el Estado"
    optional = "Requisitos Opcionales"
    unwanted = "Requisitos de Respuestas Deseadas ante Fallos"
    complex = "Requisitos Complejos"


EARSPattern_SYNTAX: dict[EARSPattern, str] = {
    EARSPattern.ubiquitous: "[El sistema] shall [comportamiento]",
    EARSPattern.event_driven: "CUANDO [evento], [el sistema] shall [comportamiento]",
    EARSPattern.state_driven: "MIENTRAS [estado], [el sistema] shall [comportamiento]",
    EARSPattern.optional: "DONDE [opción], [el sistema] shall [comportamiento]",
    EARSPattern.unwanted: (
        "SI [condición no deseada], [el sistema] shall [comportamiento de mitigación]"
    ),
    EARSPattern.complex: "MIENTRAS [estado] Y [evento], [el sistema] shall [comportamiento]",
}
