import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.contracts.pipeline.phase_outputs import (
    DiscoveryPhaseOutput,
    EARSPhaseOutput,
    FeaturesPhaseOutput,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.domain.pipeline.phase_modes.discovery_mode import DiscoveryMode
from kosmo.domain.pipeline.phase_modes.discovery_refine_mode import DiscoveryRefineMode
from kosmo.domain.pipeline.phase_modes.ears_mode import EARSMode
from kosmo.domain.pipeline.phase_modes.features_mode import FeaturesMode

_VALID_METADATA = GenerationMetadata(llm_calls=1, total_tokens=10)
_VALID_VALIDATION = ValidationResult(is_valid=True)

_DISCOVERY_MD = (
    "## Vision del producto\n"
    "El producto ayuda a las familias a organizar y repartir gastos compartidos "
    "de forma equitativa y transparente entre todos los participantes del hogar "
    "de manera simple y efectiva sin complicaciones adicionales.\n\n"
    "## Espacio del problema\n"
    "Las familias necesitan llevar un control claro y justo de los gastos compartidos "
    "evitando conflictos por dinero y asegurando transparencia en las cuentas del hogar "
    "sin una herramienta adecuada surgen discusiones y falta de confianza entre los miembros "
    "del grupo familiar.\n\n"
    "## Actores\n"
    "- **Administrador del hogar:** persona que gestiona los grupos y autoriza pagos "
    "y tiene visibilidad completa de las finanzas del grupo familiar.\n"
    "- **Miembro del hogar:** persona que participa en los gastos compartidos y registra "
    "sus consumos de forma individual y detallada.\n\n"
    "## Propuesta de valor\n"
    "- **Para el administrador:** control total y visibilidad de las finanzas del hogar "
    "en un solo lugar facilitando la toma de decisiones sobre el presupuesto familiar.\n"
    "- **Para el miembro:** claridad sobre cuanto debe y en que se gasta el dinero "
    "compartido eliminando confusiones y malentendidos entre los integrantes.\n\n"
    "## Metas del producto\n"
    "1. **Reparto equitativo de gastos:** todo gasto compartido se distribuye entre "
    "los participantes con exactitud y cada quien puede consultar el estado de sus "
    "deudas y acreencias en cualquier momento.\n"
    "2. **Control transparente del hogar:** los saldos del grupo se mantienen "
    "actualizados y consultables para eliminar las discusiones sobre montos "
    "pendientes entre los integrantes.\n\n"
    "## Reglas de negocio\n"
    "1. Todo gasto debe tener al menos un participante asignado para su registro "
    "y contabilizacion en el sistema de gestion.\n"
    "2. El monto del gasto registrado debe ser estrictamente mayor a cero pesos.\n"
    "3. Cada participante debe pertenecer al grupo del hogar configurado previamente "
    "por el administrador del sistema.\n"
    "4. Los saldos se recalculan automaticamente al registrar un nuevo gasto compartido "
    "entre los miembros del hogar registrados.\n\n"
    "## Alcance\n"
    "### Incluido\n"
    "- Registro de gastos compartidos del hogar con detalle de participantes\n"
    "### Excluido\n"
    "- Integracion con bancos y entidades financieras externas\n"
    "- Pagos electronicos y transferencias entre cuentas\n"
    "- Sincronizacion con dispositivos externos y otras aplicaciones\n"
    "- Manejo de multiples monedas y conversion de divisas\n"
    "### Futuro potencial\n"
    "- Exportacion a hoja de calculo para analisis avanzado\n"
)

_FEATURES_JSON = (
    '{"features": ['
    '{"title": "Feature 1", "description": "Descripcion valida", '
    '"number": 1, "rationale": "Justificacion", "inferred_from": ["C01"]}'
    "]}"
)

_EARS_JSON = (
    '{"requirements": ['
    '{"pattern": "ubiquitous", "trigger": "", "system": "El sistema", '
    '"response": "debe gestionar", "source_statement": "shall gestionar", '
    '"rationale": "Fundamental", "traceability": ["C01"], '
    '"acceptance_criteria": ['
    '{"given": "usuario autenticado", "when": "accede", "then": "datos correctos"}'
    "]}]}"
)


@pytest.mark.unit
def test_discovery_mode_build_output_returns_discovery_phase_output() -> None:
    # Arrange
    mode = DiscoveryMode()

    # Act
    result = mode.build_output(_DISCOVERY_MD, _VALID_VALIDATION, _VALID_METADATA)

    # Assert
    assert isinstance(result, DiscoveryPhaseOutput)
    assert result.discovery_document is not None
    assert result.discovery_document.section_count >= 1
    assert result.validation_result == _VALID_VALIDATION
    assert result.generation_metadata == _VALID_METADATA


@pytest.mark.unit
def test_discovery_mode_build_output_none_yields_empty_document_not_none_string() -> None:
    # Arrange
    mode = DiscoveryMode()

    # Act
    result = mode.build_output(None, _VALID_VALIDATION, _VALID_METADATA)

    # Assert
    assert isinstance(result, DiscoveryPhaseOutput)
    assert result.discovery_document.section_count == 0
    assert result.discovery_document.nodes == []


@pytest.mark.unit
def test_discovery_refine_mode_build_output_none_yields_empty_document() -> None:
    # Arrange
    mode = DiscoveryRefineMode()

    # Act
    result = mode.build_output(None, _VALID_VALIDATION, _VALID_METADATA)

    # Assert
    assert isinstance(result, DiscoveryPhaseOutput)
    assert result.discovery_document.nodes == []


@pytest.mark.unit
def test_discovery_refine_mode_build_output_returns_discovery_phase_output() -> None:
    # Arrange
    mode = DiscoveryRefineMode()

    # Act
    result = mode.build_output(_DISCOVERY_MD, _VALID_VALIDATION, _VALID_METADATA)

    # Assert
    assert isinstance(result, DiscoveryPhaseOutput)
    assert result.discovery_document is not None


@pytest.mark.unit
def test_discovery_mode_build_output_handles_dict_input() -> None:
    # Arrange
    mode = DiscoveryMode()

    # Act
    result = mode.build_output({"document": _DISCOVERY_MD}, _VALID_VALIDATION, _VALID_METADATA)

    # Assert
    assert isinstance(result, DiscoveryPhaseOutput)
    assert result.discovery_document.section_count >= 1


@pytest.mark.unit
def test_features_mode_build_output_returns_features_phase_output() -> None:
    # Arrange
    mode = FeaturesMode()
    import json

    # Act
    result = mode.build_output(json.loads(_FEATURES_JSON), _VALID_VALIDATION, _VALID_METADATA)

    # Assert
    assert isinstance(result, FeaturesPhaseOutput)
    assert len(result.features) == 1
    assert result.features[0].title == "Feature 1"


@pytest.mark.unit
def test_ears_mode_build_output_returns_ears_phase_output() -> None:
    # Arrange
    mode = EARSMode()
    mode._feature_id = FeatureId("feat_01")  # type: ignore[reportPrivateUsage]
    mode._feature_number = 1  # type: ignore[reportPrivateUsage]
    import json

    # Act
    result = mode.build_output(json.loads(_EARS_JSON), _VALID_VALIDATION, _VALID_METADATA)

    # Assert
    assert isinstance(result, EARSPhaseOutput)
    assert len(result.requirements) == 1
    assert result.requirements_markdown != ""
