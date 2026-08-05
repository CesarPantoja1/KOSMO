from __future__ import annotations

import pytest

from kosmo.contracts import ArtefactoAfectado, DiffCambio, EstadoPlanCambio, PlanCambio, ReporteConsistencia
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ids import PlanChangeId


@pytest.mark.unit
def test_artefacto_afectado_creation() -> None:
    # Arrange & Act
    artefacto = ArtefactoAfectado(
        artifact_id="feat_01",
        artifact_type="Feature",
        title="Gestión de usuarios",
        traceability_description="Derivado de la sección Alcance del Descubrimiento",
        suggested_diff=DiffCambio(before="Título viejo", after="Título nuevo"),
        rationale="Ajuste por modificación en Descubrimiento",
    )

    # Assert
    assert artefacto.artifact_id == "feat_01"
    assert artefacto.artifact_type == "Feature"
    assert artefacto.title == "Gestión de usuarios"
    assert artefacto.traceability_description == "Derivado de la sección Alcance del Descubrimiento"
    assert artefacto.suggested_diff.before == "Título viejo"
    assert artefacto.suggested_diff.after == "Título nuevo"
    assert artefacto.rationale == "Ajuste por modificación en Descubrimiento"


@pytest.mark.unit
def test_reporte_consistencia_creation_with_multiple_affected_artifacts() -> None:
    # Arrange
    user_change = PlanCambio(
        id=PlanChangeId("plan_01"),
        section="Alcance",
        description="Modificación del alcance del sistema",
        diff=DiffCambio(before="Alcance 1", after="Alcance 2"),
        status=EstadoPlanCambio.APPLIED,
    )
    feature_artifact = ArtefactoAfectado(
        artifact_id="feat_01",
        artifact_type="Feature",
        title="Gestión de catálogo",
        traceability_description="Derivada de Alcance",
        suggested_diff=DiffCambio(before="Catálogo básico", after="Catálogo avanzado"),
    )
    requirement_artifact = ArtefactoAfectado(
        artifact_id="req_01",
        artifact_type="EARSRequirement",
        title="Validación de timeout",
        traceability_description="Derivado de la Feature 1",
        suggested_diff=DiffCambio(before="30s timeout", after="15s timeout"),
    )

    # Act
    reporte = ReporteConsistencia(
        id="rep_01",
        source_phase=SpecPhase.DESCUBRIMIENTO,
        target_phase=SpecPhase.CARACTERISTICAS,
        user_changes=[user_change],
        affected_artifacts=[feature_artifact, requirement_artifact],
    )

    # Assert
    assert reporte.id == "rep_01"
    assert reporte.source_phase == SpecPhase.DESCUBRIMIENTO
    assert reporte.target_phase == SpecPhase.CARACTERISTICAS
    assert len(reporte.user_changes) == 1
    assert reporte.user_changes[0].status == EstadoPlanCambio.APPLIED
    assert len(reporte.affected_artifacts) == 2
    assert reporte.affected_artifacts[0].artifact_type == "Feature"
    assert reporte.affected_artifacts[1].artifact_type == "EARSRequirement"
    assert reporte.created_at is not None
