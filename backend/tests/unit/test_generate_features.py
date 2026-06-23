import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.features.generate_features import (
    GenerateFeaturesInput,
    GenerateFeaturesOutput,
    GenerateFeaturesUseCase,
)
from kosmo.contracts.llm.ports import LLMResponse, LLMUsage, PromptTemplate
from kosmo.contracts.sdd.document import DocumentNode, RichTextDocument, SectionHeading
from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
    LLMInvocationError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}

    async def by_id(self, project_id: ProjectId) -> Project | None:
        return self.projects.get(str(project_id))

    async def by_slug(self, owner_id: str, slug: str) -> Project | None:  # noqa: ARG002
        return None

    async def find_by_slug(self, slug: str) -> Project | None:  # noqa: ARG002
        return None

    async def list_by_owner(self, owner_id: str) -> list[Project]:  # noqa: ARG002
        return []

    async def save(self, project: Project) -> Project:
        self.projects[str(project.id)] = project
        return project


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.documents: dict[str, RichTextDocument] = {}

    async def get_discovery(self, project_id: ProjectId) -> RichTextDocument | None:
        return self.documents.get(str(project_id))

    async def save_discovery(
        self, project_id: ProjectId, document: RichTextDocument
    ) -> RichTextDocument:
        self.documents[str(project_id)] = document
        return document

    async def get_requirements(self, feature_id: Any) -> RichTextDocument | None:  # noqa: ARG002
        return None

    async def save_requirements(
        self, feature_id: Any, document: RichTextDocument  # noqa: ARG002
    ) -> RichTextDocument:
        return document


class InMemoryFeatureRepository:
    def __init__(self) -> None:
        self.features: dict[str, Feature] = {}

    async def by_id(self, feature_id: FeatureId) -> Feature | None:
        return self.features.get(str(feature_id))

    async def list_by_project(self, project_id: ProjectId) -> list[Feature]:
        return [f for f in self.features.values() if str(f.project_id) == str(project_id)]

    async def save(self, feature: Feature) -> Feature:
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


def _make_valid_features_response() -> LLMResponse:
    json_text = (
        '{"features": [{"title": "Feature 1", '
        '"description": "Descripcion valida de feature", '
        '"number": 1, '
        '"rationale": "Justificacion valida para la feature", '
        '"inferred_from": ["doc1.md"]}]}'
    )
    return LLMResponse(
        text=json_text,
        usage=LLMUsage(total_tokens=100),
        model="mock",
    )


def _make_invalid_features_response() -> LLMResponse:
    return LLMResponse(
        text='{"features": [{"title": "", "description": ""}]}',
        usage=LLMUsage(total_tokens=100),
        model="mock",
    )


@pytest.mark.asyncio
async def test_generate_features_raises_when_project_not_found() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    doc_repo: Any = InMemoryDocumentRepository()
    feat_repo: Any = InMemoryFeatureRepository()
    llm_client: Any = MockLLMClient(response=_make_valid_features_response())
    use_case = GenerateFeaturesUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        feature_repo=feat_repo,
        llm_client=llm_client,
    )

    # Act & Assert
    with pytest.raises(ProjectNotFoundError) as exc_info:
        await use_case.execute(GenerateFeaturesInput(project_id=ProjectId("prj_missing")))

    assert "prj_missing" in str(exc_info.value.problem.detail)
    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
async def test_generate_features_raises_when_discovery_not_found() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    doc_repo: Any = InMemoryDocumentRepository()
    feat_repo: Any = InMemoryFeatureRepository()
    project_id = ProjectId("prj_nodoc")

    project = Project(
        id=project_id,
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_123"),
    )
    await project_repo.save(project)

    llm_client: Any = MockLLMClient(response=_make_valid_features_response())
    use_case = GenerateFeaturesUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        feature_repo=feat_repo,
        llm_client=llm_client,
    )

    # Act & Assert
    with pytest.raises(DocumentNotFoundError) as exc_info:
        await use_case.execute(GenerateFeaturesInput(project_id=project_id))

    assert "discovery" in str(exc_info.value.problem.detail)
    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
async def test_generate_features_generates_features_successfully() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    doc_repo: Any = InMemoryDocumentRepository()
    feat_repo: Any = InMemoryFeatureRepository()
    project_id = ProjectId("prj_gen123")

    project = Project(
        id=project_id,
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_123"),
    )
    await project_repo.save(project)
    await doc_repo.save_discovery(project_id, _make_discovery_document())

    features_response = LLMResponse(
        text=(
            '{"features": [{"title": "Feature Generada", '
            '"description": "Descripcion generada valida y completa", '
            '"number": 1, '
            '"rationale": "Justificacion para feature generada", '
            '"inferred_from": ["discovery.md"]}]}'
        ),
        usage=LLMUsage(total_tokens=100),
        model="mock",
    )
    llm_client: Any = MockLLMClient(response=features_response)
    use_case = GenerateFeaturesUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        feature_repo=feat_repo,
        llm_client=llm_client,
    )

    # Act
    result = await use_case.execute(GenerateFeaturesInput(project_id=project_id))

    # Assert
    assert isinstance(result, GenerateFeaturesOutput)
    assert result.project_id == project_id
    assert len(result.features) == 1
    assert result.features[0].title == "Feature Generada"


@pytest.mark.asyncio
async def test_generate_features_raises_when_llm_fails() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    doc_repo: Any = InMemoryDocumentRepository()
    feat_repo: Any = InMemoryFeatureRepository()
    project_id = ProjectId("prj_llm_err")

    project = Project(
        id=project_id,
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_123"),
    )
    await project_repo.save(project)
    await doc_repo.save_discovery(project_id, _make_discovery_document())

    class FailingLLMClient:
        async def complete(
            self, prompt: PromptTemplate, **kwargs: Any  # noqa: ARG002
        ) -> LLMResponse:
            raise RuntimeError("LLM service unavailable")

    llm_client: Any = FailingLLMClient()
    use_case = GenerateFeaturesUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        feature_repo=feat_repo,
        llm_client=llm_client,
    )

    # Act & Assert
    with pytest.raises(LLMInvocationError) as exc_info:
        await use_case.execute(GenerateFeaturesInput(project_id=project_id))

    assert exc_info.value.problem.status == 502


@pytest.mark.asyncio
async def test_generate_features_persists_generated_features() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    doc_repo: Any = InMemoryDocumentRepository()
    feat_repo: Any = InMemoryFeatureRepository()
    project_id = ProjectId("prj_persist")

    project = Project(
        id=project_id,
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_123"),
    )
    await project_repo.save(project)
    await doc_repo.save_discovery(project_id, _make_discovery_document())

    features_response = LLMResponse(
        text=(
            '{"features": [{"title": "Feature Persistida", '
            '"description": "Descripcion persistida completa y valida", '
            '"number": 1, '
            '"rationale": "Justificacion para feature persistida", '
            '"inferred_from": ["discovery.md"]}]}'
        ),
        usage=LLMUsage(total_tokens=100),
        model="mock",
    )
    llm_client: Any = MockLLMClient(response=features_response)
    use_case = GenerateFeaturesUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        feature_repo=feat_repo,
        llm_client=llm_client,
    )

    # Act
    await use_case.execute(GenerateFeaturesInput(project_id=project_id))

    # Assert
    saved = await feat_repo.list_by_project(project_id)
    assert len(saved) == 1
    assert saved[0].title == "Feature Persistida"
    assert str(saved[0].project_id) == str(project_id)
