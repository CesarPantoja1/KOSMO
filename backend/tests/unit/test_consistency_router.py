from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException

from kosmo.application.consistency.evaluate_project_consistency import (
    EvaluateProjectConsistencyUseCase,
)
from kosmo.contracts import ConsistencyEvaluationOutput, ConsistencyEvaluator
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.infrastructure.api.routers.consistency import evaluate_consistency
from kosmo.infrastructure.api.schemas import (
    ChangeInputView,
    ConsistencyReportView,
    EvaluateConsistencyRequestView,
)
from tests.unit.fakes import (
    InMemoryActivityDiagramRepository,
    InMemoryFeatureRepository,
    InMemoryProjectRepository,
    InMemoryRequirementRepository,
)


class StubConsistencyEvaluator(ConsistencyEvaluator):
    def __init__(self, *, affected_ids: list[str] | None = None, should_fail: bool = False) -> None:
        self._affected_ids = affected_ids or []
        self._should_fail = should_fail

    async def evaluate(
        self,
        *,
        source_phase: Any,
        target_phase: Any,
        project_id: Any,
        applied_changes: Any,
    ) -> ConsistencyEvaluationOutput:
        if self._should_fail:
            raise RuntimeError("Stub failure")
        return ConsistencyEvaluationOutput(report_id="rpt_stub", affected_artifact_ids=list(self._affected_ids))


async def _make_uc(
    evaluator: StubConsistencyEvaluator,
    feature_repo: InMemoryFeatureRepository,
    requirement_repo: InMemoryRequirementRepository,
    diagram_repo: InMemoryActivityDiagramRepository,
) -> EvaluateProjectConsistencyUseCase:
    from kosmo.contracts.sdd.project import Project

    project_repo = InMemoryProjectRepository()
    project = Project(
        id=ProjectId("prj_001"),
        name="Test",
        slug="test",
        description="Test",
        owner_id="usr_test",
    )
    await project_repo.save(project)
    return EvaluateProjectConsistencyUseCase(
        project_repo=project_repo,  # type: ignore[reportArgumentType]
        evaluator=evaluator,  # type: ignore[reportArgumentType]
        feature_repo=feature_repo,  # type: ignore[reportArgumentType]
        requirement_repo=requirement_repo,  # type: ignore[reportArgumentType]
        diagram_repo=diagram_repo,  # type: ignore[reportArgumentType]
    )


def _principal() -> Principal:
    return Principal(subject="usr_test123", scopes=frozenset({"*"}))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_consistency_returns_report_with_affected_features() -> None:
    evaluator = StubConsistencyEvaluator(affected_ids=["feat_01"])
    feature_repo = InMemoryFeatureRepository()
    from kosmo.contracts.sdd.feature import Feature

    feature = Feature(
        id=FeatureId("feat_01"),
        number=1,
        title="Gestión de catálogo",
        slug="gestion-catalogo",
        description="Feature desc",
        project_id=ProjectId("prj_001"),
    )
    await feature_repo.save(feature)

    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    uc = await _make_uc(evaluator, feature_repo, requirement_repo, diagram_repo)

    request_body = EvaluateConsistencyRequestView(
        phase_origin="discovery",
        phase_destination="features",
        changes=[
            ChangeInputView(section="Alcance", diff_before="Alcance 1", diff_after="Alcance 2"),
        ],
    )

    result = await evaluate_consistency(
        project_id="prj_001",
        _principal=_principal(),
        request=request_body,
        uc=uc,
    )

    assert isinstance(result, ConsistencyReportView)
    assert result.phase_origin == "discovery"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_consistency_no_destination_evaluates_all_phases() -> None:
    evaluator = StubConsistencyEvaluator(affected_ids=["feat_01"])
    feature_repo = InMemoryFeatureRepository()
    from kosmo.contracts.sdd.feature import Feature

    feature = Feature(
        id=FeatureId("feat_01"),
        number=2,
        title="Otra feature",
        slug="otra-feature",
        description="Desc",
        project_id=ProjectId("prj_001"),
    )
    await feature_repo.save(feature)

    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    uc = await _make_uc(evaluator, feature_repo, requirement_repo, diagram_repo)

    request_body = EvaluateConsistencyRequestView(
        phase_origin="discovery",
        changes=[
            ChangeInputView(section="Visión", diff_before="old", diff_after="new"),
        ],
    )

    result = await evaluate_consistency(
        project_id="prj_001",
        _principal=_principal(),
        request=request_body,
        uc=uc,
    )

    assert isinstance(result, ConsistencyReportView)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evaluate_consistency_unknown_origin_phase_raises_400() -> None:
    evaluator = StubConsistencyEvaluator()
    feature_repo = InMemoryFeatureRepository()
    requirement_repo = InMemoryRequirementRepository()
    diagram_repo = InMemoryActivityDiagramRepository()
    uc = await _make_uc(evaluator, feature_repo, requirement_repo, diagram_repo)

    request_body = EvaluateConsistencyRequestView(
        phase_origin="unknown_phase",
        changes=[],
    )

    with pytest.raises(HTTPException) as exc_info:
        await evaluate_consistency(
            project_id="prj_001",
            _principal=_principal(),
            request=request_body,
            uc=uc,
        )

    assert exc_info.value.status_code == 400
