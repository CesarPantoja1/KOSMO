from dataclasses import dataclass
from typing import Any

import pytest

from kosmo.application.features.generate_features import (
    GenerateFeaturesInput,
    GenerateFeaturesOutput,
    GenerateFeaturesUseCase,
)
from kosmo.contracts.pipeline.phase_outputs import (
    FeaturesPhaseOutput,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import DocumentNode, RichTextDocument, SectionHeading
from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
    LLMInvocationError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from tests.unit.fakes import InMemoryDocumentRepository, InMemoryFeatureRepository, InMemoryProjectRepository


@dataclass
class MockAgent:
    output: Any

    async def execute_with_skill(
        self, skill_name: str, context: Any, *, project_id: Any = None, user_instructions: str | None = None
    ) -> Any:  # noqa: ARG002
        return self.output


def _make_discovery_document() -> RichTextDocument:
    return RichTextDocument(
        nodes=[
            DocumentNode(
                type="heading",
                heading=SectionHeading(text="Sistema de Gestion", level=2, slug="sistema-gestion"),
                content="Contenido del discovery",
            ),
        ]
    )


def _make_valid_features_output() -> FeaturesPhaseOutput:
    feature = Feature(
        id=FeatureId("feat_test01"),
        number=1,
        title="Feature 1",
        slug="feature-1",
        description="Descripcion valida de feature",
        project_id=ProjectId("prj_test"),
        origin="Se deriva de las metas. Se traza a Metas del producto.",
    )
    return FeaturesPhaseOutput(
        features=[feature],
        validation_result=ValidationResult(is_valid=True),
        generation_metadata=GenerationMetadata(llm_calls=1),
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_features_raises_when_project_not_found() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    doc_repo: Any = InMemoryDocumentRepository()
    feat_repo: Any = InMemoryFeatureRepository()
    agent: Any = MockAgent(output=_make_valid_features_output())
    use_case = GenerateFeaturesUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        feature_repo=feat_repo,
        agent=agent,
    )

    # Act & Assert
    with pytest.raises(ProjectNotFoundError) as exc_info:
        await use_case.execute(GenerateFeaturesInput(project_id=ProjectId("prj_missing")))

    assert "prj_missing" in str(exc_info.value.problem.detail)
    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_features_raises_when_discovery_not_found() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    doc_repo: Any = InMemoryDocumentRepository()
    feat_repo: Any = InMemoryFeatureRepository()
    agent: Any = MockAgent(output=_make_valid_features_output())
    use_case = GenerateFeaturesUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        feature_repo=feat_repo,
        agent=agent,
    )
    project = Project(
        id=ProjectId("prj_test"),
        name="Test Project",
        slug="test-project",
        description="Testing",
        owner_id=UserId("usr_test"),
    )
    await project_repo.save(project)

    # Act & Assert
    with pytest.raises(DocumentNotFoundError) as exc_info:
        await use_case.execute(GenerateFeaturesInput(project_id=ProjectId("prj_test")))

    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_features_generates_features_successfully() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    doc_repo: Any = InMemoryDocumentRepository()
    feat_repo: Any = InMemoryFeatureRepository()
    project = Project(
        id=ProjectId("prj_test"),
        name="Test Project",
        slug="test-project",
        description="Testing",
        owner_id=UserId("usr_test"),
    )
    await project_repo.save(project)
    await doc_repo.save_discovery(ProjectId("prj_test"), _make_discovery_document())
    agent: Any = MockAgent(output=_make_valid_features_output())

    use_case = GenerateFeaturesUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        feature_repo=feat_repo,
        agent=agent,
    )

    # Act
    result = await use_case.execute(GenerateFeaturesInput(project_id=ProjectId("prj_test")))

    # Assert
    assert isinstance(result, GenerateFeaturesOutput)
    assert result.project_id == ProjectId("prj_test")
    assert len(result.features) == 1
    assert result.features[0].title == "Feature 1"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_features_raises_when_llm_fails() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    doc_repo: Any = InMemoryDocumentRepository()
    feat_repo: Any = InMemoryFeatureRepository()
    project = Project(
        id=ProjectId("prj_llm_fail"),
        name="Test Project",
        slug="test-project",
        description="Testing",
        owner_id=UserId("usr_test"),
    )
    await project_repo.save(project)
    await doc_repo.save_discovery(ProjectId("prj_llm_fail"), _make_discovery_document())

    class FailingAgent:
        async def execute_with_skill(
            self, skill_name: str, context: Any, *, project_id: Any = None, user_instructions: str | None = None
        ) -> Any:  # noqa: ARG002
            raise RuntimeError("LLM service unavailable")

    agent: Any = FailingAgent()

    use_case = GenerateFeaturesUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        feature_repo=feat_repo,
        agent=agent,
    )

    # Act & Assert
    with pytest.raises(LLMInvocationError) as exc_info:
        await use_case.execute(GenerateFeaturesInput(project_id=ProjectId("prj_llm_fail")))

    assert exc_info.value.problem.status == 502


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_features_persists_generated_features() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    doc_repo: Any = InMemoryDocumentRepository()
    feat_repo: Any = InMemoryFeatureRepository()
    project = Project(
        id=ProjectId("prj_persist"),
        name="Test Project",
        slug="test-project",
        description="Testing",
        owner_id=UserId("usr_test"),
    )
    await project_repo.save(project)
    await doc_repo.save_discovery(ProjectId("prj_persist"), _make_discovery_document())
    agent: Any = MockAgent(output=_make_valid_features_output())

    use_case = GenerateFeaturesUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        feature_repo=feat_repo,
        agent=agent,
    )

    # Act
    result = await use_case.execute(GenerateFeaturesInput(project_id=ProjectId("prj_persist")))

    # Assert
    saved = await feat_repo.list_by_project(ProjectId("prj_persist"))
    assert len(saved) == 1
    assert saved[0].title == "Feature 1"
    assert result.features[0].id is not None
