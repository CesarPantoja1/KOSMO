from dataclasses import dataclass
from typing import Any

import pytest

from kosmo.application.discovery.generate_discovery import (
    GenerateDiscoveryInput,
    GenerateDiscoveryOutput,
    GenerateDiscoveryUseCase,
)
from kosmo.contracts.pipeline.phase_outputs import (
    DiscoveryPhaseOutput,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import (
    DocumentNode,
    RichTextDocument,
    SectionHeading,
)
from kosmo.contracts.sdd.errors import LLMInvocationError, ProjectNotFoundError
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from tests.unit.fakes import InMemoryDocumentRepository, InMemoryProjectRepository


@dataclass(frozen=True)
class MockKOSMOAgent:
    output: DiscoveryPhaseOutput

    async def execute_with_skill(
        self, skill_name: str, context: Any, *, project_id: Any = None, user_instructions: str | None = None
    ) -> DiscoveryPhaseOutput:  # noqa: ARG002
        return self.output


def _make_phase_output(title: str = "Generated Discovery") -> DiscoveryPhaseOutput:
    return DiscoveryPhaseOutput(
        discovery_document=RichTextDocument(
            nodes=[
                DocumentNode(
                    type="heading",
                    heading=SectionHeading(text=title, level=2, slug="generated"),
                    content="Contenido generado por IA",
                ),
            ]
        ),
        validation_result=ValidationResult(is_valid=True, errors=[]),
        generation_metadata=GenerationMetadata(llm_calls=1, total_tokens=100),
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_discovery_success() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    doc_repo: Any = InMemoryDocumentRepository()
    project = Project(
        id=ProjectId("prj_gen123"),
        name="Test Project",
        slug="test-project",
        description="A test project",
        owner_id=UserId("usr_123"),
    )
    await project_repo.save(project)

    phase_output = _make_phase_output("Discovery del Proyecto")
    agent: Any = MockKOSMOAgent(output=phase_output)

    use_case = GenerateDiscoveryUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        agent=agent,
    )

    # Act
    result = await use_case.execute(GenerateDiscoveryInput(project_id=ProjectId("prj_gen123")))

    # Assert
    assert isinstance(result, GenerateDiscoveryOutput)
    assert result.project_id == ProjectId("prj_gen123")
    assert result.document.nodes[0].heading is not None
    assert result.document.nodes[0].heading.text == "Discovery del Proyecto"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_discovery_raises_when_project_not_found() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    doc_repo: Any = InMemoryDocumentRepository()
    phase_output = _make_phase_output()
    agent: Any = MockKOSMOAgent(output=phase_output)

    use_case = GenerateDiscoveryUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        agent=agent,
    )

    # Act & Assert
    with pytest.raises(ProjectNotFoundError) as exc_info:
        await use_case.execute(GenerateDiscoveryInput(project_id=ProjectId("prj_missing")))

    assert "prj_missing" in str(exc_info.value.problem.detail)
    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_discovery_raises_when_llm_fails() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    doc_repo: Any = InMemoryDocumentRepository()
    project = Project(
        id=ProjectId("prj_llm_err"),
        name="Test Project",
        slug="test-project",
        description="A test project",
        owner_id=UserId("usr_123"),
    )
    await project_repo.save(project)

    class FailingAgent:
        async def execute_with_skill(
            self,
            skill_name: str,  # noqa: ARG002
            context: Any,  # noqa: ARG002
            *,
            project_id: Any = None,  # noqa: ARG002
            user_instructions: str | None = None,  # noqa: ARG002
        ) -> DiscoveryPhaseOutput:
            raise RuntimeError("LLM service unavailable")

    agent: Any = FailingAgent()

    use_case = GenerateDiscoveryUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        agent=agent,
    )

    # Act & Assert
    with pytest.raises(LLMInvocationError) as exc_info:
        await use_case.execute(GenerateDiscoveryInput(project_id=ProjectId("prj_llm_err")))

    assert exc_info.value.problem.status == 502


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_discovery_succeeds_despite_validation_failure() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    doc_repo: Any = InMemoryDocumentRepository()
    project = Project(
        id=ProjectId("prj_invalid"),
        name="Test Project",
        slug="test-project",
        description="A test project",
        owner_id=UserId("usr_123"),
    )
    await project_repo.save(project)

    invalid_output = DiscoveryPhaseOutput(
        discovery_document=RichTextDocument(
            nodes=[
                DocumentNode(
                    type="heading",
                    heading=SectionHeading(text="Visión del producto", level=2, slug="v"),
                    content="Contenido incompleto",
                )
            ]
        ),
        validation_result=ValidationResult(is_valid=False, errors=["Seccion faltante: Metas del producto"]),
        generation_metadata=GenerationMetadata(llm_calls=8, total_tokens=0),
    )
    agent: Any = MockKOSMOAgent(output=invalid_output)

    use_case = GenerateDiscoveryUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        agent=agent,
    )

    # Act
    output = await use_case.execute(GenerateDiscoveryInput(project_id=ProjectId("prj_invalid")))

    # Assert
    assert output.phase_output.validation_result.is_valid is False
    assert await doc_repo.get_discovery(ProjectId("prj_invalid")) is not None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_discovery_raises_when_document_is_empty() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    doc_repo: Any = InMemoryDocumentRepository()
    project = Project(
        id=ProjectId("prj_empty"),
        name="Test Project",
        slug="test-project",
        description="A test project",
        owner_id=UserId("usr_123"),
    )
    await project_repo.save(project)

    empty_output = DiscoveryPhaseOutput(
        discovery_document=RichTextDocument(nodes=[]),
        validation_result=ValidationResult(is_valid=True, errors=[]),
        generation_metadata=GenerationMetadata(llm_calls=8, total_tokens=0),
    )
    agent: Any = MockKOSMOAgent(output=empty_output)

    use_case = GenerateDiscoveryUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        agent=agent,
    )

    # Act & Assert
    with pytest.raises(LLMInvocationError):
        await use_case.execute(GenerateDiscoveryInput(project_id=ProjectId("prj_empty")))

    assert await doc_repo.get_discovery(ProjectId("prj_empty")) is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_discovery_persists_generated_document() -> None:
    # Arrange
    project_repo: Any = InMemoryProjectRepository()
    doc_repo: Any = InMemoryDocumentRepository()
    project = Project(
        id=ProjectId("prj_persist"),
        name="Test Project",
        slug="test-project",
        description="A test project",
        owner_id=UserId("usr_123"),
    )
    await project_repo.save(project)

    phase_output = _make_phase_output("Documento Persistido")
    agent: Any = MockKOSMOAgent(output=phase_output)

    use_case = GenerateDiscoveryUseCase(
        project_repo=project_repo,
        document_repo=doc_repo,
        agent=agent,
    )

    # Act
    await use_case.execute(GenerateDiscoveryInput(project_id=ProjectId("prj_persist")))

    # Assert
    saved = await doc_repo.get_discovery(ProjectId("prj_persist"))
    assert saved is not None
    assert saved.nodes[0].heading.text == "Documento Persistido"
