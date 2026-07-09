import json
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.contracts.pipeline.phase_outputs import (
    EARSPhaseOutput,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.ears import EARSPattern
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.domain.pipeline.phase_modes.ears_mode import EARSMode

_VALID_METADATA = GenerationMetadata(llm_calls=1, total_tokens=10)
_VALID_VALIDATION = ValidationResult(is_valid=True)

_VALID_EARS_JSON = json.dumps(
    {
        "requirements": [
            {
                "code": "REQ-1.1",
                "title": "Presentación de montos con dos decimales",
                "pattern": "Ubicuo",
                "statement": "El sistema debe presentar todos los montos con exactamente dos decimales",
                "origin": "Garantiza consistencia. Se deriva de C01 y Reglas de negocio.",
                "acceptance_criteria": [
                    {
                        "scenario": "Montos en pantalla de balance",
                        "given": "el usuario se encuentra en la pantalla principal",
                        "when": "hace clic en la pestaña Balance",
                        "then": "todos los montos aparecen formateados con dos decimales",
                    },
                    {
                        "scenario": "Montos en detalle de gasto",
                        "given": "el usuario se encuentra en el listado de gastos",
                        "when": "hace clic en un gasto registrado",
                        "then": "cada cuota individual aparece con dos decimales",
                    },
                ],
            },
            {
                "code": "REQ-1.2",
                "title": "Cálculo de cuota al registrar gasto",
                "pattern": "Basado en eventos",
                "statement": (
                    "CUANDO un participante confirma el registro de un gasto, "
                    "el sistema debe calcular la cuota correspondiente"
                ),
                "origin": "Traduce la interacción central de C01. Se deriva de C01 y Metas del producto.",
                "acceptance_criteria": [
                    {
                        "scenario": "Reparto equitativo entre tres participantes",
                        "given": "el usuario se encuentra en el registro de gastos con tres participantes",
                        "when": "ingresa 90 como monto y hace clic en Registrar",
                        "then": "el balance de cada participante refleja una deuda de 30",
                    },
                    {
                        "scenario": "Reparto con monto no divisible",
                        "given": "el usuario se encuentra en el registro de gastos con tres participantes",
                        "when": "ingresa 100 como monto y hace clic en Registrar",
                        "then": "las cuotas suman exactamente 100 sin diferencia por redondeo",
                    },
                ],
            },
            {
                "code": "REQ-1.3",
                "title": "Impedir registro con un solo participante",
                "pattern": "Determinado por estado",
                "statement": (
                    "MIENTRAS el grupo tiene un único participante activo, "
                    "el sistema debe impedir el registro de nuevos gastos"
                ),
                "origin": "Aplica regla de negocio de mínimo dos participantes. Se deriva de C01.",
                "acceptance_criteria": [
                    {
                        "scenario": "Intento de registro sin participantes suficientes",
                        "given": "el usuario pertenece a un grupo donde es el único miembro",
                        "when": "hace clic en Nuevo gasto",
                        "then": "el producto muestra un aviso indicando que no es posible registrar gastos",
                    },
                    {
                        "scenario": "Registro habilitado con segundo miembro",
                        "given": "el usuario pertenece a un grupo con un segundo miembro",
                        "when": "hace clic en Nuevo gasto",
                        "then": "el producto abre la pantalla de registro con normalidad",
                    },
                ],
            },
        ]
    }
)

_EARS_JSON_SINGLE_CRITERION = json.dumps(
    {
        "requirements": [
            {
                "code": "REQ-1.1",
                "title": "Presentación de montos",
                "pattern": "Ubicuo",
                "statement": "El sistema debe presentar montos con dos decimales",
                "origin": "Garantiza consistencia. Se deriva de C01.",
                "acceptance_criteria": [
                    {
                        "scenario": "Único criterio",
                        "given": "usuario en pantalla principal",
                        "when": "hace clic",
                        "then": "montos formateados",
                    },
                ],
            },
        ]
    }
)

_EARS_JSON_EMPTY = json.dumps({"requirements": []})


@pytest.mark.unit
def test_ears_mode_build_output_returns_ears_phase_output() -> None:
    # Arrange
    mode = EARSMode()
    mode._feature_id = FeatureId("feat_01")  # type: ignore[reportPrivateUsage]
    mode._feature_number = 1  # type: ignore[reportPrivateUsage]

    # Act
    result = mode.build_output(json.loads(_VALID_EARS_JSON), _VALID_VALIDATION, _VALID_METADATA)

    # Assert
    assert isinstance(result, EARSPhaseOutput)
    assert len(result.requirements) == 3
    assert result.requirements[0].title == "Presentación de montos con dos decimales"
    assert result.requirements[0].pattern == EARSPattern.ubiquitous
    assert result.requirements[0].statement == (
        "El sistema debe presentar todos los montos con exactamente dos decimales"
    )
    assert result.requirements[0].origin == "Garantiza consistencia. Se deriva de C01 y Reglas de negocio."
    assert result.requirements_markdown != ""


@pytest.mark.unit
def test_ears_mode_markdown_structure_includes_heading_separators_and_criteria() -> None:
    # Arrange
    mode = EARSMode()
    mode._feature_id = FeatureId("feat_01")  # type: ignore[reportPrivateUsage]
    mode._feature_number = 1  # type: ignore[reportPrivateUsage]

    # Act
    result = mode.build_output(json.loads(_VALID_EARS_JSON), _VALID_VALIDATION, _VALID_METADATA)

    # Assert
    assert "### REQ-1.1 Presentación de montos con dos decimales" in result.requirements_markdown
    assert "### REQ-1.2 Cálculo de cuota al registrar gasto" in result.requirements_markdown
    assert "### REQ-1.3 Impedir registro con un solo participante" in result.requirements_markdown
    assert "**Ubicuo**" in result.requirements_markdown
    assert "**Basado en eventos**" in result.requirements_markdown
    assert "**Determinado por estado**" in result.requirements_markdown
    assert "---" in result.requirements_markdown
    assert "**Criterios de Aceptación**" in result.requirements_markdown
    assert "#### Criterios" not in result.requirements_markdown
    assert "**Escenario:" in result.requirements_markdown
    assert "- **Dado** que" in result.requirements_markdown
    assert "- **Cuando**" in result.requirements_markdown
    assert "- **Entonces**" in result.requirements_markdown
    assert "**Origen**" not in result.requirements_markdown


@pytest.mark.unit
def test_ears_mode_markdown_excludes_origin_field() -> None:
    # Arrange
    mode = EARSMode()
    mode._feature_id = FeatureId("feat_01")  # type: ignore[reportPrivateUsage]
    mode._feature_number = 1  # type: ignore[reportPrivateUsage]

    # Act
    result = mode.build_output(json.loads(_VALID_EARS_JSON), _VALID_VALIDATION, _VALID_METADATA)

    # Assert
    assert "**Origen**" not in result.requirements_markdown


@pytest.mark.unit
def test_ears_mode_validate_output_detects_single_criterion() -> None:
    # Arrange
    mode = EARSMode()
    output = json.loads(_EARS_JSON_SINGLE_CRITERION)

    # Act
    result = mode.validate_output(output)

    # Assert
    assert result.is_valid is False
    assert any("al menos 2 criterios" in e for e in result.errors)


@pytest.mark.unit
def test_ears_mode_validate_output_detects_empty_requirements() -> None:
    # Arrange
    mode = EARSMode()
    output = json.loads(_EARS_JSON_EMPTY)

    # Act
    result = mode.validate_output(output)

    # Assert
    assert result.is_valid is False
    assert any("al menos 3 requisitos" in e for e in result.errors)


@pytest.mark.unit
def test_ears_mode_system_prompt_is_not_empty() -> None:
    # Arrange
    mode = EARSMode()

    # Act
    prompt = mode.system_prompt

    # Assert
    assert len(prompt) > 100
    assert "EARS" in prompt
    assert "statement" in prompt
    assert "origin" in prompt
    assert "acceptance_criteria" in prompt
    assert "code" in prompt


@pytest.mark.unit
def test_ears_mode_phase_name_is_requisitos() -> None:
    # Arrange
    mode = EARSMode()

    # Act
    phase = mode.phase_name

    # Assert
    assert phase.value == "requisitos"


@pytest.mark.unit
def test_ears_mode_available_tools_includes_software_level() -> None:
    # Arrange
    mode = EARSMode()

    # Act
    tools = mode.available_tools

    # Assert
    tool_names = {t.name for t in tools}
    assert "validate_ears_software_level" in tool_names
    assert "validate_ears_syntax" in tool_names
    assert "validate_ears_quality" in tool_names


@pytest.mark.unit
def test_ears_mode_validate_output_rejects_non_dict() -> None:
    # Arrange
    mode = EARSMode()

    # Act
    result = mode.validate_output("string_no_valido")

    # Assert
    assert result.is_valid is False
    assert "Formato de salida no reconocido" in result.errors
