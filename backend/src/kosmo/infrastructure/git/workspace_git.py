from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class GitError(RuntimeError):
    """Lanzada cuando ocurre un error al ejecutar un comando de Git en el workspace."""


def _run_git(
    cmd: list[str],
    workspace_path: Path | str,
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Helper interno para ejecutar comandos de Git dentro de un directorio de workspace."""
    cwd = Path(workspace_path).resolve()
    if not cwd.exists():
        raise GitError(f"El directorio del workspace no existe: {cwd}")

    try:
        res = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as e:
        raise GitError("Git no está instalado o no se encuentra en el PATH del sistema.") from e
    except Exception as e:
        raise GitError(f"Error al ejecutar el comando Git {' '.join(cmd)}: {e}") from e

    if check and res.returncode != 0:
        err_msg = res.stderr.strip() or res.stdout.strip() or f"Código de salida: {res.returncode}"
        raise GitError(f"Fallo al ejecutar {' '.join(cmd)} en {cwd}: {err_msg}")

    return res


def git_init(
    workspace_path: Path | str,
    initial_branch: str = "main",
    user_name: str = "KOSMO Bot",
    user_email: str = "bot@kosmo.ai",
) -> None:
    """Inicializa un repositorio Git local en el workspace y configura la identidad local."""
    cwd = Path(workspace_path).resolve()
    if not cwd.exists():
        cwd.mkdir(parents=True, exist_ok=True)

    # Intentar git init con -b para configurar rama inicial
    res = _run_git(["git", "init", "-b", initial_branch], cwd, check=False)
    if res.returncode != 0:
        # Fallback para versiones antiguas de Git que no soportan -b
        _run_git(["git", "init"], cwd, check=True)
        _run_git(["git", "checkout", "-B", initial_branch], cwd, check=False)

    # Configurar identidad local en el repositorio para evitar errores en commits
    _run_git(["git", "config", "user.name", user_name], cwd, check=False)
    _run_git(["git", "config", "user.email", user_email], cwd, check=False)


def git_add(workspace_path: Path | str, pattern: str = ".") -> None:
    """Añade archivos al área de preparación (staging)."""
    _run_git(["git", "add", pattern], workspace_path, check=True)


def git_commit(
    workspace_path: Path | str,
    message: str,
    *,
    allow_empty: bool = False,
) -> bool:
    """Crea un commit con los cambios preparados.

    Retorna True si se creó un commit exitosamente, o False si no había cambios que commitear.
    """
    cmd = ["git", "commit", "-m", message]
    if allow_empty:
        cmd.append("--allow-empty")

    res = _run_git(cmd, workspace_path, check=False)
    if res.returncode == 0:
        return True

    combined_output = (res.stdout + " " + res.stderr).lower()
    if "nothing to commit" in combined_output or "no changes added to commit" in combined_output:
        logger.debug("No hay cambios para commitear en %s", workspace_path)
        return False

    err_msg = res.stderr.strip() or res.stdout.strip() or f"Código de salida: {res.returncode}"
    raise GitError(f"Fallo en git commit: {err_msg}")


def git_rollback(workspace_path: Path | str) -> None:
    """Realiza un rollback determinista descartando cambios rastreados y eliminando no rastreados.

    Ejecuta 'git reset --hard HEAD' y 'git clean -fd'.
    """
    cwd = Path(workspace_path).resolve()
    if not cwd.exists():
        return

    # Verificar si el repo tiene commits previos
    has_head = git_has_commits(cwd)
    if has_head:
        _run_git(["git", "reset", "--hard", "HEAD"], cwd, check=True)
    else:
        # Si no hay commits previos, desestagear todo
        _run_git(["git", "rm", "-rf", "--cached", "."], cwd, check=False)

    # Limpiar archivos y directorios no rastreados
    _run_git(["git", "clean", "-fd"], cwd, check=True)


def git_status(workspace_path: Path | str) -> str:
    """Obtiene la salida de git status --porcelain."""
    res = _run_git(["git", "status", "--porcelain"], workspace_path, check=True)
    return res.stdout


def git_is_clean(workspace_path: Path | str) -> bool:
    """Verifica si el working tree está completamente limpio."""
    status = git_status(workspace_path)
    return len(status.strip()) == 0


def git_has_commits(workspace_path: Path | str) -> bool:
    """Comprueba si el repositorio tiene al menos un commit en HEAD."""
    res = _run_git(["git", "rev-parse", "--verify", "HEAD"], workspace_path, check=False)
    return res.returncode == 0


def git_head_hash(workspace_path: Path | str) -> str | None:
    """Retorna el hash completo del commit en HEAD, o None si no hay commits."""
    res = _run_git(["git", "rev-parse", "HEAD"], workspace_path, check=False)
    if res.returncode != 0:
        return None
    return res.stdout.strip() or None


def git_revert_commit(workspace_path: Path | str, commit: str) -> None:
    """Revierte un commit conservando el resto del historial (git revert --no-edit)."""
    _run_git(["git", "revert", "--no-edit", commit], workspace_path, check=True)
