import base64
from dataclasses import dataclass, replace

from kosmo.contracts.auth.secrets import EncryptedSecret, SecretCipher
from kosmo.contracts.integrations.git import GitWorkspacePort
from kosmo.contracts.integrations.github import (
    CodeSyncLog,
    CodeSyncLogRepository,
    CodeSyncStatus,
    GitHubClientPort,
    GitHubSyncStatus,
    ProjectGitHubIntegrationRepository,
    UserGitHubIntegrationRepository,
)
from kosmo.contracts.sdd.codegen import WorkspaceManagerPort
from kosmo.contracts.sdd.ids import ProjectId, UserId


@dataclass(frozen=True, slots=True)
class SyncGitHubRepositoryCommand:
    project_id: ProjectId


class SyncGitHubRepositoryUseCase:
    def __init__(
        self,
        project_github_repo: ProjectGitHubIntegrationRepository,
        user_github_repo: UserGitHubIntegrationRepository,
        github_client: GitHubClientPort,
        git_workspace: GitWorkspacePort,
        workspace_manager: WorkspaceManagerPort,
        cipher: SecretCipher,
        sync_log_repo: CodeSyncLogRepository,
    ) -> None:
        self._project_repo = project_github_repo
        self._user_repo = user_github_repo
        self._github_client = github_client
        self._git_workspace = git_workspace
        self._workspace_manager = workspace_manager
        self._cipher = cipher
        self._sync_log_repo = sync_log_repo

    async def execute(self, cmd: SyncGitHubRepositoryCommand, user_id: UserId) -> None:
        project_integration = await self._project_repo.get_by_project_id(cmd.project_id)
        if not project_integration:
            raise ValueError("El proyecto no tiene una integración configurada con GitHub.")

        workspace = await self._workspace_manager.get_workspace(cmd.project_id)
        if not workspace or not workspace.workspace_dir:
            raise ValueError("No se encontró el directorio físico del workspace para el proyecto.")

        user_integration = await self._user_repo.get_by_user_id(user_id)
        if not user_integration:
            raise ValueError("El usuario no tiene su cuenta vinculada con GitHub.")

        # Desencriptar token
        encrypted_bytes = base64.b64decode(user_integration.encrypted_token)
        decrypted_bytes = self._cipher.decrypt(EncryptedSecret(ciphertext=encrypted_bytes))
        token = decrypted_bytes.decode("utf-8")

        # Marcar como SYNCING
        project_integration = replace(project_integration, sync_status=GitHubSyncStatus.SYNCING)
        await self._project_repo.save(project_integration)

        try:
            # 1. Asegurar repositorio remoto
            user = await self._github_client.get_authenticated_user(token)
            repo_name = project_integration.repo_name or f"project-{cmd.project_id}"

            exists = await self._github_client.check_repository_exists(token, user.login, repo_name)
            if not exists:
                github_repo = await self._github_client.create_repository(
                    token=token,
                    name=repo_name,
                    description=f"Repositorio sincronizado automáticamente desde KOSMO para proyecto {cmd.project_id}",
                    is_private=True,
                )
                repo_url = github_repo.clone_url
            else:
                repo = await self._github_client.get_repository(token, user.login, repo_name)
                if repo is None:
                    raise ValueError(f"No se pudo recuperar el repositorio {repo_name}.")
                repo_url = repo.clone_url

            # Actualizar repo_url en DB
            project_integration = replace(project_integration, repo_url=repo_url, repo_name=repo_name)
            await self._project_repo.save(project_integration)

            # 2. Configurar Git local y pushear
            auth_url = self._git_workspace.build_authenticated_url(repo_url, token)
            self._git_workspace.remote_add_or_update(workspace.workspace_dir, "origin", auth_url)

            commit_hash = self._git_workspace.push(workspace.workspace_dir, "origin")

            # 3. Log y Estado Final (SUCCESS)
            project_integration = replace(
                project_integration,
                sync_status=GitHubSyncStatus.SYNCED,
                last_commit_hash=commit_hash,
            )
            await self._project_repo.save(project_integration)

            log = CodeSyncLog(
                project_id=cmd.project_id,
                status=CodeSyncStatus.SUCCESS,
                commit_sha=commit_hash,
                message=f"Sincronizado correctamente a {repo_url}",
            )
            await self._sync_log_repo.add_log(log)

        except Exception as e:
            # Revertir estado a FAILED
            project_integration = replace(
                project_integration,
                sync_status=GitHubSyncStatus.FAILED,
                error_message=str(e),
            )
            await self._project_repo.save(project_integration)

            log = CodeSyncLog(
                project_id=cmd.project_id,
                status=CodeSyncStatus.FAILED,
                message=str(e),
            )
            await self._sync_log_repo.add_log(log)
            raise
