from __future__ import annotations

import base64
import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog

from kosmo.contracts.ai.chat import ChatRepository
from kosmo.contracts.ai.consistency import (
    ConsistencyEvaluationRepository,
    TraceabilityRepository,
)
from kosmo.contracts.auth.secrets import EncryptedSecret, SecretCipher
from kosmo.contracts.integrations.deployment import (
    DeploymentProvider,
    DeploymentProviderPort,
    DeploymentWorkerPort,
    ProjectDeploymentRepository,
    UserDeploymentIntegration,
    UserDeploymentIntegrationRepository,
)
from kosmo.contracts.integrations.github import (
    GitHubClientPort,
    ProjectGitHubIntegrationRepository,
    UserGitHubIntegrationRepository,
)
from kosmo.contracts.memory.agent_memory import AgentMemoryPort
from kosmo.contracts.sdd.codegen import WorkspaceManagerPort
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.sdd.repositories import (
    ActivityDiagramRepository,
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)

_log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class DeleteProjectInput:
    project_id: ProjectId
    owner_id: UserId


class DeleteProjectUseCase:
    """Caso de uso: elimina un proyecto y todos sus artefactos en cascada.

    Descubrimiento, versiones, características, requisitos, modelos, chat,
    evaluaciones de consistencia, sesiones de agente, trazabilidad, workspace,
    despliegue en la nube (Railway) y repositorio remoto en GitHub.
    """

    def __init__(
        self,
        project_repo: ProjectRepository,
        feature_repo: FeatureRepository,
        requirement_repo: RequirementRepository,
        diagram_repo: ActivityDiagramRepository,
        document_repo: DocumentRepository,
        chat_repo: ChatRepository,
        consistency_evaluation_repo: ConsistencyEvaluationRepository,
        traceability_repo: TraceabilityRepository | None = None,
        agent_memory: AgentMemoryPort | None = None,
        workspace_manager: WorkspaceManagerPort | None = None,
        project_github_repo: ProjectGitHubIntegrationRepository | None = None,
        user_github_repo: UserGitHubIntegrationRepository | None = None,
        github_client: GitHubClientPort | None = None,
        project_deployment_repo: ProjectDeploymentRepository | None = None,
        user_deployment_repo: UserDeploymentIntegrationRepository | None = None,
        deployment_client: DeploymentProviderPort | None = None,
        deployment_worker: DeploymentWorkerPort | None = None,
        cipher: SecretCipher | None = None,
    ) -> None:
        self._project_repo = project_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._diagram_repo = diagram_repo
        self._document_repo = document_repo
        self._chat_repo = chat_repo
        self._consistency_evaluation_repo = consistency_evaluation_repo
        self._traceability_repo = traceability_repo
        self._agent_memory = agent_memory
        self._workspace_manager = workspace_manager
        self._project_github_repo = project_github_repo
        self._user_github_repo = user_github_repo
        self._github_client = github_client
        self._project_deployment_repo = project_deployment_repo
        self._user_deployment_repo = user_deployment_repo
        self._deployment_client = deployment_client
        self._deployment_worker = deployment_worker
        self._cipher = cipher

    async def execute(self, input_data: DeleteProjectInput) -> None:
        project = await self._project_repo.by_id(input_data.project_id)
        if project is None or str(project.owner_id) != str(input_data.owner_id):
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}",
            )

        if self._deployment_worker is not None:
            try:
                self._deployment_worker.cancel_monitoring(input_data.project_id)
            except Exception:
                _log.warning(
                    "delete_project.cancel_monitoring_failed",
                    project_id=str(input_data.project_id),
                    exc_info=True,
                )

        await self._cleanup_railway_deployment(input_data.project_id, input_data.owner_id)
        await self._cleanup_github_repository(input_data.project_id, input_data.owner_id)

        if self._workspace_manager is not None:
            try:
                await self._workspace_manager.delete_workspace(input_data.project_id)
            except Exception:
                _log.warning(
                    "delete_project.workspace_cleanup_failed",
                    project_id=str(input_data.project_id),
                    exc_info=True,
                )

        features = await self._feature_repo.list_by_project(input_data.project_id)
        for feature in features:
            await self._requirement_repo.delete(feature.id)
            await self._diagram_repo.delete(feature.id)
            await self._delete_traceability(str(feature.id))
            await self._feature_repo.delete(feature.id)

        await self._delete_traceability(str(input_data.project_id))

        await self._document_repo.delete_discovery(input_data.project_id)
        await self._document_repo.delete_versions_by_project(input_data.project_id)
        await self._chat_repo.delete_by_project(input_data.project_id)
        await self._consistency_evaluation_repo.delete_by_project(input_data.project_id)

        if self._agent_memory is not None:
            await self._agent_memory.delete_by_project(input_data.project_id)

        await self._project_repo.delete(input_data.project_id)

        _log.info(
            "delete_project.success",
            project_id=str(input_data.project_id),
            feature_count=len(features),
        )

    async def _cleanup_railway_deployment(self, project_id: ProjectId, owner_id: UserId) -> None:
        if self._project_deployment_repo is None:
            return
        try:
            deployment = await self._project_deployment_repo.get_by_project_id(project_id)
            if (
                deployment is not None
                and deployment.service_id
                and self._user_deployment_repo is not None
                and self._deployment_client is not None
                and self._cipher is not None
            ):
                user_integration = await self._user_deployment_repo.get_by_user_id(owner_id, DeploymentProvider.RAILWAY)
                if user_integration is not None and user_integration.encrypted_token:
                    raw_bytes = base64.b64decode(user_integration.encrypted_token.encode("utf-8"))
                    token = self._cipher.decrypt(EncryptedSecret(ciphertext=raw_bytes)).decode("utf-8")
                    try:
                        await self._deployment_client.delete_service(token, deployment.service_id)
                        _log.info(
                            "delete_project.railway_deployment_deleted",
                            project_id=str(project_id),
                            service_id=deployment.service_id,
                        )
                    except Exception:
                        if user_integration.encrypted_refresh_token:
                            try:
                                raw_rt = base64.b64decode(user_integration.encrypted_refresh_token.encode("utf-8"))
                                rt = self._cipher.decrypt(EncryptedSecret(ciphertext=raw_rt)).decode("utf-8")
                                new_dto = await self._deployment_client.refresh_access_token(rt)
                                if new_dto.access_token:
                                    token = new_dto.access_token
                                    enc_acc = base64.b64encode(
                                        self._cipher.encrypt(token.encode("utf-8")).ciphertext
                                    ).decode("utf-8")
                                    enc_ref = user_integration.encrypted_refresh_token
                                    if new_dto.refresh_token:
                                        enc_ref = base64.b64encode(
                                            self._cipher.encrypt(new_dto.refresh_token.encode("utf-8")).ciphertext
                                        ).decode("utf-8")
                                    await self._user_deployment_repo.save(
                                        UserDeploymentIntegration(
                                            user_id=user_integration.user_id,
                                            provider=user_integration.provider,
                                            encrypted_token=enc_acc,
                                            provider_username=user_integration.provider_username,
                                            encrypted_refresh_token=enc_ref,
                                            scopes=user_integration.scopes,
                                            updated_at=datetime.now(UTC),
                                        )
                                    )
                                    await self._deployment_client.delete_service(token, deployment.service_id)
                                    _log.info(
                                        "delete_project.railway_deployment_deleted",
                                        project_id=str(project_id),
                                        service_id=deployment.service_id,
                                    )
                            except Exception:
                                _log.warning(
                                    "delete_project.railway_cleanup_failed",
                                    project_id=str(project_id),
                                    exc_info=True,
                                )
                        else:
                            _log.warning(
                                "delete_project.railway_cleanup_failed",
                                project_id=str(project_id),
                                exc_info=True,
                            )
        except Exception:
            _log.warning(
                "delete_project.railway_cleanup_failed",
                project_id=str(project_id),
                exc_info=True,
            )
        finally:
            with contextlib.suppress(Exception):
                await self._project_deployment_repo.delete_by_project_id(project_id)

    async def _cleanup_github_repository(self, project_id: ProjectId, owner_id: UserId) -> None:
        if self._project_github_repo is None:
            return
        try:
            integration = await self._project_github_repo.get_by_project_id(project_id)
            if (
                integration is not None
                and (integration.repo_name or integration.repo_url)
                and self._user_github_repo is not None
                and self._github_client is not None
                and self._cipher is not None
            ):
                user_github = await self._user_github_repo.get_by_user_id(owner_id)
                if user_github is not None and user_github.encrypted_token:
                    raw_bytes = base64.b64decode(user_github.encrypted_token.encode("utf-8"))
                    token = self._cipher.decrypt(EncryptedSecret(ciphertext=raw_bytes)).decode("utf-8")

                    owner = user_github.github_username
                    repo_name = integration.repo_name
                    if not repo_name and integration.repo_url:
                        cleaned = integration.repo_url.rstrip("/").removesuffix(".git")
                        parts = cleaned.split("/")
                        if len(parts) >= 2:
                            if not owner:
                                owner = parts[-2]
                            repo_name = parts[-1]

                    if owner and repo_name:
                        try:
                            await self._github_client.delete_repository(token, owner, repo_name)
                            _log.info(
                                "delete_project.github_repo_deleted",
                                project_id=str(project_id),
                                owner=owner,
                                repo_name=repo_name,
                            )
                        except Exception:
                            _log.warning(
                                "delete_project.github_cleanup_failed",
                                project_id=str(project_id),
                                exc_info=True,
                            )
        except Exception:
            _log.warning(
                "delete_project.github_cleanup_failed",
                project_id=str(project_id),
                exc_info=True,
            )
        finally:
            with contextlib.suppress(Exception):
                await self._project_github_repo.delete_by_project_id(project_id)

    async def _delete_traceability(self, entity_id: str) -> None:
        if self._traceability_repo is None:
            return
        try:
            await self._traceability_repo.delete_by_entity_id(entity_id)
        except Exception:
            _log.warning(
                "delete_project.traceability_cleanup_failed",
                entity_id=entity_id,
                exc_info=True,
            )
