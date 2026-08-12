from __future__ import annotations

import pytest

from kosmo.application.requirements.regenerate_requirements import (
    RegenerateRequirementsInput,
    RegenerateRequirementsOutput,
    RegenerateRequirementsUseCase,
)
from kosmo.contracts.pipeline.phase_outputs import (
    EARSPhaseOutput,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.errors import (
    FeatureNotFoundError,
    LLMInvocationError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from tests.unit.fakes import (
    InMemoryFeatureRepository,
    InMemoryProjectRepository,
    InMemoryRequirementRepository,
)


class StubRegenRequirementsAgent:
    def __init__(self, *, should_fail: bool = False) -> None:
        self._should_fail = should_fail

    async def execute_with_skill(
        self,
        skill_name: str,
        context: object,
        *,
        project_id: object | None = None,  # noqa: ARG002
        user_instructions: str | None = None,  # noqa: ARG002
    ) -> object:
        if self._should_fail:
            raise RuntimeError("Stub agent failure")

        return EARSPhaseOutput(
            feature_id=FeatureId("feat_01"),
            feature_number=1,
            requirements=[],
            requirements_markdown="### REQ-1.1\n\nEl sistema shall procesar pagos.\n",
            validation_result=ValidationResult(is_valid=True, errors=[]),
            generation_metadata=GenerationMetadata(),
        )

    async def execute_conversation(
        self,
        skill_name: str,
        messages: list[object],
        context: object,
        **kwargs: object,  # noqa: ARG002
    ) -> object:
        raise NotImplementedError


@pytest.mark.asyncio
@pytest.mark.unit
async def test_regenerate_requirements_success() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    project_id = ProjectId("prj_001")
    await project_repo.save(
        Project(
            id=project_id,
            name="Test Project",
            slug="test-project",
            description="Test",
            owner_id=UserId("usr_test"),
        )
    )

    feature_repo = InMemoryFeatureRepository()
    feature_id = FeatureId("feat_01")
    await feature_repo.save(
        Feature(
            id=feature_id,
            number=1,
            title="Procesar pagos",
            slug="procesar-pagos",
            description="Gestiona pagos electrónicos",
            project_id=project_id,
        )
    )

    requirement_repo = InMemoryRequirementRepository()
    await requirement_repo.save(feature_id, "### REQ-1.1\n\nEARS original.\n")

    agent = StubRegenRequirementsAgent()
    uc = RegenerateRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        agent=agent,
    )

    # Act
    result = await uc.execute(RegenerateRequirementsInput(project_id=project_id, feature_id=feature_id))

    # Assert
    assert isinstance(result, RegenerateRequirementsOutput)
    assert result.phase == "requirements"
    assert result.artifact_id == "feat_01"
    assert "REQ-1.1" in result.content

    saved = await requirement_repo.by_feature_id(feature_id)
    assert saved is not None
    assert "REQ-1.1" in saved


@pytest.mark.asyncio
@pytest.mark.unit
async def test_regenerate_requirements_project_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()

    uc = RegenerateRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        agent=StubRegenRequirementsAgent(),
    )

    # Act & Assert
    with pytest.raises(ProjectNotFoundError):
        await uc.execute(
            RegenerateRequirementsInput(
                project_id=ProjectId("prj_missing"),
                feature_id=FeatureId("feat_01"),
            )
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_regenerate_requirements_feature_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    project_id = ProjectId("prj_001")
    await project_repo.save(
        Project(
            id=project_id,
            name="Test Project",
            slug="test-project",
            description="Test",
            owner_id=UserId("usr_test"),
        )
    )

    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()

    uc = RegenerateRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        agent=StubRegenRequirementsAgent(),
    )

    # Act & Assert
    with pytest.raises(FeatureNotFoundError):
        await uc.execute(
            RegenerateRequirementsInput(
                project_id=project_id,
                feature_id=FeatureId("feat_missing"),
            )
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_regenerate_requirements_agent_failure() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    project_id = ProjectId("prj_001")
    await project_repo.save(
        Project(
            id=project_id,
            name="Test Project",
            slug="test-project",
            description="Test",
            owner_id=UserId("usr_test"),
        )
    )

    feature_repo = InMemoryFeatureRepository()
    feature_id = FeatureId("feat_01")
    await feature_repo.save(
        Feature(
            id=feature_id,
            number=1,
            title="Procesar pagos",
            slug="procesar-pagos",
            description="Gestiona pagos electrónicos",
            project_id=project_id,
        )
    )

    requirement_repo = InMemoryRequirementRepository()
    await requirement_repo.save(feature_id, "### REQ-1.1\n\nEARS original.\n")

    agent = StubRegenRequirementsAgent(should_fail=True)
    uc = RegenerateRequirementsUseCase(
        project_repo=project_repo,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        agent=agent,
    )

    # Act & Assert
    with pytest.raises(LLMInvocationError, match="Error al regenerar"):
        await uc.execute(RegenerateRequirementsInput(project_id=project_id, feature_id=feature_id))
