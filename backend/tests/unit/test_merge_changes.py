from __future__ import annotations

import pytest

from kosmo.contracts.chat import DiffCambio, PlanCambio
from kosmo.contracts.sdd.ids import PlanChangeId
from kosmo.domain.sdd.discovery_diff import ChangeClass, ChangeType, SectionChange
from kosmo.domain.sdd.plan_diffs import merge_changes_with_diffs


def _plan_change(section: str, description: str) -> PlanCambio:
    return PlanCambio(
        id=PlanChangeId("chg_01"),
        section=section,
        description=description,
        diff=DiffCambio(before="antes", after="después"),
    )


@pytest.mark.unit
def test_merge_reuses_description_when_section_matches() -> None:
    # Arrange
    originals = [_plan_change("Alcance", "Ampliar el alcance del proyecto")]
    diffs = [
        SectionChange(
            section="Alcance",
            change_type=ChangeType.MODIFIED,
            change_class=ChangeClass.SEMANTIC,
            before="a",
            after="b",
        )
    ]

    # Act
    merged = merge_changes_with_diffs(originals, diffs)

    # Assert
    assert len(merged) == 1
    assert merged[0].section == "Alcance"
    assert merged[0].description == "Ampliar el alcance del proyecto"
    assert merged[0].diff.before == "a"
    assert merged[0].diff.after == "b"


@pytest.mark.unit
def test_merge_matches_description_by_fuzzy_section_containment() -> None:
    # Arrange
    originals = [_plan_change("Alcance del proyecto", "Descripción reutilizable")]
    diffs = [
        SectionChange(
            section="Alcance",
            change_type=ChangeType.MODIFIED,
            change_class=ChangeClass.SEMANTIC,
        )
    ]

    # Act
    merged = merge_changes_with_diffs(originals, diffs)

    # Assert
    assert merged[0].description == "Descripción reutilizable"


@pytest.mark.unit
def test_merge_builds_default_description_for_added_section() -> None:
    # Arrange
    diffs = [
        SectionChange(
            section="Glosario",
            change_type=ChangeType.ADDED,
            change_class=ChangeClass.STRUCTURAL,
        )
    ]

    # Act
    merged = merge_changes_with_diffs([], diffs)

    # Assert
    assert len(merged) == 1
    assert merged[0].description == "Seccion nueva: Glosario"


@pytest.mark.unit
def test_merge_builds_default_description_for_removed_section() -> None:
    # Arrange
    diffs = [
        SectionChange(
            section="Glosario",
            change_type=ChangeType.REMOVED,
            change_class=ChangeClass.STRUCTURAL,
        )
    ]

    # Act
    merged = merge_changes_with_diffs([], diffs)

    # Assert
    assert merged[0].description == "Seccion eliminada: Glosario"


@pytest.mark.unit
def test_merge_builds_cosmetic_description_when_only_class_is_cosmetic() -> None:
    # Arrange
    diffs = [
        SectionChange(
            section="Visión",
            change_type=ChangeType.MODIFIED,
            change_class=ChangeClass.COSMETIC,
        )
    ]

    # Act
    merged = merge_changes_with_diffs([], diffs)

    # Assert
    assert merged[0].description == "Cambio cosmetico en Visión"


@pytest.mark.unit
def test_merge_builds_modified_description_as_fallback() -> None:
    # Arrange
    diffs = [
        SectionChange(
            section="Visión",
            change_type=ChangeType.MODIFIED,
            change_class=ChangeClass.SEMANTIC,
        )
    ]

    # Act
    merged = merge_changes_with_diffs([], diffs)

    # Assert
    assert merged[0].description == "Seccion modificada: Visión"
    assert str(merged[0].id).startswith("chg_diff_")
