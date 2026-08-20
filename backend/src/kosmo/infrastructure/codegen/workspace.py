from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import functools
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

import structlog

from kosmo.contracts.codegen import (
    CodeRunnerPort,
    CodeWorkspace,
    WorkspaceManagerPort,
    WorkspaceRepository,
    WorkspaceStatus,
)
from kosmo.contracts.sdd.ids import ProjectId, WorkspaceId
from kosmo.contracts.sdd.repositories import ProjectRepository
from kosmo.infrastructure.git import (
    git_add,
    git_commit,
    git_init,
    git_rollback,
)
from kosmo.infrastructure.sandbox.code_runner import INSTALL_COMMAND, INSTALL_TIMEOUT_SECONDS

_log = structlog.get_logger("kosmo.codegen.workspace")

_IGNORED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        ".next",
        "dist",
        "build",
        "__pycache__",
        ".turbo",
        ".pytest_cache",
        ".coverage",
    }
)

DEFAULT_TEMPLATE_DIR: Path = Path(__file__).parent / "templates" / "basic-next-app"

_AGENTS_TEMPLATE_PATH: Path = Path(__file__).parent / "templates" / "workspace" / "AGENTS.md.tmpl"
_SKILLS_TEMPLATE_DIR: Path = DEFAULT_TEMPLATE_DIR / ".opencode" / "skills"


@functools.cache
def _read_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _generate_agents_md(project_name: str) -> str:
    """Genera el contenido de AGENTS.md para el workspace de implementación."""
    return _read_template(_AGENTS_TEMPLATE_PATH).replace("{{PROJECT_NAME}}", project_name)


def _generate_implementation_skill_md() -> str:
    """Genera la skill kosmo-implementation para el workspace de implementación."""
    return _read_template(_SKILLS_TEMPLATE_DIR / "kosmo-implementation" / "SKILL.md")


def _generate_testing_skill_md() -> str:
    """Genera la skill kosmo-testing (TDD con Vitest) para el workspace de implementación."""
    return _read_template(_SKILLS_TEMPLATE_DIR / "kosmo-testing" / "SKILL.md")


def _generate_tdd_skill_md() -> str:
    """Mantiene compatibilidad con alias tdd."""
    return _read_template(_SKILLS_TEMPLATE_DIR / "tdd" / "SKILL.md")


def _generate_drizzle_skill_md() -> str:
    """Genera la skill kosmo-drizzle para modelado y consultas con Drizzle ORM sobre SQLite."""
    return _read_template(_SKILLS_TEMPLATE_DIR / "kosmo-drizzle" / "SKILL.md")


def _generate_nextjs_skill_md() -> str:
    """Genera la skill kosmo-nextjs para App Router, React 19 y Server Components."""
    return _read_template(_SKILLS_TEMPLATE_DIR / "kosmo-nextjs" / "SKILL.md")


def _generate_ui_skill_md() -> str:
    """Genera la skill kosmo-ui: UI funcional, navegación y diseño consistente."""
    return _read_template(_SKILLS_TEMPLATE_DIR / "kosmo-ui" / "SKILL.md")


def _generate_opencode_json(
    project_id: ProjectId,
    workspace_dir: str,
    mcp_url: str = "http://127.0.0.1:8000/mcp",
) -> str:
    """Genera la configuración de opencode.json para el workspace de implementación."""
    config = {
        "$schema": "https://opencode.ai/config.json",
        "instructions": ["AGENTS.md"],
        "plugin": ["@dietrichgebert/ponytail"],
        "mcp": {
            "kosmo-context": {
                "type": "remote",
                "url": mcp_url,
                "environment": {
                    "KOSMO_PROJECT_ID": str(project_id),
                },
            },
            "token-savior": {
                "type": "local",
                "command": ["uvx", "--from", "token-savior-recall", "token-savior"],
                "environment": {
                    "WORKSPACE_ROOTS": workspace_dir,
                    "TOKEN_SAVIOR_CLIENT": "opencode",
                    "TOKEN_SAVIOR_PROFILE": "optimized",
                },
            },
            "context7": {
                "type": "remote",
                "url": "https://mcp.context7.com/mcp",
            },
        },
        "permission": {
            "read": {"*": "allow"},
            "edit": {"*": "allow"},
            "bash": {"*": "allow"},
        },
        # Flujo headless: el agente no debe bloquearse pidiendo aclaraciones al usuario
        "tools": {
            "question": False,
        },
    }
    return json.dumps(config, indent=2) + "\n"


class WorkspaceLockedError(RuntimeError):
    """Lanzada cuando se intenta acceder o bloquear un workspace que ya está bloqueado."""


class LocalWorkspaceManager(WorkspaceManagerPort):
    """Adaptador de infraestructura para la gestión de workspaces locales."""

    def __init__(
        self,
        workspaces_root: Path | str,
        workspace_repo: WorkspaceRepository | None = None,
        template_dir: Path | str | None = None,
        git_init: bool = True,
        mcp_url: str = "http://127.0.0.1:8000/mcp",
        project_repo: ProjectRepository | None = None,
        code_runner: CodeRunnerPort | None = None,
    ) -> None:
        self._workspaces_root = Path(workspaces_root)
        self._workspace_repo = workspace_repo
        self._template_dir = Path(template_dir) if template_dir is not None else DEFAULT_TEMPLATE_DIR
        self._git_init = git_init
        self._mcp_url = mcp_url
        self._project_repo = project_repo
        self._code_runner = code_runner
        self._in_memory_locks: set[str] = set()
        # ponytail: guard global del proceso; la carrera multi-worker se cierra con el
        # CAS (UPDATE condicional) de update_lock en el repositorio SQL.
        self._lock_guard = asyncio.Lock()

    @staticmethod
    def _extract_manifest(workspace_path: Path) -> tuple[str, ...]:
        """Extrae el listado de archivos relativos excluyendo directorios ignorados."""
        if not workspace_path.exists():
            return ()

        files: list[str] = []
        for root, dirs, filenames in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in _IGNORED_DIRS]
            rel_root = Path(root).relative_to(workspace_path)
            for fname in filenames:
                if fname in {".DS_Store", "thumbs.db"}:
                    continue
                rel_path = (rel_root / fname).as_posix()
                if rel_path.startswith("./"):
                    rel_path = rel_path[2:]
                files.append(rel_path)

        return tuple(sorted(files))

    async def ensure_workspace(self, project_id: ProjectId) -> CodeWorkspace:
        """Crea el directorio del workspace si no existe (idempotente) y retorna la entidad."""
        target_dir = (self._workspaces_root / str(project_id)).resolve()
        created_new = False

        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            created_new = True

            if self._template_dir and self._template_dir.exists():
                shutil.copytree(self._template_dir, target_dir, dirs_exist_ok=True)

            if self._git_init:
                with contextlib.suppress(Exception):
                    git_init(target_dir)

        # Generar AGENTS.md y opencode.json si no existen
        agents_file = target_dir / "AGENTS.md"
        if not agents_file.exists():
            project_name = str(project_id)
            if self._project_repo:
                with contextlib.suppress(Exception):
                    proj = await self._project_repo.by_id(project_id)
                    if proj and proj.name:
                        project_name = proj.name
            agents_file.write_text(_generate_agents_md(project_name), encoding="utf-8")

        opencode_file = target_dir / "opencode.json"
        if not opencode_file.exists():
            opencode_file.write_text(
                _generate_opencode_json(project_id, str(target_dir), self._mcp_url),
                encoding="utf-8",
            )

        # Generar las skills en .opencode/skills si no existen
        skills_dir = target_dir / ".opencode" / "skills"
        skills_map = {
            "kosmo-implementation": _generate_implementation_skill_md(),
            "kosmo-testing": _generate_testing_skill_md(),
            "kosmo-drizzle": _generate_drizzle_skill_md(),
            "kosmo-nextjs": _generate_nextjs_skill_md(),
            "kosmo-ui": _generate_ui_skill_md(),
            "tdd": _generate_tdd_skill_md(),
        }
        for skill_name, skill_content in skills_map.items():
            skill_file = skills_dir / skill_name / "SKILL.md"
            if not skill_file.exists():
                skill_file.parent.mkdir(parents=True, exist_ok=True)
                skill_file.write_text(skill_content, encoding="utf-8")

        if self._git_init and created_new:
            with contextlib.suppress(Exception):
                git_add(target_dir)
                git_commit(target_dir, "chore: initialize workspace template and configurations")

        # Pre-instalar dependencias al crear el workspace para que la primera
        # validación no consuma el timeout de npm install dentro del pipeline.
        if created_new and self._code_runner is not None:
            with contextlib.suppress(Exception):
                install = await self._code_runner.run_command(
                    str(target_dir),
                    INSTALL_COMMAND,
                    timeout_seconds=INSTALL_TIMEOUT_SECONDS,
                )
                if not install.success:
                    _log.warning(
                        "workspace.npm_install_failed",
                        project_id=str(project_id),
                        exit_code=install.exit_code,
                    )

        manifest = self._extract_manifest(target_dir)
        now = datetime.now(UTC)

        if self._workspace_repo:
            existing = await self._workspace_repo.by_project_id(project_id)
            if existing is not None and not created_new:
                return dataclasses.replace(existing, manifest_files=manifest)

            ws = CodeWorkspace(
                id=WorkspaceId(f"ws_{project_id}"),
                project_id=project_id,
                status=WorkspaceStatus.READY,
                workspace_dir=str(target_dir),
                manifest_files=manifest,
                current_branch="main",
                is_locked=str(project_id) in self._in_memory_locks,
                created_at=now,
                updated_at=now,
            )
            await self._workspace_repo.save(ws)
            return ws

        return CodeWorkspace(
            id=WorkspaceId(f"ws_{project_id}"),
            project_id=project_id,
            status=WorkspaceStatus.READY,
            workspace_dir=str(target_dir),
            manifest_files=manifest,
            current_branch="main",
            is_locked=str(project_id) in self._in_memory_locks,
            created_at=now,
            updated_at=now,
        )

    async def get_workspace(self, project_id: ProjectId) -> CodeWorkspace | None:
        """Obtiene la información del workspace si existe."""
        if self._workspace_repo:
            ws = await self._workspace_repo.by_project_id(project_id)
            if ws is not None:
                if ws.workspace_dir and Path(ws.workspace_dir).exists():
                    manifest = self._extract_manifest(Path(ws.workspace_dir))
                    return dataclasses.replace(ws, manifest_files=manifest)
                return ws

        target_dir = (self._workspaces_root / str(project_id)).resolve()
        if target_dir.exists():
            manifest = self._extract_manifest(target_dir)
            now = datetime.now(UTC)
            return CodeWorkspace(
                id=WorkspaceId(f"ws_{project_id}"),
                project_id=project_id,
                status=WorkspaceStatus.READY,
                workspace_dir=str(target_dir),
                manifest_files=manifest,
                current_branch="main",
                is_locked=str(project_id) in self._in_memory_locks,
                created_at=now,
                updated_at=now,
            )

        return None

    async def get_manifest(self, workspace: CodeWorkspace) -> tuple[str, ...]:
        """Retorna el manifiesto de archivos actual del workspace."""
        if not workspace.workspace_dir:
            return ()
        return self._extract_manifest(Path(workspace.workspace_dir))

    async def is_locked(self, project_id: ProjectId) -> bool:
        """Verifica si el workspace está bloqueado."""
        if self._workspace_repo:
            ws = await self._workspace_repo.by_project_id(project_id)
            if ws is not None and ws.is_locked:
                return True
        return str(project_id) in self._in_memory_locks

    async def acquire_lock(self, project_id: ProjectId) -> None:
        """Adquiere el bloqueo para un proyecto o lanza WorkspaceLockedError."""
        async with self._lock_guard:
            if str(project_id) in self._in_memory_locks:
                raise WorkspaceLockedError(
                    f"Workspace for project '{project_id}' is currently locked by another process."
                )
            if self._workspace_repo:
                updated = await self._workspace_repo.update_lock(project_id, is_locked=True)
                if updated is None:
                    # El CAS/INSERT de la DB decidió que otro proceso tiene el lock
                    raise WorkspaceLockedError(
                        f"Workspace for project '{project_id}' is currently locked by another process."
                    )
            self._in_memory_locks.add(str(project_id))

    async def release_lock(self, project_id: ProjectId) -> None:
        """Libera el bloqueo para un proyecto."""
        async with self._lock_guard:
            self._in_memory_locks.discard(str(project_id))
            if self._workspace_repo:
                await self._workspace_repo.release_lock(project_id)

    async def rollback_workspace(self, project_id: ProjectId) -> None:
        """Revierte el workspace al último commit exitoso y limpia archivos no rastreados."""
        target_dir = (self._workspaces_root / str(project_id)).resolve()
        if not target_dir.exists():
            return

        git_rollback(target_dir)

        manifest = self._extract_manifest(target_dir)
        if self._workspace_repo:
            ws = await self._workspace_repo.by_project_id(project_id)
            if ws is not None:
                updated = dataclasses.replace(ws, manifest_files=manifest, updated_at=datetime.now(UTC))
                await self._workspace_repo.save(updated)

    async def commit_workspace(self, project_id: ProjectId, message: str) -> bool:
        """Consolida los cambios del workspace en un commit de git y actualiza el manifiesto."""
        target_dir = (self._workspaces_root / str(project_id)).resolve()
        if not target_dir.exists():
            return False

        git_add(target_dir)
        committed = git_commit(target_dir, message)

        manifest = self._extract_manifest(target_dir)
        if self._workspace_repo:
            ws = await self._workspace_repo.by_project_id(project_id)
            if ws is not None:
                updated = dataclasses.replace(ws, manifest_files=manifest, updated_at=datetime.now(UTC))
                await self._workspace_repo.save(updated)

        return committed

    async def publish_preview(self, project_id: ProjectId) -> None:
        """Marca el proyecto como activo para el servicio de preview (un puerto por proyecto).

        El marker vive en `<workspaces_root>/.preview-active/<project_id>` con el directorio
        del workspace como contenido; el servicio preview (docker/preview/run.sh) lo escanea
        y levanta `next dev` por proyecto.
        """
        target_dir = (self._workspaces_root / str(project_id)).resolve()
        markers_dir = self._workspaces_root / ".preview-active"
        markers_dir.mkdir(parents=True, exist_ok=True)
        (markers_dir / str(project_id)).write_text(str(target_dir), encoding="utf-8")
