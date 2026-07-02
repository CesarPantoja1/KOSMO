import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.domain.pipeline.phase_validators.discovery_validator import (
    validate_discovery_quality,
    validate_discovery_structure,
)
from kosmo.domain.sdd.document_converters import markdown_to_document

_VALID_DISCOVERY_MD = (
    "## Visión del producto\n"
    "El producto ayuda a las familias a organizar y repartir gastos compartidos "
    "de forma equitativa y transparente entre todos los participantes del hogar "
    "sin complicaciones adicionales de ningun tipo.\n\n"
    "## Espacio del problema\n"
    "Las familias necesitan llevar un control claro y justo de los gastos compartidos "
    "evitando conflictos por dinero y asegurando transparencia en las cuentas del hogar "
    "porque sin una herramienta adecuada surgen discusiones frecuentes.\n\n"
    "## Actores\n"
    "- **Administrador del hogar:** persona que gestiona los grupos y supervisa que los "
    "balances esten actualizados y correctos para todo el grupo familiar.\n"
    "- **Miembro del hogar:** persona que participa en los gastos compartidos y registra "
    "sus consumos de forma individual y detallada cada mes.\n\n"
    "## Propuesta de valor\n"
    "- **Para el administrador:** control total y visibilidad de las finanzas del hogar "
    "en un solo lugar facilitando la toma de decisiones familiares.\n"
    "- **Para el miembro:** claridad sobre cuanto debe y en que se gasta el dinero "
    "compartido eliminando confusiones entre los integrantes del grupo.\n\n"
    "## Metas del producto\n"
    "1. **Reparto equitativo de gastos:** todo gasto compartido se distribuye entre los "
    "participantes con exactitud y cada quien consulta sus deudas en cualquier momento.\n"
    "2. **Control transparente del hogar:** los saldos del grupo se mantienen "
    "actualizados y consultables para eliminar las discusiones sobre montos pendientes.\n\n"
    "## Reglas de negocio\n"
    "1. Todo gasto debe tener al menos dos participantes para que la distribucion "
    "sea posible dentro del grupo del hogar.\n"
    "2. El monto total distribuido debe ser exactamente igual al monto original del gasto.\n"
    "3. Un participante no puede eliminarse mientras tenga deudas pendientes con otros.\n"
    "4. La moneda del grupo se define al crearlo y no puede modificarse despues.\n\n"
    "## Alcance\n"
    "### Incluido\n"
    "- Registro de gastos compartidos del hogar con detalle de participantes\n"
    "### Excluido\n"
    "- Integracion con bancos y entidades financieras externas\n"
    "- Pagos electronicos y transferencias entre cuentas\n"
    "- Manejo de multiples monedas y conversion de divisas\n"
    "### Futuro potencial\n"
    "- Exportacion a hoja de calculo para analisis avanzado\n"
)


@pytest.mark.unit
def test_validate_discovery_structure_passes_for_seven_sections() -> None:
    # Arrange
    doc = markdown_to_document(_VALID_DISCOVERY_MD)

    # Act
    result = validate_discovery_structure(doc)

    # Assert
    assert result.is_valid is True
    assert result.errors == []


@pytest.mark.unit
def test_validate_discovery_structure_flags_missing_metas_section() -> None:
    # Arrange
    without_metas = _VALID_DISCOVERY_MD.replace("## Metas del producto", "## Otra cosa")
    doc = markdown_to_document(without_metas)

    # Act
    result = validate_discovery_structure(doc)

    # Assert
    assert result.is_valid is False
    assert any("Metas del producto" in e for e in result.errors)


@pytest.mark.unit
def test_validate_discovery_structure_flags_single_goal() -> None:
    # Arrange
    single_goal = _VALID_DISCOVERY_MD.replace(
        "2. **Control transparente del hogar:** los saldos del grupo se mantienen "
        "actualizados y consultables para eliminar las discusiones sobre montos pendientes.\n",
        "",
    )
    doc = markdown_to_document(single_goal)

    # Act
    result = validate_discovery_structure(doc)

    # Assert
    assert result.is_valid is False
    assert any("metas" in e.lower() for e in result.errors)


@pytest.mark.unit
def test_validate_discovery_structure_flags_too_few_rules() -> None:
    # Arrange
    fewer_rules = _VALID_DISCOVERY_MD.replace(
        "4. La moneda del grupo se define al crearlo y no puede modificarse despues.\n",
        "",
    )
    doc = markdown_to_document(fewer_rules)

    # Act
    result = validate_discovery_structure(doc)

    # Assert
    assert result.is_valid is False
    assert any("reglas" in e.lower() for e in result.errors)


@pytest.mark.unit
def test_validate_discovery_structure_flags_too_few_exclusions() -> None:
    # Arrange
    fewer_exclusions = _VALID_DISCOVERY_MD.replace(
        "- Manejo de multiples monedas y conversion de divisas\n",
        "",
    )
    doc = markdown_to_document(fewer_exclusions)

    # Act
    result = validate_discovery_structure(doc)

    # Assert
    assert result.is_valid is False
    assert any("exclusiones" in e.lower() for e in result.errors)


@pytest.mark.unit
def test_validate_discovery_quality_flags_user_story_format() -> None:
    # Arrange
    with_user_story = _VALID_DISCOVERY_MD.replace(
        "1. **Reparto equitativo de gastos:** todo gasto compartido se distribuye entre los "
        "participantes con exactitud y cada quien consulta sus deudas en cualquier momento.\n",
        "1. Como miembro del hogar quiero repartir gastos para evitar conflictos.\n",
    )
    doc = markdown_to_document(with_user_story)

    # Act
    result = validate_discovery_quality(doc)

    # Assert
    assert result.is_valid is False
    assert any("Historia de Usuario" in e for e in result.errors)


@pytest.mark.unit
def test_validate_discovery_quality_passes_for_business_document() -> None:
    # Arrange
    doc = markdown_to_document(_VALID_DISCOVERY_MD)

    # Act
    result = validate_discovery_quality(doc)

    # Assert
    assert result.is_valid is True
    assert result.errors == []
