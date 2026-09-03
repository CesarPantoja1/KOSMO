from dataclasses import dataclass, replace

from kosmo.contracts.integrations.deployment import (
    DeploymentProvider,
    DeploymentStatus,
    ProjectDeployment,
    ProjectDeploymentRepository,
)
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.telemetry import traced


@dataclass(frozen=True, slots=True)
class HandleDeploymentFailureCommand:
    project_id: ProjectId
    error_message: str
    build_logs_url: str | None = None
    provider: DeploymentProvider = DeploymentProvider.RAILWAY


class HandleDeploymentFailureUseCase:
    """Caso de uso para registrar formalmente un fallo en la inicialización o ciclo de despliegue."""

    def __init__(self, project_deployment_repo: ProjectDeploymentRepository) -> None:
        self._project_deployment_repo = project_deployment_repo

    @traced("deployment.handle_failure")
    async def execute(self, cmd: HandleDeploymentFailureCommand) -> ProjectDeployment:
        deployment = await self._project_deployment_repo.get_by_project_id(cmd.project_id)
        if not deployment:
            # Crea uno dummy para registrar que al menos falló al crearse de forma temprana
            deployment = ProjectDeployment(
                project_id=cmd.project_id,
                provider=cmd.provider,
                status=DeploymentStatus.FAILED,
                error_message=cmd.error_message,
                build_logs_url=cmd.build_logs_url,
            )
        else:
            deployment = replace(
                deployment,
                status=DeploymentStatus.FAILED,
                error_message=cmd.error_message,
                build_logs_url=cmd.build_logs_url or deployment.build_logs_url,
            )

        await self._project_deployment_repo.save(deployment)
        return deployment
