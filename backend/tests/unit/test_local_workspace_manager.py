from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from kosmo.contracts.codegen import CodeWorkspace, WorkspaceRepository, WorkspaceStatus
from kosmo.contracts.sdd.ids import ProjectId, WorkspaceId
from kosmo.infrastructure.codegen.workspace import (
    LocalWorkspaceManager,
    WorkspaceLockedError,
)


class FakeWorkspaceRepository(WorkspaceRepository):
    def __init__(self) -> None:
        self.workspaces: dict[str, CodeWorkspace] = {}

    async def by_project_id(self, project_id: ProjectId) -> CodeWorkspace | None:
        return self.workspaces.get(str(project_id))

    async def by_id(self, workspace_id: WorkspaceId) -> CodeWorkspace | None:
        for ws in self.workspaces.values():
            if str(ws.id) == str(workspace_id):
                return ws
        return None

    async def save(self, workspace: CodeWorkspace) -> CodeWorkspace:
        self.workspaces[str(workspace.project_id)] = workspace
        return workspace

    async def delete(self, project_id: ProjectId) -> None:
        self.workspaces.pop(str(project_id), None)

    async def update_lock(
        self,
        project_id: ProjectId | str,
        is_locked: bool,
        locked_by: str | None = None,
    ) -> CodeWorkspace | None:
        ws = self.workspaces.get(str(project_id))
        if ws is None:
            return None
        updated = CodeWorkspace(
            id=ws.id,
            project_id=ws.project_id,
            status=ws.status,
            workspace_dir=ws.workspace_dir,
            manifest_files=ws.manifest_files,
            current_branch=ws.current_branch,
            is_locked=is_locked,
            locked_at=ws.locked_at,
            locked_by=locked_by if is_locked else None,
            created_at=ws.created_at,
            updated_at=ws.updated_at,
        )
        self.workspaces[str(project_id)] = updated
        return updated

    async def release_lock(self, project_id: ProjectId | str) -> CodeWorkspace | None:
        return await self.update_lock(project_id, is_locked=False, locked_by=None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_workspace_creates_directory_and_manifest() -> None:
    # Arrange
    with tempfile.TemporaryDirectory() as tmp_root, tempfile.TemporaryDirectory() as tmp_template:
        template_path = Path(tmp_template)
        (template_path / "package.json").write_text('{"name": "test"}')
        (template_path / "src").mkdir()
        (template_path / "src" / "index.ts").write_text("console.log('hello');")

        repo = FakeWorkspaceRepository()
        manager = LocalWorkspaceManager(
            workspaces_root=tmp_root,
            workspace_repo=repo,
            template_dir=tmp_template,
            git_init=False,
        )

        project_id = ProjectId("prj_01")

        # Act
        ws = await manager.ensure_workspace(project_id)

        # Assert
        assert ws.project_id == project_id
        assert ws.status == WorkspaceStatus.READY
        assert ws.workspace_dir is not None
        assert Path(ws.workspace_dir).exists()
        assert (Path(ws.workspace_dir) / "package.json").exists()
        assert (Path(ws.workspace_dir) / "src" / "index.ts").exists()

        assert "package.json" in ws.manifest_files
        assert "src/index.ts" in ws.manifest_files

        # Persisted in repo
        persisted = await repo.by_project_id(project_id)
        assert persisted is not None
        assert persisted.workspace_dir == ws.workspace_dir


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_workspace_is_idempotent() -> None:
    # Arrange
    with tempfile.TemporaryDirectory() as tmp_root, tempfile.TemporaryDirectory() as tmp_template:
        template_path = Path(tmp_template)
        (template_path / "package.json").write_text('{"name": "original"}')

        manager = LocalWorkspaceManager(
            workspaces_root=tmp_root,
            template_dir=tmp_template,
            git_init=False,
        )
        project_id = ProjectId("prj_01")

        # Act 1: Initial creation
        ws1 = await manager.ensure_workspace(project_id)
        assert ws1.workspace_dir is not None
        file_path = Path(ws1.workspace_dir) / "package.json"
        file_path.write_text('{"name": "modified"}')

        # Act 2: Second call should not overwrite existing file
        ws2 = await manager.ensure_workspace(project_id)

        # Assert
        assert ws1.workspace_dir == ws2.workspace_dir
        assert file_path.read_text() == '{"name": "modified"}'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_workspace_returns_workspace_or_none() -> None:
    # Arrange
    with tempfile.TemporaryDirectory() as tmp_root:
        manager = LocalWorkspaceManager(workspaces_root=tmp_root, git_init=False)
        project_id = ProjectId("prj_01")

        # Act & Assert before creation
        assert await manager.get_workspace(project_id) is None

        # Act after creation
        created = await manager.ensure_workspace(project_id)
        found = await manager.get_workspace(project_id)

        # Assert
        assert found is not None
        assert found.workspace_dir == created.workspace_dir
        assert found.project_id == project_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_manifest_filters_ignored_directories() -> None:
    # Arrange
    with tempfile.TemporaryDirectory() as tmp_root:
        manager = LocalWorkspaceManager(workspaces_root=tmp_root, git_init=False)
        project_id = ProjectId("prj_01")
        ws = await manager.ensure_workspace(project_id)
        ws_path = Path(ws.workspace_dir)  # type: ignore[arg-type]

        # Create ignored and valid files
        (ws_path / "node_modules").mkdir()
        (ws_path / "node_modules" / "dummy.js").write_text("ignored")
        (ws_path / ".git").mkdir()
        (ws_path / ".git" / "config").write_text("ignored")
        (ws_path / ".next").mkdir()
        (ws_path / ".next" / "cache.json").write_text("ignored")

        (ws_path / "src").mkdir(exist_ok=True)
        (ws_path / "src" / "app.ts").write_text("valid")
        (ws_path / "README.md").write_text("valid")

        # Act
        manifest = await manager.get_manifest(ws)

        # Assert
        assert "src/app.ts" in manifest
        assert "README.md" in manifest
        assert not any("node_modules" in f for f in manifest)
        assert not any(".git" in f for f in manifest)
        assert not any(".next" in f for f in manifest)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_locking_prevents_concurrent_access() -> None:
    # Arrange
    with tempfile.TemporaryDirectory() as tmp_root:
        repo = FakeWorkspaceRepository()
        manager = LocalWorkspaceManager(
            workspaces_root=tmp_root,
            workspace_repo=repo,
            git_init=False,
        )
        project_id = ProjectId("prj_01")
        await manager.ensure_workspace(project_id)

        # Act 1: Initial state is unlocked
        assert await manager.is_locked(project_id) is False

        # Act 2: Acquire lock
        await manager.acquire_lock(project_id)
        assert await manager.is_locked(project_id) is True

        # Act 3: Acquiring lock again raises WorkspaceLockedError
        with pytest.raises(WorkspaceLockedError, match="currently locked"):
            await manager.acquire_lock(project_id)

        # Act 4: Release lock
        await manager.release_lock(project_id)
        assert await manager.is_locked(project_id) is False

        # Act 5: Can acquire lock again after release
        await manager.acquire_lock(project_id)
        assert await manager.is_locked(project_id) is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_manifest_empty_or_nonexistent() -> None:
    # Arrange
    manager = LocalWorkspaceManager(workspaces_root="/tmp/fake_root", git_init=False)
    empty_ws = CodeWorkspace(
        id=WorkspaceId("ws_01"),
        project_id=ProjectId("prj_01"),
        workspace_dir=None,
    )
    nonexistent_ws = CodeWorkspace(
        id=WorkspaceId("ws_01"),
        project_id=ProjectId("prj_01"),
        workspace_dir="/nonexistent/directory/path",
    )

    # Act & Assert
    assert await manager.get_manifest(empty_ws) == ()
    assert await manager.get_manifest(nonexistent_ws) == ()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_workspace_with_git_init() -> None:
    # Arrange
    with tempfile.TemporaryDirectory() as tmp_root:
        manager = LocalWorkspaceManager(workspaces_root=tmp_root, git_init=True)
        project_id = ProjectId("prj_git")

        # Act
        ws = await manager.ensure_workspace(project_id)

        # Assert
        assert ws.workspace_dir is not None
        assert Path(ws.workspace_dir).exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_workspace_repo_with_missing_dir() -> None:
    # Arrange
    with tempfile.TemporaryDirectory() as tmp_root:
        repo = FakeWorkspaceRepository()
        manager = LocalWorkspaceManager(workspaces_root=tmp_root, workspace_repo=repo, git_init=False)
        project_id = ProjectId("prj_01")
        ws = CodeWorkspace(
            id=WorkspaceId("ws_01"),
            project_id=project_id,
            workspace_dir="/nonexistent/path",
        )
        await repo.save(ws)

        # Act
        result = await manager.get_workspace(project_id)

        # Assert
        assert result is not None
        assert result.workspace_dir == "/nonexistent/path"
