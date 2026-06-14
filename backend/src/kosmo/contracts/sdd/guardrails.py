from __future__ import annotations

from dataclasses import dataclass, field

DISCOVERY_SECTIONS: list[str] = [
    "Vision del producto",
    "Espacio del problema",
    "Actores",
    "Propuesta de valor",
    "Casos de uso",
    "Capacidades principales",
    "Reglas de negocio",
    "Atributos de calidad",
    "Alcance",
]

PROHIBITED_TERMS: list[str] = [
    "API",
    "api",
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
    "docker",
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
    "redis",
    "MongoDB",
    "PostgreSQL",
    "Kubernetes",
    "K8s",
    "AWS",
    "GCP",
    "Azure",
]


@dataclass(frozen=True)
class GuardrailViolation:
    term: str
    context: str
    section: str = ""


@dataclass(frozen=True)
class GuardrailResult:
    is_valid: bool
    violations: list[GuardrailViolation] = field(default_factory=list)

    @property
    def error_messages(self) -> list[str]:
        return [
            f'Término prohibido "{v.term}" encontrado en {v.section}: {v.context}'
            for v in self.violations
        ]
