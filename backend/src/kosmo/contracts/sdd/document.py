from __future__ import annotations

from enum import StrEnum


class ProjectPhase(StrEnum):
    descubrimiento = "descubrimiento"
    requisitos = "requisitos"
    modelado = "modelado"
    desarrollo = "desarrollo"
    finalizado = "finalizado"


class ProjectStatus(StrEnum):
    en_proceso = "en_proceso"
    completado = "completado"
    archivado = "archivado"


class SpecPhase(StrEnum):
    discovery = "discovery"
    requirements = "requirements"
    modeling = "modeling"


class MarkType(StrEnum):
    bold = "bold"
    italic = "italic"
    code = "code"


class EARSPattern(StrEnum):
    ubiquitous = "ubiquitous"
    event_driven = "event_driven"
    unwanted = "unwanted"
    state_driven = "state_driven"


class EARSPatternLabel(StrEnum):
    UBI = "UBI"
    EVE = "EVE"
    UNW = "UNW"
    STA = "STA"


EARSPattern_SYNTAX: str = ""


class DocumentNode:
    pass


class AcceptanceCriterion:
    pass


class FeatureSelection:
    pass


class RichTextDocument:
    pass


class SectionHeading:
    pass


class SuggestedFeature:
    pass


class TextMark:
    pass
