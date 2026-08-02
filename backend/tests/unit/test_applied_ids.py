import pytest

from kosmo.application.chat.apply_plan_changes import ApplyPlanChangesOutput, FailedChange
from kosmo.contracts import DiffCambio, EstadoPlanCambio, PlanCambio, PlanChangeId


@pytest.mark.unit
class TestApplyPlanChangesOutput:
    def test_applied_ids_returns_only_applied_change_ids(self) -> None:
        # Arrange
        applied = PlanCambio(
            id=PlanChangeId("chg_001"),
            section="Alcance",
            description="Test",
            diff=DiffCambio(before="old", after="new"),
            status=EstadoPlanCambio.APPLIED,
        )
        failed = FailedChange(id=PlanChangeId("chg_002"), reason="No encontrado")

        # Act
        output = ApplyPlanChangesOutput(
            applied_count=1,
            failed_count=1,
            applied_changes=[applied],
            failed_changes=[failed],
        )

        # Assert
        assert output.applied_ids == ["chg_001"]

    def test_applied_ids_does_not_include_failed_ids(self) -> None:
        # Arrange
        applied = PlanCambio(
            id=PlanChangeId("chg_a"),
            section="Test",
            description="Test",
            diff=DiffCambio(before="a", after="b"),
            status=EstadoPlanCambio.APPLIED,
        )
        failed = FailedChange(id=PlanChangeId("chg_f"), reason="Error")

        # Act
        output = ApplyPlanChangesOutput(
            applied_count=1,
            failed_count=1,
            applied_changes=[applied],
            failed_changes=[failed],
        )

        # Assert
        assert "chg_f" not in output.applied_ids
        assert output.applied_ids == ["chg_a"]

    def test_applied_ids_empty_when_no_applied_changes(self) -> None:
        # Arrange
        failed = FailedChange(id=PlanChangeId("chg_x"), reason="Todo falló")

        # Act
        output = ApplyPlanChangesOutput(
            applied_count=0,
            failed_count=1,
            applied_changes=[],
            failed_changes=[failed],
        )

        # Assert
        assert output.applied_ids == []

    def test_multiple_applied_changes_all_in_ids(self) -> None:
        # Arrange
        c1 = PlanCambio(
            id=PlanChangeId("chg_01"),
            section="A",
            description="A",
            diff=DiffCambio(before="1", after="2"),
            status=EstadoPlanCambio.APPLIED,
        )
        c2 = PlanCambio(
            id=PlanChangeId("chg_02"),
            section="B",
            description="B",
            diff=DiffCambio(before="3", after="4"),
            status=EstadoPlanCambio.APPLIED,
        )

        # Act
        output = ApplyPlanChangesOutput(
            applied_count=2,
            failed_count=0,
            applied_changes=[c1, c2],
            failed_changes=[],
        )

        # Assert
        assert output.applied_ids == ["chg_01", "chg_02"]
        assert output.failed_count == 0
