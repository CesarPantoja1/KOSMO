from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from kosmo.application.integrations.execute_ephemeral_validation import (
    EphemeralValidationError,
    ExecuteEphemeralValidationCommand,
    ExecuteEphemeralValidationUseCase,
)
from kosmo.contracts.auth.secrets import EncryptedSecret, SecretCipher
from kosmo.contracts.integrations.git import GitWorkspacePort
from kosmo.contracts.integrations.github import (
    CodeSyncLog,
    CodeSyncLogRepository,
    CodeSyncStatus,
    GitHubClientPort,
    GitHubSyncStatus,
    ProjectGitHubIntegration,
    ProjectGitHubIntegrationRepository,
    UserGitHubIntegrationRepository,
)
from kosmo.contracts.sdd.codegen import WorkspaceManagerPort
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.sdd.repositories import ProjectRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SyncGitHubRepositoryCommand:
    project_id: ProjectId
    project_name: str | None = None
    repo_name: str | None = None
    is_public: bool = False
    commit_message: str | None = None


class SyncGitHubRepositoryUseCase:
    """Orquesta la sincronización (inicial o incremental) del código fuente con GitHub."""

    def __init__(
        self,
        project_github_repo: ProjectGitHubIntegrationRepository,
        user_github_repo: UserGitHubIntegrationRepository,
        github_client: GitHubClientPort,
        git_workspace: GitWorkspacePort,
        workspace_manager: WorkspaceManagerPort,
        cipher: SecretCipher,
        sync_log_repo: CodeSyncLogRepository,
        ephemeral_validator: ExecuteEphemeralValidationUseCase | None = None,
        project_repo: ProjectRepository | None = None,
    ) -> None:
        self._project_repo = project_github_repo
        self._user_repo = user_github_repo
        self._github_client = github_client
        self._git_workspace = git_workspace
        self._workspace_manager = workspace_manager
        self._cipher = cipher
        self._sync_log_repo = sync_log_repo
        self._ephemeral_validator = ephemeral_validator
        self._sdd_project_repo = project_repo

    async def execute(
        self,
        cmd: SyncGitHubRepositoryCommand,
        user_id: UserId,
    ) -> ProjectGitHubIntegration:
        user_integration = await self._user_repo.get_by_user_id(user_id)
        if not user_integration:
            raise ValueError("El usuario no tiene su cuenta vinculada con GitHub.")

        workspace = await self._workspace_manager.ensure_workspace(cmd.project_id)
        if not workspace or not workspace.workspace_dir:
            raise ValueError("No se encontró el directorio físico del workspace para el proyecto.")

        project_integration = await self._project_repo.get_by_project_id(cmd.project_id)
        if project_integration is None:
            project_integration = ProjectGitHubIntegration(
                project_id=cmd.project_id,
                repo_name=cmd.repo_name,
                is_public=cmd.is_public,
                sync_status=GitHubSyncStatus.NOT_CREATED,
            )

        # Desencriptar token
        encrypted_bytes = base64.b64decode(user_integration.encrypted_token)
        decrypted_bytes = self._cipher.decrypt(EncryptedSecret(ciphertext=encrypted_bytes))
        token = decrypted_bytes.decode("utf-8")

        # Marcar como SYNCING
        now = datetime.now(UTC)
        project_integration = replace(
            project_integration,
            sync_status=GitHubSyncStatus.SYNCING,
            updated_at=now,
        )
        await self._project_repo.save(project_integration)

        try:
            # Determinar si es sincronización incremental o creación inicial
            is_incremental = bool(
                project_integration.repo_url and project_integration.sync_status != GitHubSyncStatus.NOT_CREATED
            )

            if is_incremental:
                repo_url = project_integration.repo_url
                repo_name = project_integration.repo_name or f"project-{cmd.project_id}"
            else:
                user = await self._github_client.get_authenticated_user(token)
                repo_name = cmd.repo_name or project_integration.repo_name or f"project-{cmd.project_id}"
                is_public = cmd.is_public or project_integration.is_public

                exists = await self._github_client.check_repository_exists(token, user.login, repo_name)
                if not exists:
                    project_display = cmd.project_name
                    if not project_display and self._sdd_project_repo is not None:
                        proj = await self._sdd_project_repo.by_id(cmd.project_id)
                        if proj is not None and proj.name:
                            project_display = proj.name
                    project_display = project_display or str(cmd.project_id)

                    github_repo = await self._github_client.create_repository(
                        token=token,
                        name=repo_name,
                        description=(
                            f"Repositorio sincronizado automáticamente desde KOSMO para proyecto {project_display}"
                        ),
                        is_private=not is_public,
                    )
                    repo_url = github_repo.clone_url
                    if github_repo.id:
                        try:
                            await self._github_client.grant_app_installation_access(token, github_repo.id)
                        except Exception as exc:
                            logger.debug("No se pudo otorgar acceso a Railway para nuevo repositorio: %s", exc)
                else:
                    repo = await self._github_client.get_repository(token, user.login, repo_name)
                    if repo is None:
                        raise ValueError(f"No se pudo recuperar el repositorio {repo_name}.")
                    repo_url = repo.clone_url
                    if repo.id:
                        try:
                            await self._github_client.grant_app_installation_access(token, repo.id)
                        except Exception as exc:
                            logger.debug("No se pudo otorgar acceso a Railway para repositorio existente: %s", exc)

                project_integration = replace(
                    project_integration,
                    repo_url=repo_url,
                    repo_name=repo_name,
                    is_public=is_public,
                )
                await self._project_repo.save(project_integration)

            # Validación previa en contenedor efímero si se proveyó validador
            if self._ephemeral_validator is not None:
                val_res = await self._ephemeral_validator.execute(
                    ExecuteEphemeralValidationCommand(
                        workspace_path=workspace.workspace_dir,
                        project_id=cmd.project_id,
                    )
                )
                if not val_res.is_valid:
                    error_msg = (
                        f"Validación efímera fallida en el paso '{val_res.failed_step}': "
                        f"{'; '.join(val_res.error_summary)}"
                    )
                    raise EphemeralValidationError(error_msg, step=val_res.failed_step, errors=val_res.error_summary)

            # La URL persistida del remoto nunca debe contener el token OAuth.
            # El adaptador usa el token exclusivamente para este push.
            self._git_workspace.remote_add_or_update(workspace.workspace_dir, "origin", repo_url)

            branch = project_integration.default_branch or "main"
            commit_hash = self._git_workspace.push(
                workspace.workspace_dir,
                "origin",
                branch=branch,
                token=token,
            )

            # Log y Estado Final (SUCCESS)
            push_time = datetime.now(UTC)
            project_integration = replace(
                project_integration,
                repo_url=repo_url,
                repo_name=repo_name,
                sync_status=GitHubSyncStatus.SYNCED,
                last_commit_hash=commit_hash,
                last_push_at=push_time,
                last_synced_at=push_time,
                error_message=None,
                updated_at=push_time,
            )
            saved_integration = await self._project_repo.save(project_integration)

            log = CodeSyncLog(
                project_id=cmd.project_id,
                status=CodeSyncStatus.SUCCESS,
                commit_sha=commit_hash,
                message=f"Sincronizado correctamente a {repo_url}",
                synced_at=push_time,
            )
            await self._sync_log_repo.add_log(log)

            return saved_integration

        except Exception as e:
            fail_time = datetime.now(UTC)
            project_integration = replace(
                project_integration,
                sync_status=GitHubSyncStatus.FAILED,
                error_message=str(e),
                updated_at=fail_time,
            )
            await self._project_repo.save(project_integration)

            log = CodeSyncLog(
                project_id=cmd.project_id,
                status=CodeSyncStatus.FAILED,
                message=str(e),
                synced_at=fail_time,
            )
            await self._sync_log_repo.add_log(log)
            raise
