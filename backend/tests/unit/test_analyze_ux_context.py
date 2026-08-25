from __future__ import annotations

import pytest

from kosmo.application.codegen.analyze_ux_context import (
    UXAnalysisInput,
    UXAnalyzerUseCase,
)
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.ux_context import (
    BusinessArchetype,
    DataDensity,
    ShellPattern,
)
from kosmo.domain.sdd.document_converters import markdown_to_document
from tests.unit.fakes import InMemoryDocumentRepository, InMemoryFeatureRepository


@pytest.mark.asyncio
async def test_analyze_ux_context_dashboard_archetype():
    doc_repo = InMemoryDocumentRepository()
    feat_repo = InMemoryFeatureRepository()

    project_id = ProjectId("proj_dash_01")
    feature_id = FeatureId("feat_01")

    discovery_md = """## Visión del producto
Sistema de control financiero y monitoreo de gastos para operaciones empresariales.

## Espacio del problema
Las empresas no tienen visibilidad de sus métricas y reportes diarios.

## Actores
- **Administrador:** gestiona balances y presupuestos.
- **Auditor:** revisa reportes de control.

## Metas del producto
1. **Control de gastos:** cálculo automático de métricas e indicadores en tiempo real.
2. **Reportes analíticos:** exportación de estadísticas mensuales.
"""
    await doc_repo.save_discovery(project_id, markdown_to_document(discovery_md))
    await feat_repo.save(
        Feature(
            id=feature_id,
            number=1,
            title="Monitoreo de gastos y reportes",
            slug="monitoreo-gastos",
            description="El usuario consulta las métricas y reportes de gastos.",
            project_id=project_id,
        )
    )

    use_case = UXAnalyzerUseCase(document_repo=doc_repo, feature_repo=feat_repo)
    result = await use_case.execute(UXAnalysisInput(feature_id=feature_id, project_id=project_id))

    assert result.ux_context.archetype == BusinessArchetype.DASHBOARD
    assert result.ux_context.shell_pattern == ShellPattern.SIDEBAR
    assert result.ux_context.data_density == DataDensity.HIGH
    assert "Table" in result.ux_context.recommended_components
    assert "Stat" in result.ux_context.recommended_components
    assert "Bootstrap 5" in result.prompt_block
    assert "PROHIBIDO" in result.prompt_block


@pytest.mark.asyncio
async def test_analyze_ux_context_storefront_archetype():
    doc_repo = InMemoryDocumentRepository()
    feat_repo = InMemoryFeatureRepository()

    project_id = ProjectId("proj_store_01")
    feature_id = FeatureId("feat_02")

    discovery_md = """## Visión del producto
Tienda online de productos orgánicos con catálogo interactivo y reservas.

## Actores
- **Cliente:** busca productos en el catálogo y realiza pedidos.

## Metas del producto
1. **Catálogo de ventas:** visualización de productos y precios.
"""
    await doc_repo.save_discovery(project_id, markdown_to_document(discovery_md))
    await feat_repo.save(
        Feature(
            id=feature_id,
            number=2,
            title="Catálogo de productos y compras",
            slug="catalogo-productos",
            description="El usuario explora el inventario de la tienda y agrega productos al pedido.",
            project_id=project_id,
        )
    )

    use_case = UXAnalyzerUseCase(document_repo=doc_repo, feature_repo=feat_repo)
    result = await use_case.execute(UXAnalysisInput(feature_id=feature_id, project_id=project_id))

    assert result.ux_context.archetype == BusinessArchetype.STOREFRONT
    assert result.ux_context.shell_pattern == ShellPattern.TOP_NAV
    assert result.ux_context.data_density == DataDensity.LOW
    assert "Card" in result.ux_context.recommended_components


@pytest.mark.asyncio
async def test_analyze_ux_context_workflow_archetype():
    doc_repo = InMemoryDocumentRepository()
    feat_repo = InMemoryFeatureRepository()

    project_id = ProjectId("proj_wf_01")
    feature_id = FeatureId("feat_03")

    discovery_md = """## Visión del producto
Sistema de gestión de trámites y flujo de aprobaciones para licencias.

## Metas del producto
1. **Flujo de solicitud:** registro paso a paso y seguimiento de estados.
"""
    await doc_repo.save_discovery(project_id, markdown_to_document(discovery_md))
    await feat_repo.save(
        Feature(
            id=feature_id,
            number=3,
            title="Registro de solicitud de trámite",
            slug="registro-tramite",
            description="El usuario llena el proceso por etapas y envía su solicitud para aprobación.",
            project_id=project_id,
        )
    )

    use_case = UXAnalyzerUseCase(document_repo=doc_repo, feature_repo=feat_repo)
    result = await use_case.execute(UXAnalysisInput(feature_id=feature_id, project_id=project_id))

    assert result.ux_context.archetype == BusinessArchetype.WORKFLOW
    assert result.ux_context.shell_pattern == ShellPattern.SIDEBAR
    assert "Steps" in result.ux_context.recommended_components
    assert "BadgeStatus" in result.ux_context.recommended_components
