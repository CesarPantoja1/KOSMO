class SpecError(Exception):
    pass


class SpecNotFoundError(SpecError):
    def __init__(self, spec_id: str) -> None:
        super().__init__(f"Especificación no encontrada: {spec_id}")


class ProjectNotFoundError(SpecError):
    def __init__(self, project_id: str) -> None:
        super().__init__(f"Proyecto no encontrado: {project_id}")


class PhaseTransitionError(SpecError):
    def __init__(self, spec_id: str, current: str, target: str) -> None:
        super().__init__(f"No se puede avanzar de fase {current} a {target} para el spec {spec_id}")


class ValidationError(SpecError):
    def __init__(self, artifact: str, findings: list[str]) -> None:
        detail = "; ".join(findings)
        super().__init__(f"Validación fallida en {artifact}: {detail}")


class EARSValidationError(ValidationError):
    pass


class DomainModelValidationError(ValidationError):
    pass


class TaskGraphValidationError(ValidationError):
    pass


class LLMInvocationError(SpecError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Error de invocación LLM: {detail}")


class ApiKeyError(Exception):
    def __init__(self, provider: str, detail: str) -> None:
        super().__init__(f"Error de API key ({provider}): {detail}")


class InvalidApiKeyError(ApiKeyError):
    pass


class ApiKeyNotFoundError(ApiKeyError):
    def __init__(self, key_id: str) -> None:
        super().__init__(key_id, "Clave no encontrada")


class ConstitutionError(SpecError):
    pass


class FeatureNotApprovedError(SpecError):
    def __init__(self, feature_id: str) -> None:
        super().__init__(
            f"La caracteristica {feature_id} debe estar Aprobada para generar requisitos"
        )


class FeatureNotEditableError(SpecError):
    def __init__(self, feature_id: str, current_status: str) -> None:
        super().__init__(
            f"La caracteristica {feature_id} esta en estado {current_status}. "
            "Solo se pueden editar caracteristicas en estado Borrador."
        )


class FeatureNotFoundError(SpecError):
    def __init__(self, feature_id: str) -> None:
        super().__init__(f"Característica no encontrada: {feature_id}")


class FeatureOperationError(SpecError):
    pass


class ProjectAlreadyExistsError(SpecError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Ya existe un proyecto con el nombre: {name}")


class DocumentValidationError(SpecError):
    def __init__(self, findings: list[str]) -> None:
        detail = "; ".join(findings)
        super().__init__(f"Documento inválido: {detail}")


class DocumentNotFoundError(SpecError):
    def __init__(self, resource_type: str, resource_id: str) -> None:
        super().__init__(f"Documento no encontrado para {resource_type} {resource_id}")


class MarkdownParseError(SpecError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Error al parsear Markdown: {detail}")
