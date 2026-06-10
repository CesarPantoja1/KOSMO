from pydantic import BaseModel, Field


class GuardrailViolation(BaseModel):
    field: str
    message: str
    severity: str = Field(description="'blocker' o 'warning'")

    @property
    def is_blocker(self) -> bool:
        return self.severity == "blocker"


class GuardrailResult(BaseModel):
    is_valid: bool
    violations: list[GuardrailViolation] = Field(default_factory=list)
    sanitized: dict | list | None = None
    summary: str = ""


PROHIBITED_TERMS: set[str] = {
    "api",
    "endpoint",
    "rest",
    "graphql",
    "websocket",
    "http",
    "json",
    "xml",
    "base de datos",
    "tabla",
    "columna",
    "indice",
    "sql",
    "nosql",
    "postgresql",
    "mongodb",
    "redis",
    "servidor",
    "contenedor",
    "pod",
    "cluster",
    "load balancer",
    "cdn",
    "cloud",
    "aws",
    "azure",
    "gcp",
    "frontend",
    "backend",
    "componente",
    "modulo",
    "clase",
    "metodo",
    "funcion",
    "controlador",
    "middleware",
    "framework",
    "libreria",
    "react",
    "angular",
    "vue",
    "django",
    "flask",
    "spring",
    "express",
    "node",
    "python",
    "java",
    "typescript",
    "javascript",
    "microservicio",
    "orm",
    "docker",
    "kubernetes",
    "ci/cd",
    "cache",
    "jwt",
    "oauth",
    "token de acceso",
    "apikey",
}


DISCOVERY_SECTIONS: list[str] = [
    "vision",
    "problem_space",
    "actors",
    "value_proposition",
    "use_cases",
    "core_capabilities",
    "business_rules",
    "quality_attributes",
    "scope",
]

MIN_SECTION_LENGTH: int = 50
