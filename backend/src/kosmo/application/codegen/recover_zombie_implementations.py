from __future__ import annotations

import contextlib
from dataclasses import replace
from datetime import UTC, datetime

import structlog

from kosmo.contracts.sdd.codegen import (
    FeatureImplementationRepository,
    FeatureImplementationStatus,
    OpenCodeClientPort,
    WorkspaceManagerPort,
)

_log = structlog.get_logger("kosmo.codegen.recovery")


async def recover_zombie_implementations(
    implementation_repo: FeatureImplementationRepository,
    opencode_client: OpenCodeClientPort,
    workspace_manager: WorkspaceManagerPort,
) -> int:
    """Marca como FAILED las implementaciones IN_PROGRESS que quedaron huérfanas tras un reinicio.

    Best-effort por implementación: cierra la sesión OpenCode y libera el lock
    del workspace sin que un fallo individual bloquee el resto.
    """
    zombies = await implementation_repo.list_by_status(FeatureImplementationStatus.IN_PROGRESS)
    now = datetime.now(UTC)
    for impl in zombies:
        try:
            if impl.session_id is not None:
                with contextlib.suppress(Exception):
                    await opencode_client.close_session(impl.session_id)
            with contextlib.suppress(Exception):
                await workspace_manager.release_lock(impl.project_id)
            await implementation_repo.save(replace(impl, status=FeatureImplementationStatus.FAILED, updated_at=now))
        except Exception:
            _log.exception(
                "codegen.zombie_recovery_failed",
                implementation_id=str(impl.id),
                feature_id=str(impl.feature_id),
            )
    return len(zombies)
