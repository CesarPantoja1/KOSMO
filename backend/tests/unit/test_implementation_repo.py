from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.codegen import (
    FeatureImplementation,
    FeatureImplementationStatus,
    FileAction,
    FileOperation,
    ImplementationPlan,
    ValidationRunResult,
    ValidationStep,
    ValidationStepResult,
)
from kosmo.contracts.sdd.ids import FeatureId, ImplementationId, ProjectId
from kosmo.infrastructure.persistence.postgres.models import FeatureImplementationModel
from kosmo.infrastructure.persistence.postgres.repositories.feature_implementation_repo import (
    SqlAlchemyFeatureImplementationRepository,
)


def _make_impl(
    impl_id: str = "impl_01",
    feature_id: str = "feat_01",
    project_id: str = "prj_01",
    status: FeatureImplementationStatus = FeatureImplementationStatus.IN_PROGRESS,
    session_id: str | None = "oc_sess_1",
    plan: ImplementationPlan | None = None,
    last_validation: ValidationRunResult | None = None,
) -> FeatureImplementation:
    now = datetime.now(UTC)
    return FeatureImplementation(
        id=ImplementationId(impl_id),
        feature_id=FeatureId(feature_id),
        project_id=ProjectId(project_id),
        status=status,
        session_id=session_id,
        plan=plan,
        last_validation=last_validation,
        attempt_count=1,
        max_attempts=3,
        generated_files=("src/app/page.tsx",),
        retry_history=(("error tsc",),),
        created_at=now,
        updated_at=now,
    )


def _make_plan() -> ImplementationPlan:
    return ImplementationPlan(
        feature_id=FeatureId("feat_01"),
        operations=(FileOperation(path="src/app/page.tsx", action=FileAction.CREATE, description="crear página"),),
        summary="Plan para la feature",
        created_at=datetime.now(UTC),
    )


def _make_validation() -> ValidationRunResult:
    return ValidationRunResult(
        steps=(
            ValidationStepResult(
                step=ValidationStep.TYPECHECK,
                success=True,
                duration_ms=120,
                exit_code=0,
                raw_output="ok",
                error_messages=(),
            ),
        ),
        all_passed=True,
        total_duration_ms=120,
        executed_at=datetime.now(UTC),
        error_summary=(),
    )


def _make_async_session_mock(returned_model: FeatureImplementationModel | None = None) -> MagicMock:
    mock_session = MagicMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = returned_model
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()
    return mock_session


def _make_session_factory(mock_session: MagicMock) -> MagicMock:
    mock_session_factory = MagicMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_session_factory


def _make_model(
    impl_id: str = "impl_01",
    feature_id: str = "feat_01",
    project_id: str = "prj_01",
) -> FeatureImplementationModel:
    now = datetime.now(UTC)
    return FeatureImplementationModel(
        id=impl_id,
        feature_id=feature_id,
        project_id=project_id,
        status="in_progress",
        session_id="oc_sess_1",
        plan=None,
        last_validation=None,
        attempt_count=1,
        max_attempts=3,
        generated_files=["src/app/page.tsx"],
        retry_history=[],
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_init_raises_without_session_or_factory() -> None:
    # Act & Assert
    with pytest.raises(ValueError, match="Se requiere session_factory o session"):
        SqlAlchemyFeatureImplementationRepository(session_factory=None, session=None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_inserts_when_no_existing_implementation() -> None:
    # Arrange
    impl = _make_impl(plan=_make_plan(), last_validation=_make_validation())
    mock_session = _make_async_session_mock(returned_model=None)
    repo = SqlAlchemyFeatureImplementationRepository(session_factory=_make_session_factory(mock_session))

    # Act
    result = await repo.save(impl)

    # Assert
    assert result == impl
    mock_session.add.assert_called_once()
    added_model = mock_session.add.call_args[0][0]
    assert added_model.id == "impl_01"
    assert added_model.feature_id == "feat_01"
    assert added_model.project_id == "prj_01"
    assert added_model.status == "in_progress"
    assert added_model.session_id == "oc_sess_1"
    assert added_model.attempt_count == 1
    assert added_model.max_attempts == 3
    assert added_model.generated_files == ["src/app/page.tsx"]
    assert added_model.plan["feature_id"] == "feat_01"
    assert added_model.plan["operations"][0]["path"] == "src/app/page.tsx"
    assert added_model.last_validation["all_passed"] is True
    assert added_model.last_validation["steps"][0]["step"] == "typecheck"
    mock_session.commit.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_updates_when_existing_implementation() -> None:
    # Arrange
    impl = _make_impl(status=FeatureImplementationStatus.IMPLEMENTED, session_id=None, plan=None)
    existing_model = _make_model()
    mock_session = _make_async_session_mock(returned_model=existing_model)
    repo = SqlAlchemyFeatureImplementationRepository(session_factory=_make_session_factory(mock_session))

    # Act
    result = await repo.save(impl)

    # Assert
    assert result == impl
    mock_session.add.assert_not_called()
    assert existing_model.status == "implemented"
    assert existing_model.session_id is None
    assert existing_model.updated_at is not None
    mock_session.commit.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_stores_none_plan_and_validation() -> None:
    # Arrange
    impl = _make_impl(plan=None, last_validation=None)
    mock_session = _make_async_session_mock(returned_model=None)
    repo = SqlAlchemyFeatureImplementationRepository(session_factory=_make_session_factory(mock_session))

    # Act
    await repo.save(impl)

    # Assert
    added_model = mock_session.add.call_args[0][0]
    assert added_model.plan is None
    assert added_model.last_validation is None
    assert added_model.retry_history == [["error tsc"]]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_by_feature_id_returns_implementation_when_found() -> None:
    # Arrange
    model = _make_model()
    model.plan = {
        "feature_id": "feat_01",
        "operations": [
            {"path": "src/app/page.tsx", "action": "create", "description": "crear página"},
        ],
        "summary": "Plan",
        "estimated_effort": "",
        "created_at": "2026-08-19T10:00:00+00:00",
    }
    model.last_validation = {
        "steps": [
            {
                "step": "typecheck",
                "success": True,
                "duration_ms": 120,
                "exit_code": 0,
                "raw_output": "ok",
                "errors": [],
                "error_messages": [],
            },
        ],
        "all_passed": True,
        "total_duration_ms": 120,
        "executed_at": "2026-08-19T10:01:00+00:00",
        "error_summary": [],
    }
    mock_session = _make_async_session_mock(returned_model=model)
    repo = SqlAlchemyFeatureImplementationRepository(session=mock_session)

    # Act
    result = await repo.by_feature_id(FeatureId("feat_01"))

    # Assert
    assert result is not None
    assert result.id == "impl_01"
    assert result.project_id == "prj_01"
    assert result.plan is not None
    assert result.plan.operations[0].path == "src/app/page.tsx"
    assert result.plan.operations[0].action == FileAction.CREATE
    assert result.last_validation is not None
    assert result.last_validation.all_passed is True
    assert result.last_validation.steps[0].step == ValidationStep.TYPECHECK
    assert result.generated_files == ("src/app/page.tsx",)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_by_feature_id_returns_none_when_not_found() -> None:
    # Arrange
    mock_session = _make_async_session_mock(returned_model=None)
    repo = SqlAlchemyFeatureImplementationRepository(session=mock_session)

    # Act
    result = await repo.by_feature_id(FeatureId("feat_missing"))

    # Assert
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_by_id_returns_implementation_when_found() -> None:
    # Arrange
    model = _make_model()
    mock_session = _make_async_session_mock(returned_model=model)
    repo = SqlAlchemyFeatureImplementationRepository(session=mock_session)

    # Act
    result = await repo.by_id(ImplementationId("impl_01"))

    # Assert
    assert result is not None
    assert result.id == "impl_01"
    assert result.feature_id == "feat_01"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_by_id_returns_none_when_not_found() -> None:
    # Arrange
    mock_session = _make_async_session_mock(returned_model=None)
    repo = SqlAlchemyFeatureImplementationRepository(session=mock_session)

    # Act
    result = await repo.by_id(ImplementationId("impl_missing"))

    # Assert
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_by_project_returns_implementations() -> None:
    # Arrange
    model_a = _make_model()
    model_b = _make_model(impl_id="impl_02", feature_id="feat_02")
    mock_session = _make_async_session_mock()
    mock_session.execute.return_value.scalars.return_value.all.return_value = [model_a, model_b]
    repo = SqlAlchemyFeatureImplementationRepository(session=mock_session)

    # Act
    result = await repo.list_by_project(ProjectId("prj_01"))

    # Assert
    assert len(result) == 2
    assert [str(r.id) for r in result] == ["impl_01", "impl_02"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_removes_implementation() -> None:
    # Arrange
    mock_session = _make_async_session_mock()
    repo = SqlAlchemyFeatureImplementationRepository(session=mock_session)

    # Act
    await repo.delete(FeatureId("feat_01"))

    # Assert
    mock_session.execute.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_commits_when_repo_owns_session() -> None:
    # Arrange
    mock_session = _make_async_session_mock()
    repo = SqlAlchemyFeatureImplementationRepository(session_factory=_make_session_factory(mock_session))

    # Act
    await repo.delete(FeatureId("feat_01"))

    # Assert
    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_awaited_once()
