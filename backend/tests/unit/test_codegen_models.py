from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects import postgresql as pg

from kosmo.infrastructure.persistence.postgres.models import (
    Base,
    FeatureImplementationModel,
    WorkspaceModel,
)


@pytest.mark.unit
def test_workspace_model_metadata() -> None:
    # Arrange & Act
    table = Base.metadata.tables.get("workspaces")

    # Assert
    assert table is not None
    assert "id" in table.columns
    assert isinstance(table.columns["id"].type, String)
    assert table.columns["id"].primary_key is True

    assert "project_id" in table.columns
    assert isinstance(table.columns["project_id"].type, String)
    assert table.columns["project_id"].nullable is False
    assert len(table.columns["project_id"].foreign_keys) == 1
    fk = next(iter(table.columns["project_id"].foreign_keys))
    assert fk.target_fullname == "projects.id"

    assert "current_branch" in table.columns
    assert isinstance(table.columns["current_branch"].type, String)
    assert table.columns["current_branch"].nullable is False

    assert "is_locked" in table.columns
    assert isinstance(table.columns["is_locked"].type, Boolean)
    assert table.columns["is_locked"].nullable is False

    assert "locked_at" in table.columns
    assert isinstance(table.columns["locked_at"].type, DateTime)
    assert table.columns["locked_at"].nullable is True

    assert "locked_by" in table.columns
    assert isinstance(table.columns["locked_by"].type, String)
    assert table.columns["locked_by"].nullable is True

    assert "path" in table.columns
    assert isinstance(table.columns["path"].type, Text)
    assert table.columns["path"].nullable is False

    assert "created_at" in table.columns
    assert isinstance(table.columns["created_at"].type, DateTime)
    assert table.columns["created_at"].nullable is False

    assert "updated_at" in table.columns
    assert isinstance(table.columns["updated_at"].type, DateTime)
    assert table.columns["updated_at"].nullable is False


@pytest.mark.unit
def test_feature_implementation_model_metadata() -> None:
    # Arrange & Act
    table = Base.metadata.tables.get("feature_implementations")

    # Assert
    assert table is not None
    assert "id" in table.columns
    assert table.columns["id"].primary_key is True

    assert "feature_id" in table.columns
    assert len(table.columns["feature_id"].foreign_keys) == 1
    fk_feat = next(iter(table.columns["feature_id"].foreign_keys))
    assert fk_feat.target_fullname == "features.id"

    assert "project_id" in table.columns
    assert len(table.columns["project_id"].foreign_keys) == 1
    fk_prj = next(iter(table.columns["project_id"].foreign_keys))
    assert fk_prj.target_fullname == "projects.id"

    assert "status" in table.columns
    assert isinstance(table.columns["status"].type, String)

    assert "session_id" in table.columns
    assert isinstance(table.columns["session_id"].type, String)
    assert table.columns["session_id"].nullable is True

    assert "plan" in table.columns
    assert isinstance(table.columns["plan"].type, pg.JSONB)
    assert table.columns["plan"].nullable is True

    assert "last_validation" in table.columns
    assert isinstance(table.columns["last_validation"].type, pg.JSONB)
    assert table.columns["last_validation"].nullable is True

    assert "attempt_count" in table.columns
    assert isinstance(table.columns["attempt_count"].type, Integer)
    assert table.columns["attempt_count"].nullable is False

    assert "max_attempts" in table.columns
    assert isinstance(table.columns["max_attempts"].type, Integer)
    assert table.columns["max_attempts"].nullable is False

    assert "generated_files" in table.columns
    assert isinstance(table.columns["generated_files"].type, pg.JSONB)
    assert table.columns["generated_files"].nullable is False

    assert "retry_history" in table.columns
    assert isinstance(table.columns["retry_history"].type, pg.JSONB)
    assert table.columns["retry_history"].nullable is False

    assert "created_at" in table.columns
    assert isinstance(table.columns["created_at"].type, DateTime)

    assert "updated_at" in table.columns
    assert isinstance(table.columns["updated_at"].type, DateTime)


@pytest.mark.unit
def test_models_instantiation() -> None:
    # Arrange
    now = datetime.now(UTC)

    # Act
    ws = WorkspaceModel(
        id="ws_01",
        project_id="prj_01",
        current_branch="feature/feat_01",
        is_locked=True,
        locked_at=now,
        locked_by="user_01",
        path="/workspaces/prj_01",
        created_at=now,
        updated_at=now,
    )
    impl = FeatureImplementationModel(
        id="impl_01",
        feature_id="feat_01",
        project_id="prj_01",
        status="in_progress",
        session_id="oc_sess_1",
        plan={"feature_id": "feat_01", "operations": []},
        last_validation=None,
        attempt_count=1,
        max_attempts=3,
        generated_files=[],
        retry_history=[],
        created_at=now,
        updated_at=now,
    )

    # Assert
    assert ws.id == "ws_01"
    assert ws.is_locked is True
    assert impl.id == "impl_01"
    assert impl.status == "in_progress"
    assert impl.session_id == "oc_sess_1"
    assert impl.plan == {"feature_id": "feat_01", "operations": []}
