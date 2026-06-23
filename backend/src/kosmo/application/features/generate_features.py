from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from kosmo.contracts.llm.ports import LLMClient, PromptTemplate
from kosmo.contracts.pipeline.phase_contexts import FeaturesPhaseContext
from kosmo.contracts.pipeline.phase_outputs import (
    FeaturesPhaseOutput,
    GenerationMetadata,
)
from kosmo.contracts.sdd.errors import LLMInvocationError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import (
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
)
from kosmo.domain.pipeline.phase_modes.features_mode import FeaturesMode


@dataclass(frozen=True)
class GenerateFeaturesInput:
    project_id: ProjectId


@dataclass(frozen=True)
class GenerateFeaturesOutput:
    project_id: ProjectId
    features: list[Feature]
    phase_output: FeaturesPhaseOutput


class GenerateFeaturesUseCase:
    """Caso de uso: genera las características del producto software mediante IA.

    Orquesta la generación de características:
    1. Verifica que el proyecto existe.
    2. Obtiene el documento de descubrimiento.
    3. Construye el contexto de fase.
    4. Delega al LLM la generación de características usando FeaturesMode.
    5. Valida la estructura y unicidad de las características generadas.
    6. Persiste las características resultantes en el FeatureRepository.
    7. Gestiona los fallos del servicio de IA.
    """

    def __init__(
        self,
        project_repo: ProjectRepository,
        document_repo: DocumentRepository,
        feature_repo: FeatureRepository,
        llm_client: LLMClient,
    ) -> None:
        self._project_repo = project_repo
        self._document_repo = document_repo
        self._feature_repo = feature_repo
        self._llm_client = llm_client

    async def execute(
        self, input_data: GenerateFeaturesInput
    ) -> GenerateFeaturesOutput:
        from kosmo.contracts.sdd.errors import (
            DocumentNotFoundError,
            ProjectNotFoundError,
        )

        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}/features",
            )

        discovery_doc = await self._document_repo.get_discovery(
            input_data.project_id
        )
        if discovery_doc is None:
            raise DocumentNotFoundError(
                document_type="discovery",
                instance=f"/api/v1/projects/{input_data.project_id}/features",
            )

        existing_features = await self._feature_repo.list_by_project(
            input_data.project_id
        )
        existing_titles = [f.title for f in existing_features]

        mode = FeaturesMode()
        context = FeaturesPhaseContext(
            discovery_document=discovery_doc,
            existing_feature_titles=existing_titles,
        )

        system_prompt = mode.system_prompt
        user_prompt = mode.build_user_prompt(context)

        max_retries = 2
        last_errors: list[str] = []

        try:
            for attempt in range(max_retries + 1):
                llm_response = await self._llm_client.complete(
                    prompt=PromptTemplate(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                    ),
                    temperature=0.2,
                    max_tokens=4096,
                )

                generated_content = self._parse_llm_response(llm_response.text)
                validation = mode.validate_output(generated_content)

                if validation.is_valid:
                    features_data = self._extract_features_list(generated_content)
                    features = self._build_features(
                        features_data, input_data.project_id, existing_features
                    )

                    saved_features = await self._feature_repo.save_many(features)

                    metadata = GenerationMetadata(
                        llm_calls=attempt + 1,
                        total_tokens=llm_response.usage.total_tokens,
                        retry_count=attempt,
                        model_used=llm_response.model,
                    )

                    return GenerateFeaturesOutput(
                        project_id=input_data.project_id,
                        features=saved_features,
                        phase_output=FeaturesPhaseOutput(
                            features=saved_features,
                            validation_result=validation,
                            generation_metadata=metadata,
                        ),
                    )

                last_errors = validation.errors
                user_prompt = mode.build_retry_prompt(
                    user_prompt, last_errors, attempt + 1
                )

            raise LLMInvocationError(
                detail=(
                    f"No se pudieron generar características válidas después de "
                    f"{max_retries + 1} intentos: {'; '.join(last_errors)}"
                ),
                instance=f"/api/v1/projects/{input_data.project_id}/features",
            )

        except LLMInvocationError:
            raise
        except Exception as exc:
            raise LLMInvocationError(
                detail=f"Error al generar características: {exc}",
                instance=f"/api/v1/projects/{input_data.project_id}/features",
            ) from exc

    @staticmethod
    def _parse_llm_response(text: str) -> Any:
        try:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            if "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            return json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            return {"raw_text": text}

    @staticmethod
    def _extract_features_list(content: Any) -> list[dict[str, Any]]:  # pyright: ignore[reportExplicitAny]
        if isinstance(content, dict):
            raw: object = content.get("features", [])  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            if isinstance(raw, list):
                return raw  # type: ignore[reportReturnType]
        if isinstance(content, list):
            return content  # type: ignore[reportReturnType]
        return []

    @staticmethod
    def _build_features(
        features_data: list[dict[str, Any]],  # pyright: ignore[reportExplicitAny]
        project_id: ProjectId,
        existing: list[Feature],
    ) -> list[Feature]:
        from kosmo.contracts.sdd.ids import FeatureId
        from kosmo.domain.sdd.id_generator import IdGenerator

        features: list[Feature] = []
        next_num = max((f.number for f in existing), default=0) + 1

        for item in features_data:
            features.append(
                Feature(
                    id=FeatureId(IdGenerator.generate("feature")),
                    project_id=project_id,
                    number=int(item.get("number", next_num)),
                    title=str(item.get("title", f"Característica {next_num}")),
                    slug=str(item.get("slug", "")),
                    description=str(item.get("description", "")),
                    rationale=str(item.get("rationale", "")),
                    inferred_from=(
                        item.get("inferred_from", [])
                        if isinstance(item.get("inferred_from"), list)
                        else []
                    ),
                )
            )
            next_num += 1

        return features
