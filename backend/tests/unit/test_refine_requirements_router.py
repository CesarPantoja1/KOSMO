import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.requirements.refine_requirements import RefineRequirementsUseCase
from kosmo.contracts.auth import Principal
from kosmo.contracts.pipeline.phase_outputs import (
    EARSPhaseOutput,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import AcceptanceCriterion, EARSPattern
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId, RequirementId, UserId
from kosmo.contracts.sdd.project import Project
from kosmo.infrastructure.api.routers.requirements import (
    RefineRequirementsRequest,
    refine_requirements,
)


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self.projects: dict[str, Project] = {}

    async def by_id(self, project_id: ProjectId) -> Project | None:
        return self.projects.get(str(project_id))

    async def save(self, project: Project) -> Project:
        self.projects[str(project.id)] = project
        return project


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


class InMemoryRequirementRepository:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    async def by_feature_id(self, feature_id: FeatureId) -> str | None:
        return self._data.get(str(feature_id))

    async def save(self, feature_id: FeatureId, markdown: str) -> None:
        self._data[str(feature_id)] = markdown


class StubRefineAgent:
    def __init__(self, output: EARSPhaseOutput) -> None:
        self._output = output

    async def execute_with_skill(
        self, skill_name: str, context: Any, *, project_id: Any = None, user_instructions: str | None = None
    ) -> Any:  # noqa: ARG002
        return self._output


class _FakeState:
    def __init__(self, use_case: RefineRequirementsUseCase, feature_repo: Any) -> None:
        self.refine_requirements = use_case
        self.feature_repo = feature_repo


class _FakeApp:
    def __init__(self, state: _FakeState) -> None:
        self.state = state


class _FakeRequest:
    def __init__(self, use_case: RefineRequirementsUseCase, feature_repo: Any) -> None:
        self.app = _FakeApp(_FakeState(use_case, feature_repo))


def _principal() -> Principal:
    return Principal(subject="usr_test123", scopes=frozenset({"*"}))


def _an_ears_requirement(feature_id: FeatureId) -> EARSRequirement:
    return EARSRequirement(
        id=RequirementId("req_refine01"),
        feature_id=feature_id,
        feature_number=1,
        requirement_number=1,
        title="Presentación de montos",
        pattern=EARSPattern.ubiquitous,
        statement="El sistema debe presentar los montos con dos decimales.",
        origin="Se deriva de la caracteristica C01.",
        acceptance_criteria=[
            AcceptanceCriterion(
                scenario="Presentacion de montos",
                given="un monto valido",
                when="se presenta al usuario",
                then="se muestra con dos decimales",
            ),
            AcceptanceCriterion(
                scenario="Presentacion de montos enteros",
                given="un monto entero",
                when="se presenta al usuario",
                then="se muestra con dos decimales",
            ),
        ],
    )


def _valid_phase_output(feature_id: FeatureId, markdown: str) -> EARSPhaseOutput:
    return EARSPhaseOutput(
        feature_id=feature_id,
        feature_number=1,
        requirements=[_an_ears_requirement(feature_id)],
        requirements_markdown=markdown,
        validation_result=ValidationResult(is_valid=True),
        generation_metadata=GenerationMetadata(),
    )


def _seed_project_and_feature(
    project_repo: InMemoryProjectRepository,
    feature_repo: InMemoryFeatureRepository,
    project_id: str,
    feature_id: str,
) -> None:
    project = Project(
        id=ProjectId(project_id),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_refine01"),
    )
    project_repo.projects[project_id] = project
    feature = Feature(
        id=FeatureId(feature_id),
        number=1,
        title="Test Feature",
        slug="test-feature",
        description="Test feature",
        project_id=project.id,
    )
    feature_repo.features[feature_id] = feature


@pytest.mark.asyncio
@pytest.mark.unit
async def test_refine_requirements_returns_refined_markdown_when_requirements_exist() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    _seed_project_and_feature(project_repo, feature_repo, "prj_refine01", "feat_refine01")
    await requirement_repo.save(FeatureId("feat_refine01"), "## Requisitos EARS\n\noriginal")
    refined_markdown = "## Requisitos EARS\n\nrefinado con criterios adicionales"
    agent = StubRefineAgent(_valid_phase_output(FeatureId("feat_refine01"), refined_markdown))
    use_case = RefineRequirementsUseCase(
        project_repo=project_repo,  # type: ignore[arg-type]
        feature_repo=feature_repo,  # type: ignore[arg-type]
        requirement_repo=requirement_repo,  # type: ignore[arg-type]
        agent=agent,  # type: ignore[arg-type]
    )
    request: Any = _FakeRequest(use_case, feature_repo)
    body = RefineRequirementsRequest(
        project_id="prj_refine01",
        instructions="Agrega casos limite y escenarios alternativos a los criterios.",
    )

    # Act
    result = await refine_requirements(
        feature_id="feat_refine01",
        body=body,
        _principal=_principal(),
        request=request,
    )

    # Assert
    assert result["feature_id"] == "feat_refine01"
    assert result["feature_number"] == 1
    assert result["requirements_markdown"] == refined_markdown
    assert result["total"] == 1
    assert await requirement_repo.by_feature_id(FeatureId("feat_refine01")) == refined_markdown


@pytest.mark.asyncio
@pytest.mark.unit
async def test_refine_requirements_raises_404_when_no_previous_requirements() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    _seed_project_and_feature(project_repo, feature_repo, "prj_refine02", "feat_refine02")
    agent = StubRefineAgent(_valid_phase_output(FeatureId("feat_refine02"), "irrelevante"))
    use_case = RefineRequirementsUseCase(
        project_repo=project_repo,  # type: ignore[arg-type]
        feature_repo=feature_repo,  # type: ignore[arg-type]
        requirement_repo=requirement_repo,  # type: ignore[arg-type]
        agent=agent,  # type: ignore[arg-type]
    )
    request: Any = _FakeRequest(use_case, feature_repo)
    body = RefineRequirementsRequest(
        project_id="prj_refine02",
        instructions="Refina los requisitos existentes.",
    )

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await refine_requirements(
            feature_id="feat_refine02",
            body=body,
            _principal=_principal(),
            request=request,
        )

    # Assert (detalle del error)
    assert exc_info.value.status_code == 404
    assert "feat_refine02" in exc_info.value.detail


@pytest.mark.asyncio
@pytest.mark.unit
async def test_refine_requirements_raises_404_when_feature_not_found() -> None:
    # Arrange
    project_repo = InMemoryProjectRepository()
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    project = Project(
        id=ProjectId("prj_refine03"),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_refine03"),
    )
    project_repo.projects["prj_refine03"] = project
    agent = StubRefineAgent(_valid_phase_output(FeatureId("feat_missing"), "irrelevante"))
    use_case = RefineRequirementsUseCase(
        project_repo=project_repo,  # type: ignore[arg-type]
        feature_repo=feature_repo,  # type: ignore[arg-type]
        requirement_repo=requirement_repo,  # type: ignore[arg-type]
        agent=agent,  # type: ignore[arg-type]
    )
    request: Any = _FakeRequest(use_case, feature_repo)
    body = RefineRequirementsRequest(
        project_id="prj_refine03",
        instructions="Refina los requisitos.",
    )

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await refine_requirements(
            feature_id="feat_missing",
            body=body,
            _principal=_principal(),
            request=request,
        )

    # Assert (detalle del error)
    assert exc_info.value.status_code == 404
    assert "feat_missing" in exc_info.value.detail
