from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.dependencies.container import get_container
from kosmo.infrastructure.api.main import app


class _Projects:
    async def by_id(self, project_id: ProjectId) -> SimpleNamespace | None:
        if str(project_id) != "prj_01ABC":
            return None
        return SimpleNamespace(id=project_id, owner_id=UserId("usr_01"))


def test_preview_publica_host_sin_guion_bajo(tmp_path: Path) -> None:
    # Arrange
    (tmp_path / ".preview-ports.json").write_text(
        '{"prj_01ABC":{"port":3000,"url":"http://localhost:3000"}}', encoding="utf-8"
    )
    container = SimpleNamespace(
        repos=SimpleNamespace(projects=_Projects()),
        settings=SimpleNamespace(
            kosmo_workspaces_dir=tmp_path,
            preview_public_host_suffix="preview-kosmo.cespan.dev",
        ),
    )
    app.dependency_overrides[get_principal] = lambda: Principal(subject="usr_01")
    app.dependency_overrides[get_container] = lambda: container

    try:
        # Act
        response = TestClient(app).get("/api/v1/projects/prj_01ABC/preview")

        # Assert
        assert response.status_code == 200
        assert response.json() == {"url": "https://prj-01abc-preview-kosmo.cespan.dev"}
    finally:
        app.dependency_overrides.clear()
