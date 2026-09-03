from __future__ import annotations

import logging

from kosmo.contracts.integrations.deployment import (
    DeploymentStatus,
    DeploymentWorkerPort,
    ProjectDeploymentRepository,
)
from kosmo.contracts.sdd.repositories import ProjectRepository

logger = logging.getLogger(__name__)


async def recover_pending_deployments(
    *,
    project_deployment_repo: ProjectDeploymentRepository,
    project_repo: ProjectRepository,
    deployment_worker: DeploymentWorkerPort,
) -> int:
    """Vuelve a iniciar el sondeo de despliegues que seguían en curso tras un reinicio.

    El estado de Railway y el identificador de servicio ya están persistidos; solo la tarea
    de ``asyncio`` se pierde cuando el proceso API se reinicia.
    """
    resumed = 0
    pending_deployments = await project_deployment_repo.list_by_status(DeploymentStatus.BUILDING)

    for deployment in pending_deployments:
        if not deployment.service_id:
            logger.warning(
                "No se recupera el despliegue de %s: no tiene service_id.",
                deployment.project_id,
            )
            continue

        project = await project_repo.by_id(deployment.project_id)
        if project is None:
            logger.warning(
                "No se recupera el despliegue de %s: el proyecto ya no existe.",
                deployment.project_id,
            )
            continue

        deployment_worker.start_monitoring(
            project_id=deployment.project_id,
            user_id=project.owner_id,
            provider=deployment.provider,
        )
        resumed += 1

    return resumed
