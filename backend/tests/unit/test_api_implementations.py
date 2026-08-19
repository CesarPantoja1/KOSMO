from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from kosmo.contracts.auth import Principal
from kosmo.contracts.codegen import (
    CodeWorkspace,
    FeatureImplementation,
    OpenCodeEvent,
    OpenCodeEventType,
    WorkspaceStatus,
)
from kosmo.contracts.sdd.ids import FeatureId, ImplementationId, ProjectId, WorkspaceId
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.dependencies.container import get_container
from kosmo.infrastructure.api.main import app


@pytest.fixture
def mock_broker():
    with patch("kosmo.infrastructure.api.routers.implementations.broker") as mock:
        yield mock


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def valid_token_headers():
    # In KOSMO, we might need a real-ish token, or we can mock get_principal.
    # Usually we mock get_principal or the route depends on it.
    # For unit tests, we can just override the dependency:
    from unittest.mock import MagicMock

    from kosmo.contracts.auth import Principal
    from kosmo.infrastructure.api.dependencies.auth import get_principal
    from kosmo.infrastructure.api.dependencies.container import get_container

    app.dependency_overrides[get_principal] = lambda: Principal(subject="usr_123")
    app.dependency_overrides[get_container] = lambda: MagicMock()
    return {"Authorization": "Bearer mock"}


def test_start_implementation(client: TestClient, mock_broker, valid_token_headers: dict[str, str]) -> None:
    # Arrange
    payload = {
        "feature_id": "feat_01ULXGXXXX",
        "max_retries": 3,
    }

    # Act
    response = client.post(
        "/api/v1/implementations",
        json=payload,
        headers=valid_token_headers,
    )

    # Assert
    assert response.status_code == 202
    data = response.json()
    assert "implementation_id" in data
    assert data["implementation_id"] == "impl_feat_01ULXGXXXX"

    # Verificar que se llamó al broker
    mock_broker.start_implementation.assert_called_once()
    kwargs = mock_broker.start_implementation.call_args.kwargs
    assert kwargs["implementation_id"] == "impl_feat_01ULXGXXXX"


def test_stream_implementation_events(client: TestClient, mock_broker, valid_token_headers: dict[str, str]) -> None:
    # Arrange
    async def fake_subscribe(*_args, **_kwargs) -> AsyncGenerator[OpenCodeEvent]:
        yield OpenCodeEvent(event_type=OpenCodeEventType.PLAN_PROGRESS, session_id="sess_123", data={"msg": "hello"})
        yield OpenCodeEvent(event_type=OpenCodeEventType.DONE, session_id="sess_123", data={})

    mock_broker.subscribe.side_effect = fake_subscribe

    # Act
    with client.stream("GET", "/api/v1/implementations/impl_123/events", headers=valid_token_headers) as response:
        assert response.status_code == 200

        content = response.read().decode()

    # Assert
    assert "event: plan_progress" in content
    assert '"event_type": "plan_progress"' in content
    assert '"msg":"hello"' in content.replace(" ", "")
    assert "event: done" in content


class FakeImplementationRepo:
    def __init__(self, generated_files: tuple[str, ...]) -> None:
        self.generated_files = generated_files

    async def by_id(self, implementation_id: ImplementationId) -> FeatureImplementation | None:
        if str(implementation_id) != "impl_feat_01":
            return None
        now = datetime.now(UTC)
        return FeatureImplementation(
            id=ImplementationId("impl_feat_01"),
            feature_id=FeatureId("feat_01"),
            project_id=ProjectId("prj_01"),
            generated_files=self.generated_files,
            created_at=now,
            updated_at=now,
        )


class FakeWorkspaceRepo:
    def __init__(self, workspace_dir: str) -> None:
        self.workspace_dir = workspace_dir

    async def by_project_id(self, project_id: ProjectId) -> CodeWorkspace | None:
        return CodeWorkspace(
            id=WorkspaceId("ws_01"),
            project_id=ProjectId("prj_01"),
            status=WorkspaceStatus.READY,
            workspace_dir=self.workspace_dir,
        )


class FakeRepos:
    def __init__(self, workspace_dir: str) -> None:
        self.implementations = FakeImplementationRepo(("src/app/page.tsx",))
        self.workspaces = FakeWorkspaceRepo(workspace_dir)


class FakeContainer:
    def __init__(self, workspace_dir: str) -> None:
        self.repos = FakeRepos(workspace_dir)


def test_get_implementation_file_content(
    client: TestClient,
    tmp_path: Path,
) -> None:
    # Arrange
    workspace_dir = tmp_path / "workspaces" / "prj_01"
    workspace_dir.mkdir(parents=True)
    (workspace_dir / "src").mkdir()
    (workspace_dir / "src" / "app").mkdir()
    (workspace_dir / "src" / "app" / "page.tsx").write_text(
        "export default function Page() { return null; }",
        encoding="utf-8",
    )
    app.dependency_overrides[get_principal] = lambda: Principal(subject="usr_123")
    app.dependency_overrides[get_container] = lambda: FakeContainer(str(workspace_dir))

    # Act
    response = client.get(
        "/api/v1/implementations/impl_feat_01/files/content",
        params={"path": "src/app/page.tsx"},
        headers={"Authorization": "Bearer mock"},
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "src/app/page.tsx"
    assert "export default function Page" in data["content"]


def test_get_implementation_file_content_rechaza_traversal(
    client: TestClient,
    tmp_path: Path,
) -> None:
    # Arrange
    app.dependency_overrides[get_principal] = lambda: Principal(subject="usr_123")
    app.dependency_overrides[get_container] = lambda: FakeContainer(str(tmp_path / "workspaces" / "prj_01"))

    # Act
    response = client.get(
        "/api/v1/implementations/impl_feat_01/files/content",
        params={"path": "../secreto.txt"},
        headers={"Authorization": "Bearer mock"},
    )

    # Assert
    assert response.status_code == 422


def test_get_implementation_file_content_not_found(
    client: TestClient,
    tmp_path: Path,
) -> None:
    # Arrange
    app.dependency_overrides[get_principal] = lambda: Principal(subject="usr_123")
    app.dependency_overrides[get_container] = lambda: FakeContainer(str(tmp_path / "workspaces" / "prj_01"))

    # Act
    response = client.get(
        "/api/v1/implementations/impl_missing/files/content",
        params={"path": "src/app/page.tsx"},
        headers={"Authorization": "Bearer mock"},
    )

    # Assert
    assert response.status_code == 404
