from __future__ import annotations

import pytest

from kosmo.application.consistency.trigger_downstream import trigger_downstream_evaluation
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import ProjectId
from tests.unit.fakes import InMemoryOutbox


@pytest.mark.unit
@pytest.mark.asyncio
async def test_trigger_downstream_includes_operation_id() -> None:
    # Arrange
    outbox = InMemoryOutbox()

    # Act
    await trigger_downstream_evaluation(
        outbox,
        project_id=ProjectId("prj_01"),
        source_phase=SpecPhase.DESCUBRIMIENTO,
        changes=[{"section": "Alcance", "before": "a", "after": "b"}],
    )

    # Assert
    assert len(outbox.jobs) == 1
    job_type, payload = outbox.jobs[0]
    assert job_type == "consistency_evaluate"
    assert payload["operation_id"].startswith("ope_")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_trigger_downstream_is_noop_without_outbox() -> None:
    # Arrange & Act
    await trigger_downstream_evaluation(
        None,
        project_id=ProjectId("prj_01"),
        source_phase=SpecPhase.DESCUBRIMIENTO,
        changes=[],
    )

    # Assert — no falla ni encola
