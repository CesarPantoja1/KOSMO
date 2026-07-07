from __future__ import annotations

from dataclasses import dataclass

from kosmo.application.features.save_features import (
    SuggestFeaturesInput,
    SuggestFeaturesUseCase,
)
from kosmo.contracts.pipeline.phase_outputs import SuggestedFeature
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository
from kosmo.domain.sdd.id_generator import IdGenerator


@dataclass(frozen=True)
class CreateCharacteristicInput:
    project_id: ProjectId
    title: str
    description: str


@dataclass(frozen=True)
class CreateCharacteristicOutput:
    characteristic: Feature
    suggestions: list[SuggestedFeature]


class CreateCharacteristicUseCase:
    """Caso de uso: crea una caracteristica de producto de forma manual.

    Orquesta la creacion:
    1. Valida que el titulo no este vacio y no exceda 50 caracteres.
    2. Valida que la descripcion no exceda 500 caracteres.
    3. Obtiene el siguiente numero secuencial para el proyecto.
    4. Crea la entidad Feature con slug y display_id generados.
    5. Persiste la caracteristica en el repositorio.
    6. Orquesta la generacion de sugerencias con IA.
    """

    def __init__(
        self,
        feature_repo: FeatureRepository,
        suggest_use_case: SuggestFeaturesUseCase,
    ) -> None:
        self._feature_repo = feature_repo
        self._suggest_use_case = suggest_use_case

    async def execute(self, input_data: CreateCharacteristicInput) -> CreateCharacteristicOutput:
        if not input_data.title.strip():
            raise ValueError("El titulo de la caracteristica no puede estar vacio")

        if len(input_data.title) > 50:
            raise ValueError(
                f"El titulo de la caracteristica no puede exceder los 50 caracteres (actual: {len(input_data.title)})"
            )

        if len(input_data.description) > 500:
            raise ValueError(
                f"La descripcion de la caracteristica no puede exceder los 500 caracteres "
                f"(actual: {len(input_data.description)})"
            )

        next_number = await self._feature_repo.next_number(input_data.project_id)

        feature = Feature(
            id=FeatureId(IdGenerator.generate("feature")),
            project_id=input_data.project_id,
            number=next_number,
            title=input_data.title.strip(),
            slug=input_data.title.strip().lower().replace(" ", "-"),
            description=input_data.description,
        )

        saved = await self._feature_repo.save(feature)

        suggest_input = SuggestFeaturesInput(project_id=input_data.project_id)
        suggest_output = await self._suggest_use_case.execute(suggest_input)

        return CreateCharacteristicOutput(
            characteristic=saved,
            suggestions=suggest_output.suggestions,
        )
