from __future__ import annotations

import pytest

from kosmo.application.consistency.trigger_downstream import trigger_downstream_evaluation
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from tests.unit.fakes import InMemoryOutbox


@pytest.mark.unit
@pytest.mark.asyncio
async def test_trigger_downstream_enqueues_consistency_evaluate() -> None:
    # Arrange
    outbox = InMemoryOutbox()
    changes = [{"section": "documento", "before": "", "after": "contenido nuevo"}]

    # Act
    await trigger_downstream_evaluation(
        outbox,
        project_id=ProjectId("prj_01"),
        source_phase=SpecPhase.DESCUBRIMIENTO,
        changes=changes,
    )

    # Assert
    assert len(outbox.jobs) == 1
    job_type, payload = outbox.jobs[0]
    assert job_type == "consistency_evaluate"
    assert payload["project_id"] == "prj_01"
    assert payload["source_phase"] == "descubrimiento"
    assert payload["changes"] == changes


@pytest.mark.unit
@pytest.mark.asyncio
async def test_trigger_downstream_is_noop_without_outbox() -> None:
    # Arrange
    changes = [{"section": "documento", "before": "", "after": "contenido nuevo"}]

    # Act & Assert — no debe lanzar excepción
    await trigger_downstream_evaluation(
        None,
        project_id=ProjectId("prj_01"),
        source_phase=SpecPhase.REQUISITOS,
        changes=changes,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_trigger_downstream_is_noop_when_source_has_no_downstream() -> None:
    # Arrange
    outbox = InMemoryOutbox()

    # Act
    await trigger_downstream_evaluation(
        outbox,
        project_id=ProjectId("prj_01"),
        source_phase=SpecPhase.MODELO,
        changes=[{"section": "diagrama", "before": "", "after": "contenido"}],
    )

    # Assert
    assert outbox.jobs == []
