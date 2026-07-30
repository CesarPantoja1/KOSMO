from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from kosmo.contracts.llm.ports import LLMClient, PromptTemplate
from kosmo.contracts.sdd.document import SpecPhase


class PhaseClassification(BaseModel):
    belongs_to_current_phase: bool = Field(description="True si el mensaje corresponde al ámbito de la fase actual")
    target_phase: str = Field(
        default="",
        description="Fase a la que pertenece el mensaje: discovery, features, requirements",
    )
    message: str = Field(
        default="",
        description="Mensaje de redirección en español indicando la fase correcta",
    )


_PHASE_CLASSIFICATION_PROMPT = (
    "Eres un clasificador de intención para la plataforma KOSMO.\n"
    "Tu única tarea es determinar a qué fase del proceso de especificación pertenece "
    "el mensaje del usuario.\n\n"
    "FASES DISPONIBLES:\n\n"
    "1. Descubrimiento (discovery):\n"
    "   - Visión del negocio, problema, actores, propuesta de valor, metas del producto.\n"
    "   - Reglas de negocio, alcance del producto (incluido/excluido).\n"
    "   - Estrategia comercial, modelo de negocio, diferenciadores.\n"
    "   - Palabras clave: visión, negocio, mercado, propuesta de valor, alcance, actores, "
    "reglas de negocio, metas, problema.\n\n"
    "2. Características (features):\n"
    "   - Lo que el usuario desea lograr con el producto (funcionalidades a nivel de usuario).\n"
    "   - Título, descripción de características, acciones que el usuario quiere realizar.\n"
    "   - NO incluye detalles técnicos, APIs, bases de datos ni requisitos de software.\n"
    "   - Palabras clave: característica, funcionalidad, título, descripción, origen, "
    "acción de usuario, C01, C02.\n\n"
    "3. Requisitos (requirements):\n"
    "   - Requisitos de software, criterios de aceptación, casos de prueba.\n"
    "   - Formato EARS (Dado-Cuando-Entonces / Given-When-Then).\n"
    "   - Comportamiento del sistema, validaciones, restricciones técnicas.\n"
    "   - Palabras clave: requisito, criterio de aceptación, Dado-Cuando-Entonces, "
    "EARS, validación, REQ, especificación técnica.\n\n"
    "FORMATO DE SALIDA (JSON):\n"
    "{\n"
    '  "belongs_to_current_phase": true | false,\n'
    '  "target_phase": "discovery" | "features" | "requirements" | "",\n'
    '  "message": "Mensaje de redirección en español o cadena vacía si es válido"\n'
    "}\n\n"
    "REGLAS:\n"
    "- Si el mensaje NO corresponde a la fase actual, target_phase debe contener "
    "la fase correcta y message un texto como: 'Este cambio pertenece a la fase de "
    "Descubrimiento. Ve a esa fase para realizarlo.'\n"
    "- Si el mensaje ES ambiguo o consultivo (ej. '¿qué es una característica?', "
    "'ayúdame a entender'), considéralo como válido para la fase actual.\n"
    "- Si el mensaje ES claramente de la fase actual, target_phase y message van vacíos."
)


@dataclass(frozen=True)
class ValidatePhaseContextInput:
    content: str
    current_phase: SpecPhase


@dataclass(frozen=True)
class ValidatePhaseContextOutput:
    is_valid: bool
    redirect_message: str | None = None
    target_phase: str | None = None


class ValidatePhaseContextUseCase:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def execute(self, input_data: ValidatePhaseContextInput) -> ValidatePhaseContextOutput:
        content = input_data.content.strip()
        if not content:
            return ValidatePhaseContextOutput(is_valid=True)

        phase_name = input_data.current_phase.value

        user_prompt = f"Fase actual: {phase_name}\n\nMensaje del usuario a clasificar:\n{content}"

        try:
            result = await self._llm_client.complete_typed(
                prompt=PromptTemplate(
                    system_prompt=_PHASE_CLASSIFICATION_PROMPT,
                    user_prompt=user_prompt,
                ),
                output_type=PhaseClassification,
                temperature=0.1,
                max_tokens=256,
            )
        except Exception:
            return ValidatePhaseContextOutput(is_valid=True)

        normalized_target = _normalize_phase(result.target_phase)
        normalized_current = _normalize_phase(phase_name)

        is_valid = result.belongs_to_current_phase and (
            not normalized_target or normalized_target == normalized_current
        )

        if is_valid:
            return ValidatePhaseContextOutput(is_valid=True)

        return ValidatePhaseContextOutput(
            is_valid=False,
            redirect_message=result.message or self._default_redirect(normalized_target),
            target_phase=normalized_target or None,
        )

    @staticmethod
    def _default_redirect(target_phase: str) -> str:
        phase_labels: dict[str, str] = {
            "discovery": "Descubrimiento",
            "features": "Características",
            "requirements": "Requisitos",
        }
        label = phase_labels.get(target_phase, target_phase)
        return f"Este cambio pertenece a la fase de {label}. Ve a esa fase para realizarlo."


def _normalize_phase(phase: str) -> str:
    if not phase:
        return ""
    phase = phase.strip().lower()
    mapping: dict[str, str] = {
        "discovery": "descubrimiento",
        "features": "caracteristicas",
        "requirements": "requisitos",
        "model": "modelo",
    }
    return mapping.get(phase, phase)
