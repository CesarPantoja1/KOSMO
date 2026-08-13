from typing import Any

import pytest

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
    SpecPhase,
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
from tests.unit.fakes import (
    InMemoryDocumentRepository,
    InMemoryFeatureRepository,
    InMemoryProjectRepository,
    InMemoryRequirementRepository,
    InMemoryTraceabilityRepository,
    InMemoryUnitOfWork,
)


class MockAgent:
    def __init__(self, output: Any) -> None:
        self._output = output

    async def execute_with_skill(
        self, skill_name: str, context: Any, *, project_id: Any = None, user_instructions: str | None = None
    ) -> Any:  # noqa: ARG002
        return self._output


def _make_uc(
    project_repo: InMemoryProjectRepository,
    document_repo: InMemoryDocumentRepository,
    feature_repo: InMemoryFeatureRepository,
    requirement_repo: InMemoryRequirementRepository,
    agent: Any,
    traceability: InMemoryTraceabilityRepository | None = None,
) -> GenerateEARSUseCase:
    uow = InMemoryUnitOfWork(
        projects=project_repo,
        documents=document_repo,
        features=feature_repo,
        requirements=requirement_repo,
        traceability=traceability,
    )
    return GenerateEARSUseCase(uow=uow, agent=agent)  # type: ignore[arg-type]


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
        title="Gestión segura de datos",
        pattern=EARSPattern.ubiquitous,
        statement="El sistema shall gestionar los datos de forma segura",
        origin="Requisito fundamental. Se deriva de C01 y Reglas de negocio.",
        acceptance_criteria=[
            AcceptanceCriterion(
                scenario="Acceso autenticado",
                given="un usuario autenticado",
                when="accede a sus datos",
                then="los datos se muestran correctamente",
            ),
            AcceptanceCriterion(
                scenario="Acceso no autenticado",
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
        requirements_markdown=(
            "### REQ-1.1\n\n| Campo | Contenido |\n|-------|-----------|\n"
            "| **Patrón** | Requisitos Ubicuos |\n"
            "| **Enunciado** | El sistema shall gestionar los datos de forma segura |\n\n"
            "#### Criterios de Aceptación\n\n"
            "**Escenario: Acceso autenticado**\n\n"
            "- **Dado** que un usuario autenticado\n"
            "- **Cuando** accede a sus datos\n"
            "- **Entonces** los datos se muestran correctamente"
        ),
        validation_result=ValidationResult(is_valid=True),
        generation_metadata=GenerationMetadata(llm_calls=1),
    )


@pytest.mark.asyncio
@pytest.mark.unit
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
    use_case = _make_uc(project_repo, doc_repo, feat_repo, req_repo, agent)

    # Act
    result = await use_case.execute(GenerateEARSInput(project_id=ProjectId("prj_01"), feature_id=FeatureId("feat_01")))

    # Assert
    assert isinstance(result, GenerateEARSOutput)
    assert len(result.requirements) >= 1
    assert result.requirements[0].pattern == EARSPattern.ubiquitous


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_ears_raises_project_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    doc_repo = InMemoryDocumentRepository()
    feat_repo = InMemoryFeatureRepository()
    req_repo = InMemoryRequirementRepository()
    agent = MockAgent(output=_make_valid_ears_output())
    use_case = _make_uc(project_repo, doc_repo, feat_repo, req_repo, agent)

    # Act & Assert
    with pytest.raises(ProjectNotFoundError) as exc_info:
        await use_case.execute(GenerateEARSInput(project_id=ProjectId("prj_missing"), feature_id=FeatureId("feat_01")))
    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
@pytest.mark.unit
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
    use_case = _make_uc(project_repo, doc_repo, feat_repo, req_repo, agent)

    # Act & Assert
    with pytest.raises(FeatureNotFoundError) as exc_info:
        await use_case.execute(GenerateEARSInput(project_id=ProjectId("prj_01"), feature_id=FeatureId("feat_missing")))
    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
@pytest.mark.unit
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
    use_case = _make_uc(project_repo, doc_repo, feat_repo, req_repo, agent)

    # Act & Assert
    with pytest.raises(DocumentNotFoundError) as exc_info:
        await use_case.execute(GenerateEARSInput(project_id=ProjectId("prj_01"), feature_id=FeatureId("feat_01")))
    assert exc_info.value.problem.status == 404


@pytest.mark.asyncio
@pytest.mark.unit
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
    use_case = _make_uc(project_repo, doc_repo, feat_repo, req_repo, agent)

    # Act
    result = await use_case.execute(GenerateEARSInput(project_id=ProjectId("prj_01"), feature_id=FeatureId("feat_01")))

    # Assert
    saved = await req_repo.by_feature_id(FeatureId("feat_01"))
    assert saved is not None
    assert "shall" in saved
    assert len(result.requirements) == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_ears_records_traceability_edges_and_advances_phase() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    doc_repo = InMemoryDocumentRepository()
    feat_repo = InMemoryFeatureRepository()
    req_repo = InMemoryRequirementRepository()
    traceability = InMemoryTraceabilityRepository()
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
    use_case = _make_uc(project_repo, doc_repo, feat_repo, req_repo, agent, traceability)

    # Act
    result = await use_case.execute(GenerateEARSInput(project_id=ProjectId("prj_01"), feature_id=FeatureId("feat_01")))

    # Assert: edges feature→requirement y avance de fase en la misma ejecucion
    assert len(traceability.edges) == 1
    assert traceability.edges[0][0] == "feature"
    assert traceability.edges[0][1] == "feat_01"
    assert traceability.edges[0][2] == "requirement"
    assert traceability.edges[0][3] == str(result.requirements[0].id)

    persisted_project = await project_repo.by_id(ProjectId("prj_01"))
    assert persisted_project is not None
    assert persisted_project.current_phase == SpecPhase.REQUISITOS.value


@pytest.mark.asyncio
@pytest.mark.unit
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
        async def execute_with_skill(
            self, skill_name: str, context: Any, *, project_id: Any = None, user_instructions: str | None = None
        ) -> Any:  # noqa: ARG002
            raise RuntimeError("LLM service unavailable")

    agent = FailingAgent()
    use_case = _make_uc(project_repo, doc_repo, feat_repo, req_repo, agent)

    # Act & Assert
    with pytest.raises(LLMInvocationError) as exc_info:
        await use_case.execute(GenerateEARSInput(project_id=ProjectId("prj_01"), feature_id=FeatureId("feat_01")))
    assert exc_info.value.problem.status == 502
