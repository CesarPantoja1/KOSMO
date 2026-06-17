from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GuardrailViolation:
    message: str


@dataclass
class GuardrailResult:
    passed: bool = True
    violations: list[GuardrailViolation] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]


# Secciones que debe tener el documento de descubrimiento
DISCOVERY_SECTIONS: list[str] = [
    "Vision del Producto",
    "Problema que Resuelve",
    "Publico Objetivo",
    "Propuesta de Valor",
    "Contexto del Negocio",
]

# Términos técnicos que la IA tiene prohibido usar en la visión del producto.
# Son reemplazados automáticamente por output_guardrails.auto_repair_technical_terms.
PROHIBITED_TERMS: list[str] = [
    # Infraestructura y arquitectura
    "base de datos",
    "database",
    "SQL",
    "NoSQL",
    "API",
    "REST",
    "GraphQL",
    "microservicio",
    "microservices",
    "servidor",
    "server",
    "frontend",
    "backend",
    "framework",
    "librería",
    "library",
    "cloud",
    "nube",
    "docker",
    "kubernetes",
    "contenedor",
    "container",
    "repositorio",
    "repository",
    # Conceptos de desarrollo
    "endpoint",
    "payload",
    "token",
    "JWT",
    "OAuth",
    "autenticación",
    "authentication",
    "middleware",
    "deploy",
    "despliegue",
    "pipeline",
    "CI/CD",
    "DevOps",
    "compilar",
    "compile",
    "runtime",
    "caché",
    "cache",
    "log",
    "logging",
    # Lenguajes y plataformas
    "Python",
    "JavaScript",
    "TypeScript",
    "React",
    "Next.js",
    "FastAPI",
    "PostgreSQL",
    "MongoDB",
    "Redis",
]
