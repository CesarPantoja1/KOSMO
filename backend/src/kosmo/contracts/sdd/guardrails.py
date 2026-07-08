from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GuardrailViolation:
    term: str
    context: str
    section: str = ""


@dataclass(frozen=True)
class GuardrailResult:
    is_valid: bool
    violations: list[GuardrailViolation] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]

    @property
    def error_messages(self) -> list[str]:
        return [f'Termino prohibido "{v.term}" encontrado en {v.section}: {v.context}' for v in self.violations]


DISCOVERY_SECTIONS: list[str] = [
    "Visión del producto",
    "Espacio del problema",
    "Actores",
    "Propuesta de valor",
    "Metas del producto",
    "Reglas de negocio",
    "Alcance",
]

PROHIBITED_TERMS: list[str] = [
    "API",
    "base de datos",
    "database",
    "microservicio",
    "microservicios",
    "endpoint",
    "endpoints",
    "servidor",
    "server",
    "lenguaje de programacion",
    "framework",
    "protocolo",
    "protocolos",
    "arquitectura",
    "deployment",
    "deploy",
    "Docker",
    "cloud",
    "SQL",
    "HTTP",
    "REST",
    "GraphQL",
    "microservice",
    "backend",
    "frontend",
    "cache",
    "caché",
    "Redis",
    "MongoDB",
    "PostgreSQL",
    "Kubernetes",
    "K8s",
    "AWS",
    "GCP",
    "Azure",
    "plataforma",
    "sistema",
    "software",
    "web",
    "aplicación",
    "aplicaciones",
]

FEATURE_LEVEL_PROHIBITED_TERMS: list[str] = [
    "propuesta de valor",
    "modelo de negocio",
    "ventaja competitiva",
    "diferenciador",
    "monetizacion",
    "monetización",
    "ROI",
    "KPI",
    "stakeholder",
    "oportunidad de mercado",
    "segmento de mercado",
    "caso de negocio",
    "estrategia comercial",
]
