import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.requirements.generate_ears import (
    GenerateEARSInput,
    GenerateEARSOutput,
    GenerateEARSUseCase,
)
from kosmo.contracts.pipeline.phase_outputs import (
    EARSPhaseOutput,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import (
    AcceptanceCriterion,
    RichTextDocument,
)
from kosmo.contracts.sdd.ears import EARSPattern, EARSRequirement
from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
    FeatureNotFoundError,
    LLMInvocationError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, RequirementId, UserId
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

    async def save_many(self, features: list[Feature]) -> list[Feature]:
        for f in features:
            self.features[str(f.id)] = f
        return features


class InMemoryRequirementRepository:
    def __init__(self) -> None:
        self.requirements: dict[str, str] = {}

    async def save(self, feature_id: FeatureId, markdown: str) -> None:
        self.requirements[str(feature_id)] = markdown

    async def by_feature_id(self, feature_id: FeatureId) -> str | None:
        return self.requirements.get(str(feature_id))


class MockAgent:
    def __init__(self, output: Any) -> None:
        self._output = output

    async def execute(self, phase: Any, context: Any) -> Any:  # noqa: ARG002
        return self._output


def _make_feature(feature_id: str = "feat_01") -> Feature:
    return Feature(
        id=FeatureId(feature_id),
        number=1,
        title="Test Feature",
        slug="test-feature",
        description="Test feature description",
        project_id=ProjectId("prj_01"),
    )


def _make_discovery_document() -> RichTextDocument:
    return RichTextDocument(nodes=[])


def _make_valid_ears_output() -> EARSPhaseOutput:
    req = EARSRequirement(
        id=RequirementId("req_01TEST"),
        feature_id=FeatureId("feat_01"),
        feature_number=1,
        requirement_number=1,
        pattern=EARSPattern.ubiquitous,
        trigger="",
        system="El sistema",
        response="debe gestionar los datos de forma segura",
        source_statement="El sistema shall gestionar los datos de forma segura",
        rationale="Requisito fundamental",
        traceability=["C01"],
        acceptance_criteria=[
            AcceptanceCriterion(
                given="un usuario autenticado",
                when="accede a sus datos",
                then="los datos se muestran correctamente",
            ),
            AcceptanceCriterion(
                given="un usuario no autenticado",
                when="intenta acceder",
                then="recibe un error de autenticacion",
            ),
        ],
    )
    return EARSPhaseOutput(
        feature_id=FeatureId("feat_01"),
        feature_number=1,
        requirements=[req],
        requirements_markdown="### REQ-1.1\n\nEl sistema shall gestionar los datos de forma segura",
        validation_result=ValidationResult(is_valid=True),
        generation_metadata=GenerationMetadata(llm_calls=1),
    )


@pytest.mark.asyncio
async def test_generate_ears_success() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    doc_repo = InMemoryDocumentRepository()
    feat_repo = InMemoryFeatureRepository()
    req_repo = InMemoryRequirementRepository()
    project = Project(
        id=ProjectId("prj_01"),
        name="Test Project",
        slug="test-project",
        description="Testing",
        owner_id=UserId("usr_01"),
    )
    await project_repo.save(project)
    await doc_repo.save_discovery(ProjectId("prj_01"), _make_discovery_document())
    feature = _make_feature()
    await feat_repo.save_many([feature])
    agent = MockAgent(output=_make_valid_ears_output())
    use_case = GenerateEARSUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        feature_repo=feat_repo,
        requirement_repo=req_repo,
        agent=agent,
    )

    # Act
    result = await use_case.execute(
        GenerateEARSInput(project_id=ProjectId("prj_01"), feature_id=FeatureId("feat_01"))
    )

    # Assert
    assert isinstance(result, GenerateEARSOutput)
    assert len(result.requirements) >= 1
    assert result.requirements[0].pattern == EARSPattern.ubiquitous


@pytest.mark.asyncio
async def test_generate_ears_raises_project_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    doc_repo = InMemoryDocumentRepository()
    feat_repo = InMemoryFeatureRepository()
    req_repo = InMemoryRequirementRepository()
    agent = MockAgent(output=_make_valid_ears_output())
    use_case = GenerateEARSUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        feature_repo=feat_repo,
        requirement_repo=req_repo,
        agent=agent,
    )

    # Act & Assert
    with pytest.raises(ProjectNotFoundError) as exc_info:
        await use_case.execute(
            GenerateEARSInput(project_id=ProjectId("prj_missing"), feature_id=FeatureId("feat_01"))
        )
    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
async def test_generate_ears_raises_feature_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    doc_repo = InMemoryDocumentRepository()
    feat_repo = InMemoryFeatureRepository()
    req_repo = InMemoryRequirementRepository()
    project = Project(
        id=ProjectId("prj_01"),
        name="Test Project",
        slug="test-project",
        description="Testing",
        owner_id=UserId("usr_01"),
    )
    await project_repo.save(project)
    agent = MockAgent(output=_make_valid_ears_output())
    use_case = GenerateEARSUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        feature_repo=feat_repo,
        requirement_repo=req_repo,
        agent=agent,
    )

    # Act & Assert
    with pytest.raises(FeatureNotFoundError) as exc_info:
        await use_case.execute(
            GenerateEARSInput(project_id=ProjectId("prj_01"), feature_id=FeatureId("feat_missing"))
        )
    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
async def test_generate_ears_raises_document_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    doc_repo = InMemoryDocumentRepository()
    feat_repo = InMemoryFeatureRepository()
    req_repo = InMemoryRequirementRepository()
    project = Project(
        id=ProjectId("prj_01"),
        name="Test Project",
        slug="test-project",
        description="Testing",
        owner_id=UserId("usr_01"),
    )
    await project_repo.save(project)
    feature = _make_feature()
    await feat_repo.save_many([feature])
    agent = MockAgent(output=_make_valid_ears_output())
    use_case = GenerateEARSUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        feature_repo=feat_repo,
        requirement_repo=req_repo,
        agent=agent,
    )

    # Act & Assert
    with pytest.raises(DocumentNotFoundError) as exc_info:
        await use_case.execute(
            GenerateEARSInput(project_id=ProjectId("prj_01"), feature_id=FeatureId("feat_01"))
        )
    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
async def test_generate_ears_persists_requirements_markdown() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    doc_repo = InMemoryDocumentRepository()
    feat_repo = InMemoryFeatureRepository()
    req_repo = InMemoryRequirementRepository()
    project = Project(
        id=ProjectId("prj_01"),
        name="Test Project",
        slug="test-project",
        description="Testing",
        owner_id=UserId("usr_01"),
    )
    await project_repo.save(project)
    await doc_repo.save_discovery(ProjectId("prj_01"), _make_discovery_document())
    feature = _make_feature()
    await feat_repo.save_many([feature])
    agent = MockAgent(output=_make_valid_ears_output())
    use_case = GenerateEARSUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        feature_repo=feat_repo,
        requirement_repo=req_repo,
        agent=agent,
    )

    # Act
    result = await use_case.execute(
        GenerateEARSInput(project_id=ProjectId("prj_01"), feature_id=FeatureId("feat_01"))
    )

    # Assert
    saved = await req_repo.by_feature_id(FeatureId("feat_01"))
    assert saved is not None
    assert "shall" in saved
    assert len(result.requirements) == 1


@pytest.mark.asyncio
async def test_generate_ears_raises_when_llm_fails() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    doc_repo = InMemoryDocumentRepository()
    feat_repo = InMemoryFeatureRepository()
    req_repo = InMemoryRequirementRepository()
    project = Project(
        id=ProjectId("prj_01"),
        name="Test Project",
        slug="test-project",
        description="Testing",
        owner_id=UserId("usr_01"),
    )
    await project_repo.save(project)
    await doc_repo.save_discovery(ProjectId("prj_01"), _make_discovery_document())
    feature = _make_feature()
    await feat_repo.save_many([feature])

    class FailingAgent:
        async def execute(self, phase: Any, context: Any) -> Any:  # noqa: ARG002
            raise RuntimeError("LLM service unavailable")

    agent = FailingAgent()
    use_case = GenerateEARSUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        feature_repo=feat_repo,
        requirement_repo=req_repo,
        agent=agent,
    )

    # Act & Assert
    with pytest.raises(LLMInvocationError) as exc_info:
        await use_case.execute(
            GenerateEARSInput(project_id=ProjectId("prj_01"), feature_id=FeatureId("feat_01"))
        )
    assert exc_info.value.problem.status == 502
