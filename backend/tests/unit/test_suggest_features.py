from dataclasses import dataclass
from typing import Any

import pytest

from kosmo.application.features.save_features import (
    SuggestFeaturesInput,
    SuggestFeaturesOutput,
    SuggestFeaturesUseCase,
)
from kosmo.contracts.llm.ports import LLMResponse, LLMUsage, PromptTemplate
from kosmo.contracts.sdd.document import DocumentNode, RichTextDocument, SectionHeading
from kosmo.contracts.sdd.errors import DocumentNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.documents: dict[str, RichTextDocument] = {}

    async def get_discovery(self, project_id: ProjectId) -> RichTextDocument | None:
        return self.documents.get(str(project_id))

    async def save_discovery(self, project_id: ProjectId, document: RichTextDocument) -> RichTextDocument:
        self.documents[str(project_id)] = document
        return document

    async def get_requirements(self, feature_id: Any) -> RichTextDocument | None:  # noqa: ARG002
        return None

    async def save_requirements(
        self,
        feature_id: Any,  # noqa: ARG002
        document: RichTextDocument,  # noqa: ARG002
    ) -> RichTextDocument:
        return document


class InMemoryFeatureRepository:
    def __init__(self) -> None:
        self.features: dict[str, Feature] = {}

    async def by_id(self, feature_id: FeatureId) -> Feature | None:
        return self.features.get(str(feature_id))

    async def list_by_project(self, project_id: ProjectId) -> list[Feature]:
        return [f for f in self.features.values() if str(f.project_id) == str(project_id)]

    async def save(self, feature: Feature) -> Feature:  # type: ignore[override]
        self.features[str(feature.id)] = feature
        return feature

    async def save_many(self, features: list[Feature]) -> list[Feature]:
        for f in features:
            self.features[str(f.id)] = f
        return features

    async def next_number(self, project_id: ProjectId) -> int:  # noqa: ARG002
        return 1


@dataclass
class MockLLMClient:
    response: LLMResponse

    async def complete(self, prompt: PromptTemplate, **kwargs: Any) -> LLMResponse:  # noqa: ARG002
        return self.response


def _make_discovery_document() -> RichTextDocument:
    return RichTextDocument(
        nodes=[
            DocumentNode(
                type="heading",
                heading=SectionHeading(text="Sistema de Gestión", level=2, slug="sistema-gestion"),
                content="Contenido del discovery",
            ),
        ]
    )


@pytest.mark.asyncio
async def test_suggest_features_raises_when_discovery_not_found() -> None:
    # Arrange
    doc_repo: Any = InMemoryDocumentRepository()
    feat_repo: Any = InMemoryFeatureRepository()
    llm_client: Any = MockLLMClient(response=LLMResponse(text="{}", usage=LLMUsage(total_tokens=0), model="mock"))
    use_case = SuggestFeaturesUseCase(
        document_repo=doc_repo,
        feature_repo=feat_repo,
        llm_client=llm_client,
    )

    # Act & Assert
    with pytest.raises(DocumentNotFoundError) as exc_info:
        await use_case.execute(SuggestFeaturesInput(project_id=ProjectId("prj_no_discovery")))

    assert "discovery" in str(exc_info.value.problem.detail)
    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
async def test_suggest_features_returns_suggestions_from_llm() -> None:
    # Arrange
    doc_repo: Any = InMemoryDocumentRepository()
    feat_repo: Any = InMemoryFeatureRepository()
    project_id = ProjectId("prj_suggest123")

    await doc_repo.save_discovery(project_id, _make_discovery_document())

    llm_json = """{
        "suggestions": [
            {
                "title": "Registrar gastos entre participantes",
                "description": "Cualquier participante indica el monto de un gasto compartido.",
                "origin": "Se deriva de la meta Gestion financiera. Se traza a Metas del producto."
            },
            {
                "title": "Consultar balances y deudas",
                "description": "Cualquier participante accede a un resumen de sus deudas.",
                "origin": "Se deriva de la meta Gestion financiera. Se traza a Metas del producto."
            },
            {
                "title": "Liquidar deudas del grupo",
                "description": "El administrador visualiza un plan de transferencias optimizado.",
                "origin": "Se deriva de la meta Gestion financiera. Se traza a Metas del producto."
            }
        ]
    }"""
    llm_client: Any = MockLLMClient(response=LLMResponse(text=llm_json, usage=LLMUsage(total_tokens=100), model="mock"))
    use_case = SuggestFeaturesUseCase(
        document_repo=doc_repo,
        feature_repo=feat_repo,
        llm_client=llm_client,
    )

    # Act
    result = await use_case.execute(SuggestFeaturesInput(project_id=project_id))

    # Assert
    assert isinstance(result, SuggestFeaturesOutput)
    assert len(result.suggestions) == 3
    assert result.suggestions[0].title == "Registrar gastos entre participantes"
    assert result.suggestions[0].number == 1
    assert result.suggestions[1].title == "Consultar balances y deudas"
    assert result.suggestions[2].title == "Liquidar deudas del grupo"


@pytest.mark.asyncio
async def test_suggest_features_excludes_existing_titles() -> None:
    # Arrange
    doc_repo: Any = InMemoryDocumentRepository()
    feat_repo: Any = InMemoryFeatureRepository()
    project_id = ProjectId("prj_existing456")

    await doc_repo.save_discovery(project_id, _make_discovery_document())

    existing = Feature(
        id=FeatureId("feat_exist123"),
        number=1,
        title="Registrar gastos entre participantes",
        slug="registrar-gastos-entre-participantes",
        description="Registro existente de gastos",
        project_id=project_id,
    )
    await feat_repo.save(existing)

    llm_json = """{
        "suggestions": [
            {
                "title": "Nueva Feature",
                "description": "Descripción de la nueva característica",
                "origin": "Se traza a Metas del producto."
            }
        ]
    }"""
    llm_client: Any = MockLLMClient(response=LLMResponse(text=llm_json, usage=LLMUsage(total_tokens=100), model="mock"))
    use_case = SuggestFeaturesUseCase(
        document_repo=doc_repo,
        feature_repo=feat_repo,
        llm_client=llm_client,
    )

    # Act
    result = await use_case.execute(SuggestFeaturesInput(project_id=project_id))

    # Assert
    assert "Registrar gastos entre participantes" in result.excluded_titles
    assert result.suggestions[0].number == 2


@pytest.mark.asyncio
async def test_suggest_features_strips_identifier_prefix_from_title() -> None:
    # Arrange
    doc_repo: Any = InMemoryDocumentRepository()
    feat_repo: Any = InMemoryFeatureRepository()
    project_id = ProjectId("prj_strip123")

    await doc_repo.save_discovery(project_id, _make_discovery_document())

    llm_json = """{
        "suggestions": [
            {
                "title": "C01 Registrar gastos entre participantes",
                "description": "Descripcion del registro de gastos",
                "origin": "Se traza a Metas del producto."
            },
            {
                "title": "C02: Consultar balances y deudas",
                "description": "Consulta de balances del grupo",
                "origin": "Se traza a Metas del producto."
            },
            {
                "title": "C03 - Liquidar deudas del grupo",
                "description": "Liquidacion de deudas pendientes",
                "origin": "Se traza a Metas del producto."
            }
        ]
    }"""
    llm_client: Any = MockLLMClient(response=LLMResponse(text=llm_json, usage=LLMUsage(total_tokens=100), model="mock"))
    use_case = SuggestFeaturesUseCase(
        document_repo=doc_repo,
        feature_repo=feat_repo,
        llm_client=llm_client,
    )

    # Act
    result = await use_case.execute(SuggestFeaturesInput(project_id=project_id))

    # Assert
    assert result.suggestions[0].title == "Registrar gastos entre participantes"
    assert result.suggestions[1].title == "Consultar balances y deudas"
    assert result.suggestions[2].title == "Liquidar deudas del grupo"
