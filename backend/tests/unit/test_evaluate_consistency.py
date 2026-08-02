from __future__ import annotations

import pytest

from kosmo.application.consistency.evaluate_consistency import EvaluateConsistencyUseCase
from kosmo.contracts import DiffCambio, EstadoPlanCambio, PlanCambio
from kosmo.contracts.consistency import ConsistencyEvaluationOutput
from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, PlanChangeId, ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    DocumentRepository,
    FeatureRepository,
    RequirementRepository,
)
from tests.unit.fakes import (
    InMemoryActivityDiagramRepository,
    InMemoryDocumentRepository,
    InMemoryFeatureRepository,
    InMemoryProjectRepository,
    InMemoryRequirementRepository,
)


class StubConsistencyAgent:
    def __init__(self, *, affected_ids: list[str] | None = None, should_fail: bool = False) -> None:
        self._affected_ids = affected_ids or []
        self._should_fail = should_fail

    async def execute_with_skill(  # noqa: ARG002
        self,
        skill_name: str,
        context: object,
        *,
        project_id: object | None = None,
        user_instructions: str | None = None,
    ) -> object:
        if self._should_fail:
            raise RuntimeError("Stub agent failure")
        return {"affected_artifact_ids": list(self._affected_ids), "rationale": "Stub evaluation"}

    async def execute_conversation(
        self,
        skill_name: str,
        messages: list[object],
        context: object,
        **kwargs: object,  # noqa: ARG002
    ) -> object:
        raise NotImplementedError("Not used in consistency tests")


def _make_project(project_id: str = "prj_test") -> Project:
    return Project(
        id=ProjectId(project_id),
        name="Test Project",
        slug="test-project",
        description="Test",
        owner_id=UserId("usr_test"),
    )


def _make_feature(feature_id: str, project_id: str, title: str, number: int = 1) -> Feature:
    return Feature(
        id=FeatureId(feature_id),
        number=number,
        title=title,
        slug=title.lower().replace(" ", "-"),
        description=f"Descripción de {title}",
        project_id=ProjectId(project_id),
        origin="Derivado de Descubrimiento",
    )


def _plan_change(cid: str, before: str = "old", after: str = "new") -> PlanCambio:
    return PlanCambio(
        id=PlanChangeId(cid),
        section="Alcance",
        description="Cambio de alcance",
        diff=DiffCambio(before=before, after=after),
        status=EstadoPlanCambio.APPLIED,
    )


def _make_uc(
    agent: AgentPort,
    feature_repo: FeatureRepository,
    requirement_repo: RequirementRepository,
    diagram_repo: ActivityDiagramRepository,
    document_repo: DocumentRepository,
) -> EvaluateConsistencyUseCase:
    return EvaluateConsistencyUseCase(
        agent=agent,
        feature_repo=feature_repo,
        requirement_repo=requirement_repo,
        diagram_repo=diagram_repo,
        document_repo=document_repo,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_identifies_affected_features() -> None:
    # Arrange
    project = _make_project("prj_001")
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)

    feature_repo = InMemoryFeatureRepository()
    feat = _make_feature("feat_01", "prj_001", "Gestión de catálogo", number=1)
    await feature_repo.save(feat)

    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    document_repo = InMemoryDocumentRepository()

    agent = StubConsistencyAgent(affected_ids=["feat_01"])
    uc = _make_uc(agent, feature_repo, requirement_repo, diagram_repo, document_repo)

    change = _plan_change("chg_01", before="Alcance original", after="Alcance LATAM")

    # Act
    result = await uc.evaluate(
        source_phase=SpecPhase.DESCUBRIMIENTO,
        target_phase=SpecPhase.CARACTERISTICAS,
        project_id=ProjectId("prj_001"),
        applied_changes=[change],
    )

    # Assert
    assert isinstance(result, ConsistencyEvaluationOutput)
    assert result.report_id.startswith("cnr_")
    assert result.affected_artifact_ids == ["feat_01"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_agent_failure_returns_empty() -> None:
    # Arrange
    project = _make_project("prj_002")
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)

    feature_repo = InMemoryFeatureRepository()
    feat = _make_feature("feat_02", "prj_002", "Feature Test", number=1)
    await feature_repo.save(feat)

    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    document_repo = InMemoryDocumentRepository()

    agent = StubConsistencyAgent(should_fail=True)
    uc = _make_uc(agent, feature_repo, requirement_repo, diagram_repo, document_repo)

    change = _plan_change("chg_01")

    # Act
    result = await uc.evaluate(
        source_phase=SpecPhase.DESCUBRIMIENTO,
        target_phase=SpecPhase.CARACTERISTICAS,
        project_id=ProjectId("prj_002"),
        applied_changes=[change],
    )

    # Assert
    assert result.affected_artifact_ids == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_no_downstream_artifacts_returns_empty() -> None:
    # Arrange
    project = _make_project("prj_003")
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)

    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    document_repo = InMemoryDocumentRepository()

    agent = StubConsistencyAgent(affected_ids=["should_not_appear"])
    uc = _make_uc(agent, feature_repo, requirement_repo, diagram_repo, document_repo)

    change = _plan_change("chg_01")

    # Act
    result = await uc.evaluate(
        source_phase=SpecPhase.DESCUBRIMIENTO,
        target_phase=SpecPhase.CARACTERISTICAS,
        project_id=ProjectId("prj_003"),
        applied_changes=[change],
    )

    # Assert: sin features registradas, el evaluador devuelve vacío sin llamar al agente
    assert result.affected_artifact_ids == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_filters_out_unknown_ids() -> None:
    # Arrange
    project = _make_project("prj_004")
    project_repo = InMemoryProjectRepository()
    await project_repo.save(project)

    feature_repo = InMemoryFeatureRepository()
    feat = _make_feature("feat_04", "prj_004", "Feature Real", number=1)
    await feature_repo.save(feat)

    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    document_repo = InMemoryDocumentRepository()

    agent = StubConsistencyAgent(affected_ids=["feat_04", "feat_fantasma"])
    uc = _make_uc(agent, feature_repo, requirement_repo, diagram_repo, document_repo)

    change = _plan_change("chg_01")

    # Act
    result = await uc.evaluate(
        source_phase=SpecPhase.DESCUBRIMIENTO,
        target_phase=SpecPhase.CARACTERISTICAS,
        project_id=ProjectId("prj_004"),
        applied_changes=[change],
    )

    # Assert: solo devuelve IDs que corresponden a artefactos reales
    assert result.affected_artifact_ids == ["feat_04"]
