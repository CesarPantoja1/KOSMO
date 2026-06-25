from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, cast

from kosmo.contracts.llm.ports import LLMClient, PromptTemplate
from kosmo.contracts.pipeline.phase_outputs import SuggestedFeature, SuggestFeaturesOutput
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository, FeatureRepository


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
    """Caso de uso: sugiere características adicionales que no dupliquen las existentes.

    Invoca al LLM para generar 3 sugerencias de características basadas en
    el documento de descubrimiento, evitando duplicar las que ya existen.
    """

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

        discovery_doc = await self._document_repo.get_discovery(input_data.project_id)
        if discovery_doc is None:
            raise DocumentNotFoundError(
                document_type="discovery",
                instance=f"/api/v1/projects/{input_data.project_id}/features/suggest",
            )

        existing_features = await self._feature_repo.list_by_project(input_data.project_id)
        existing_titles = [f.title for f in existing_features]
        next_number = len(existing_features) + 1

        suggest_prompt = (
            "Eres un diseñador de producto experto.\n"
            "A continuación se presenta un Documento de Descubrimiento y una lista de\n"
            "características ya existentes. Tu tarea es sugerir EXACTAMENTE 3 nuevas\n"
            "características que NO dupliquen las ya existentes.\n\n"
            "Respondé ÚNICAMENTE con JSON:\n"
            "```json\n"
            '{"suggestions": [\n'
            '  {"title": "...", "description": "...", "rationale": "...",\n'
            '   "inferred_from": ["..."]}\n'
            "]}\n"
            "```\n\n"
        )

        from kosmo.domain.sdd.document_converters import document_to_markdown

        suggest_prompt += "## Documento de Descubrimiento\n\n"
        suggest_prompt += document_to_markdown(discovery_doc)

        if existing_titles:
            titles = ", ".join(existing_titles)
            suggest_prompt += f"\n\n## Características ya existentes (NO duplicar)\n\n{titles}"

        suggest_prompt += (
            f"\n\nLa primera sugerencia será C{next_number:02d}."
            f"\nGenerá exactamente 3 sugerencias. "
            "Nada de texto antes o después del JSON."
        )

        llm_response = await self._llm_client.complete(
            prompt=PromptTemplate(
                system_prompt=suggest_prompt,
                user_prompt="Generá 3 sugerencias de características.",
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
            title = str(item.get("title", f"Característica {number}"))
            inferred_from_raw = item.get("inferred_from", [])
            inferred_from: list[str] = (
                [str(x) for x in inferred_from_raw]  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
                if isinstance(inferred_from_raw, list)
                else []
            )
            suggestions.append(
                SuggestedFeature(
                    number=number,
                    title=title,
                    description=str(item.get("description", "")),
                    rationale=str(item.get("rationale", "")),
                    inferred_from=inferred_from,
                )
            )

        return suggestions


class SaveSelectedFeaturesUseCase:
    """Caso de uso: guarda las características seleccionadas por el usuario.

    Persiste las características que el usuario seleccionó desde las sugerencias
    de la IA o desde la creación manual, asignándoles proyecto y numeración.
    """

    def __init__(self, feature_repo: FeatureRepository) -> None:
        self._feature_repo = feature_repo

    async def execute(self, input_data: SaveSelectedFeaturesInput) -> SaveSelectedFeaturesOutput:
        from kosmo.contracts.sdd.ids import FeatureId
        from kosmo.domain.sdd.id_generator import IdGenerator

        existing = await self._feature_repo.list_by_project(input_data.project_id)
        next_num = max((f.number for f in existing), default=0) + 1

        features: list[Feature] = []
        for item in input_data.features:
            title = str(item.get("title", f"Característica {next_num}"))
            inferred_raw = cast("list[Any]", item.get("inferred_from", []))
            inferred: list[str] = [str(x) for x in inferred_raw] if inferred_raw else []
            features.append(
                Feature(
                    id=FeatureId(IdGenerator.generate("feature")),
                    project_id=input_data.project_id,
                    number=next_num,
                    title=title,
                    slug=title.lower().replace(" ", "-"),
                    description=str(item.get("description", "")),
                    rationale=str(item.get("rationale", "")),
                    inferred_from=inferred,
                )
            )
            next_num += 1

        saved = await self._feature_repo.save_many(features)

        return SaveSelectedFeaturesOutput(
            project_id=input_data.project_id,
            features=saved,
        )
