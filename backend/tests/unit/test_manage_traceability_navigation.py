import pytest
from ulid import ULID

from kosmo.application.traceability.manage_traceability_navigation import (
    ManageTraceabilityNavigationUseCase,
    TraceabilityNavigationInput,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import FeatureNotFoundError
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from tests.unit.fakes import InMemoryFeatureRepository


@pytest.fixture
def feature_repo() -> InMemoryFeatureRepository:
    return InMemoryFeatureRepository()


@pytest.fixture
def use_case(feature_repo: InMemoryFeatureRepository) -> ManageTraceabilityNavigationUseCase:
    return ManageTraceabilityNavigationUseCase(feature_repo=feature_repo)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_manage_traceability_navigation_permitted_at_discovery_level(
    use_case: ManageTraceabilityNavigationUseCase,
) -> None:
    # Arrange
    input_data = TraceabilityNavigationInput(
        entity_id=str(ULID()),
        level=SpecPhase.DESCUBRIMIENTO,
    )

    # Act
    result = await use_case.execute(input_data)

    # Assert
    assert result.permitted is True
    assert result.redirect_message is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_manage_traceability_navigation_permitted_at_features_level(
    use_case: ManageTraceabilityNavigationUseCase,
) -> None:
    # Arrange
    input_data = TraceabilityNavigationInput(
        entity_id=str(ULID()),
        level=SpecPhase.CARACTERISTICAS,
    )

    # Act
    result = await use_case.execute(input_data)

    # Assert
    assert result.permitted is True
    assert result.redirect_message is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_manage_traceability_navigation_redirects_at_requirements_level(
    use_case: ManageTraceabilityNavigationUseCase,
    feature_repo: InMemoryFeatureRepository,
) -> None:
    # Arrange
    project_id = ProjectId(ULID().hex)
    feature = Feature(
        id=FeatureId(ULID().hex),
        project_id=project_id,
        number=1,
        title="Registrar gastos",
        slug="registrar-gastos",
        description="Feature de prueba",
    )
    await feature_repo.save(feature)

    input_data = TraceabilityNavigationInput(
        entity_id=str(feature.id),
        level=SpecPhase.REQUISITOS,
    )

    # Act
    result = await use_case.execute(input_data)

    # Assert
    assert result.permitted is False
    assert result.redirect_message is not None
    assert "Registrar gastos" in result.redirect_message
    assert result.source_entity_name == "Registrar gastos"
    assert result.source_entity_id == str(feature.id)
    assert result.source_level == SpecPhase.CARACTERISTICAS.value


@pytest.mark.asyncio
@pytest.mark.unit
async def test_manage_traceability_navigation_redirects_at_model_level(
    use_case: ManageTraceabilityNavigationUseCase,
    feature_repo: InMemoryFeatureRepository,
) -> None:
    # Arrange
    project_id = ProjectId(ULID().hex)
    feature = Feature(
        id=FeatureId(ULID().hex),
        project_id=project_id,
        number=2,
        title="Calcular balances",
        slug="calcular-balances",
        description="Feature de prueba",
    )
    await feature_repo.save(feature)

    input_data = TraceabilityNavigationInput(
        entity_id=str(feature.id),
        level=SpecPhase.MODELO,
    )

    # Act
    result = await use_case.execute(input_data)

    # Assert
    assert result.permitted is False
    assert result.redirect_message is not None
    assert "Calcular balances" in result.redirect_message
    assert result.source_entity_name == "Calcular balances"
    assert result.source_level == SpecPhase.REQUISITOS.value


@pytest.mark.asyncio
@pytest.mark.unit
async def test_manage_traceability_navigation_raises_when_feature_not_found(
    use_case: ManageTraceabilityNavigationUseCase,
) -> None:
    # Arrange
    missing_id = FeatureId(ULID().hex)
    input_data = TraceabilityNavigationInput(
        entity_id=str(missing_id),
        level=SpecPhase.REQUISITOS,
    )

    # Act & Assert
    with pytest.raises(FeatureNotFoundError) as exc_info:
        await use_case.execute(input_data)

    assert exc_info.value.problem.status == 404
    assert str(missing_id) in exc_info.value.problem.detail


@pytest.mark.asyncio
@pytest.mark.unit
async def test_manage_traceability_navigation_redirects_at_implementation_level(
    use_case: ManageTraceabilityNavigationUseCase,
    feature_repo: InMemoryFeatureRepository,
) -> None:
    # Arrange
    project_id = ProjectId(ULID().hex)
    feature = Feature(
        id=FeatureId(ULID().hex),
        project_id=project_id,
        number=3,
        title="Exportar reportes",
        slug="exportar-reportes",
        description="Feature de prueba",
    )
    await feature_repo.save(feature)

    input_data = TraceabilityNavigationInput(
        entity_id=str(feature.id),
        level=SpecPhase.IMPLEMENTACION,
    )

    # Act
    result = await use_case.execute(input_data)

    # Assert
    assert result.permitted is False
    assert result.redirect_message is not None
    assert "Exportar reportes" in result.redirect_message
    assert result.source_entity_name == "Exportar reportes"
    assert result.source_level == SpecPhase.MODELO.value
