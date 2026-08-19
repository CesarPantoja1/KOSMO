from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from kosmo.infrastructure.git import (
    GitError,
    git_add,
    git_commit,
    git_has_commits,
    git_init,
    git_is_clean,
    git_rollback,
    git_status,
)


@pytest.mark.unit
def test_git_init_creates_repo_with_branch_and_config() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        git_init(path, initial_branch="main", user_name="Test Bot", user_email="test@bot.com")

        assert (path / ".git").exists()
        assert (path / ".git").is_dir()

        # Verificar configuración de usuario
        res_name = subprocess.run(
            ["git", "config", "user.name"],
            cwd=path,
            capture_output=True,
            text=True,
            check=False,
        )
        res_email = subprocess.run(
            ["git", "config", "user.email"],
            cwd=path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert res_name.stdout.strip() == "Test Bot"
        assert res_email.stdout.strip() == "test@bot.com"


@pytest.mark.unit
def test_git_add_and_commit() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        git_init(path)

        # Crear archivo
        file1 = path / "hello.txt"
        file1.write_text("Hello Git!", encoding="utf-8")

        assert not git_has_commits(path)
        assert not git_is_clean(path)

        # Staging y commit
        git_add(path)
        committed = git_commit(path, "feat: initial commit")

        assert committed is True
        assert git_has_commits(path)
        assert git_is_clean(path)


@pytest.mark.unit
def test_git_commit_no_changes_returns_false() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        git_init(path)

        file1 = path / "hello.txt"
        file1.write_text("Hello Git!", encoding="utf-8")
        git_add(path)
        git_commit(path, "feat: first commit")

        # Intentar commitear sin cambios
        second_commit = git_commit(path, "feat: second commit without changes")
        assert second_commit is False


@pytest.mark.unit
def test_git_rollback_reverts_modifications_and_removes_untracked() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        git_init(path)

        # Estado inicial limpio con un commit
        tracked_file = path / "tracked.txt"
        tracked_file.write_text("version 1.0", encoding="utf-8")
        git_add(path)
        git_commit(path, "chore: initial version")

        # Realizar cambios fallidos durante un reintento
        tracked_file.write_text("broken modifications", encoding="utf-8")
        untracked_file = path / "untracked.ts"
        untracked_file.write_text("bad code", encoding="utf-8")
        untracked_dir = path / "temp_folder"
        untracked_dir.mkdir()
        (untracked_dir / "nested.ts").write_text("nested bad code", encoding="utf-8")

        assert not git_is_clean(path)

        # Act: Ejecutar rollback
        git_rollback(path)

        # Assert: Todo volvió al estado del último commit exitoso
        assert tracked_file.read_text(encoding="utf-8") == "version 1.0"
        assert not untracked_file.exists()
        assert not untracked_dir.exists()
        assert git_is_clean(path)


@pytest.mark.unit
def test_git_rollback_when_no_head_removes_untracked() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        git_init(path)

        untracked_file = path / "draft.txt"
        untracked_file.write_text("draft content", encoding="utf-8")

        # Rollback sin commits
        git_rollback(path)

        assert not untracked_file.exists()


@pytest.mark.unit
def test_git_status_and_is_clean() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        git_init(path)

        assert git_is_clean(path)

        (path / "file.txt").write_text("content", encoding="utf-8")
        status = git_status(path)
        assert "file.txt" in status
        assert not git_is_clean(path)


@pytest.mark.unit
def test_git_operations_on_nonexistent_dir_raise_git_error() -> None:
    non_existent = Path("/nonexistent/path/for/kosmo/git/tests")

    with pytest.raises(GitError, match="El directorio del workspace no existe"):
        git_add(non_existent)

    with pytest.raises(GitError, match="El directorio del workspace no existe"):
        git_status(non_existent)
