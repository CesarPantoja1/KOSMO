from __future__ import annotations

import json
import re
from dataclasses import dataclass

from kosmo.contracts.llm.ports import LLMClient, PromptTemplate
from kosmo.contracts.pipeline.phase_outputs import SuggestedFeature, SuggestFeaturesOutput
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.guardrails import DISCOVERY_SECTIONS
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository, FeatureRepository
from kosmo.domain.sdd.document_converters import slugify_spanish
from kosmo.domain.sdd.id_generator import IdGenerator

_FEATURE_ID_PREFIX = re.compile(r"^\s*C\d+[\s:.–—-]+")

_SUGGEST_FEATURES_SYSTEM_PROMPT = (
    "Eres un diseñador de producto experto.\n"
    "Las Características operan a nivel de usuario: cada característica expresa "
    "lo que el usuario desea lograr, no lo que el software hace. En este nivel "
    "no existe todavía un sistema ni una aplicación.\n\n"
    "Genera sugerencias de características con EXACTAMENTE tres campos:\n\n"
    "### 1. Título\n"
    "Máximo seis palabras que expresan la intención de interacción del usuario "
    "con el futuro producto. Se redacta como una acción que el usuario desea "
    "realizar. Evita nomenclatura de software y terminología de negocio abstracta.\n\n"
    "### 2. Descripción\n"
    "Párrafo de una a dos oraciones que describe cómo el usuario interactuaría "
    "con el producto para lograr el propósito del título. Se construye desde "
    "la perspectiva del usuario, sin mencionar componentes de software, "
    "mecanismos técnicos ni conceptos de negocio abstractos.\n\n"
    "### 3. Origen\n"
    "Unifica la justificación de existencia de la característica y las secciones "
    "del Descubrimiento de las cuales se deriva. Explica en una a dos oraciones "
    "por qué resulta esencial y enumera las secciones del Descubrimiento que la "
    "fundamentan.\n\n"
    "Secciones válidas del Descubrimiento para trazabilidad:\n"
    + "\n".join(f"- {s}" for s in DISCOVERY_SECTIONS)
    + "\n\n"
    "REGLAS CRÍTICAS DE CALIDAD:\n"
    "1. NIVEL DE USUARIO: Las características expresan lo que el usuario desea "
    "lograr, no lo que el software hace. PROHIBIDO: API, base de datos, "
    "microservicios, endpoints, servidores, lenguajes, frameworks, protocolos, "
    "arquitectura, deployment, Docker, cloud, SQL, HTTP, REST, GraphQL, backend, "
    "frontend, cache, Redis, MongoDB, PostgreSQL, Kubernetes, AWS, GCP, Azure, "
    "plataforma, sistema, software, web, aplicación, aplicaciones.\n"
    "2. SIN TERMINOLOGÍA DE NEGOCIO ABSTRACTA: PROHIBIDO usar términos como: "
    "propuesta de valor, modelo de negocio, ventaja competitiva, diferenciador, "
    "monetización, ROI, KPI, stakeholder, oportunidad de mercado, segmento de "
    "mercado, caso de negocio, estrategia comercial. El origin puede mencionar "
    "nombres de secciones del Descubrimiento, pero el título y la descripción "
    "no deben contenerlos.\n"
    "3. NO DUPLICADOS: Las sugerencias generadas deben ser distintas entre sí "
    "y no presentar solapamiento o redundancia semántica. Tampoco deben duplicar "
    "las características ya existentes listadas en el prompt del usuario.\n"
    "4. TÍTULO MÁXIMO SEIS PALABRAS: El título no puede exceder seis palabras.\n"
    "5. TRAZABILIDAD: El campo origin debe mencionar al menos una sección del "
    "Descubrimiento de la lista anterior.\n"
    "6. IDIOMA: Todo el contenido debe estar en español con acentuación y "
    "ortografía correctas.\n"
    "7. CANTIDAD: Genera EXACTAMENTE 3 sugerencias. "
    "Nada de texto antes o después del JSON.\n\n"
    "FORMATO DE SALIDA:\n"
    "Debes responder ÚNICAMENTE con un objeto JSON válido con la siguiente "
    "estructura, sin texto de introducción ni de conclusión:\n"
    "```json\n"
    "{\n"
    '  "suggestions": [\n'
    "    {\n"
    '      "title": "Registrar gastos entre participantes",\n'
    '      "description": "Cualquier participante del grupo indica el monto de "\n'
    '        "un gasto, selecciona a las personas involucradas.",\n'
    '      "origin": "Se deriva de la meta Gestión financiera de gastos. "\n'
    '        "Se traza a Metas del producto, Actores y Reglas de negocio."\n'
    "    }\n"
    "  ]\n"
    "}\n"
    "```"
)


def _strip_feature_id_prefix(title: str) -> str:
    return _FEATURE_ID_PREFIX.sub("", title).strip()


@dataclass(frozen=True)
class SuggestFeaturesInput:
    project_id: ProjectId


@dataclass(frozen=True)
class SaveSelectedFeaturesInput:
    project_id: ProjectId
    features: list[dict[str, object]]


@dataclass(frozen=True)
class SaveSelectedFeaturesOutput:
    project_id: ProjectId
    features: list[Feature]


class SuggestFeaturesUseCase:
    def __init__(
        self,
        document_repo: DocumentRepository,
        feature_repo: FeatureRepository,
        llm_client: LLMClient,
    ) -> None:
        self._document_repo = document_repo
        self._feature_repo = feature_repo
        self._llm_client = llm_client

    async def execute(self, input_data: SuggestFeaturesInput) -> SuggestFeaturesOutput:
        from kosmo.contracts.sdd.errors import DocumentNotFoundError
        from kosmo.domain.sdd.document_converters import document_to_markdown

        discovery_doc = await self._document_repo.get_discovery(input_data.project_id)
        if discovery_doc is None:
            raise DocumentNotFoundError(
                document_type="discovery",
                instance=f"/api/v1/projects/{input_data.project_id}/features/suggest",
            )

        existing_features = await self._feature_repo.list_by_project(input_data.project_id)
        existing_titles = [f.title for f in existing_features]
        next_number = len(existing_features) + 1

        user_prompt_parts = [
            "## Documento de Descubrimiento\n\n",
            document_to_markdown(discovery_doc),
        ]

        if existing_titles:
            existing_list = "\n".join(f"- {title}" for title in existing_titles)
            user_prompt_parts.append(
                f"\n## Características Existentes (NO DUPLICAR NI REPETIR ESTAS CARACTERÍSTICAS):\n\n{existing_list}"
            )

        user_prompt = "\n".join(user_prompt_parts)

        llm_response = await self._llm_client.complete(
            prompt=PromptTemplate(
                system_prompt=_SUGGEST_FEATURES_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            ),
            temperature=0.4,
        )

        suggestions_data = self._parse_llm_response(llm_response.text)
        suggestions = self._parse_suggestions(suggestions_data, next_number)

        return SuggestFeaturesOutput(
            suggestions=suggestions,
            excluded_titles=existing_titles,
            domain_inferred=(discovery_doc.sections[0].text if discovery_doc.sections else ""),
        )

    @staticmethod
    def _parse_llm_response(text: str) -> object:
        try:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            if "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            return json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            return {"suggestions": []}

    @staticmethod
    def _parse_suggestions(data: object, next_number: int) -> list[SuggestedFeature]:
        suggestions: list[SuggestedFeature] = []
        items: list[object] = []

        if isinstance(data, dict) and "suggestions" in data:
            raw_suggestions: object = data["suggestions"]  # pyright: ignore[reportUnknownVariableType]
            if isinstance(raw_suggestions, list):
                items = raw_suggestions  # pyright: ignore[reportUnknownVariableType]
        elif isinstance(data, list):
            items = data  # pyright: ignore[reportUnknownVariableType]

        for i, item_ in enumerate(items[:3]):
            if not isinstance(item_, dict):
                continue
            item: dict[str, object] = item_  # type: ignore[reportUnknownVariableType]
            number = next_number + i
            title = _strip_feature_id_prefix(str(item.get("title", f"Característica {number}")))
            suggestions.append(
                SuggestedFeature(
                    number=number,
                    title=title,
                    description=str(item.get("description", "")),
                    origin=str(item.get("origin", "")),
                )
            )

        return suggestions


class SaveSelectedFeaturesUseCase:
    def __init__(self, feature_repo: FeatureRepository) -> None:
        self._feature_repo = feature_repo

    async def execute(self, input_data: SaveSelectedFeaturesInput) -> SaveSelectedFeaturesOutput:

        existing = await self._feature_repo.list_by_project(input_data.project_id)
        next_num = max((f.number for f in existing), default=0) + 1

        features: list[Feature] = []
        for item in input_data.features:
            title = _strip_feature_id_prefix(str(item.get("title", f"Característica {next_num}")))
            features.append(
                Feature(
                    id=FeatureId(IdGenerator.generate("feature")),
                    project_id=input_data.project_id,
                    number=next_num,
                    title=title,
                    slug=slugify_spanish(title) or f"feature-{next_num}",
                    description=str(item.get("description", "")),
                    origin=str(item.get("origin", "")),
                )
            )
            next_num += 1

        saved = await self._feature_repo.save_many(features)

        return SaveSelectedFeaturesOutput(
            project_id=input_data.project_id,
            features=saved,
        )
