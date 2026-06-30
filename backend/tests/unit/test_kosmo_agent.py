import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.contracts.llm.ports import LLMResponse, LLMUsage, PromptTemplate
from kosmo.contracts.pipeline.phase_contexts import DiscoveryPhaseContext
from kosmo.contracts.pipeline.phase_outputs import (
    DiscoveryPhaseOutput,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.pipeline.kosmo_agent import KOSMOAgent
from kosmo.domain.pipeline.tool_registry import ToolRegistry


def _discovery_final_json(text: str) -> str:
    return json.dumps({"reasoning": "Documento listo", "final": True, "output": text})


_DISCOVERY_VALID = (
    "## Visión del producto\n"
    "El producto ayuda a las familias a organizar y repartir gastos compartidos "
    "de forma equitativa y transparente entre todos los participantes del hogar "
    "de manera simple y efectiva sin complicaciones adicionales.\n\n"
    "## Espacio del problema\n"
    "Las familias necesitan llevar un control claro y justo de los gastos compartidos, "
    "evitando conflictos por dinero y asegurando transparencia en las cuentas del hogar. "
    "Sin una herramienta adecuada surgen discusiones y falta de confianza entre los miembros "
    "del grupo familiar.\n\n"
    "## Actores\n"
    "- **Administrador del hogar:** persona que gestiona los grupos y autoriza pagos "
    "y tiene visibilidad completa de las finanzas del grupo familiar.\n"
    "- **Miembro del hogar:** persona que participa en los gastos compartidos y registra "
    "sus consumos de forma individual y detallada.\n\n"
    "## Propuesta de valor\n"
    "- **Para el administrador:** control total y visibilidad de las finanzas del hogar "
    "en un solo lugar, facilitando la toma de decisiones sobre el presupuesto familiar.\n"
    "- **Para el miembro:** claridad sobre cuanto debe y en que se gasta el dinero "
    "compartido, eliminando confusiones y malentendidos entre los integrantes.\n\n"
    "## Casos de uso\n"
    "1. **Registrar gasto:** el usuario registra un gasto compartido indicando monto "
    "y los participantes involucrados en el consumo.\n"
    "2. **Calcular reparto:** el sistema divide el gasto total entre los participantes "
    "de forma equitativa segun el criterio definido.\n"
    "3. **Visualizar balance:** el usuario consulta el saldo pendiente con cada miembro "
    "del hogar en cualquier momento.\n"
    "4. **Generar informe:** el administrador genera un resumen mensual de todos los "
    "gastos compartidos del hogar.\n\n"
    "## Capacidades principales\n"
    "- **Registro de gastos:** permite registrar cada gasto compartido con su detalle "
    "y los participantes involucrados en el consumo de manera sencilla.\n"
    "- **Calculo automatico:** divide los gastos de forma equitativa entre los miembros "
    "del hogar sin necesidad de calculos manuales adicionales.\n\n"
    "## Reglas de negocio\n"
    "1. Todo gasto debe tener al menos un participante asignado para su registro "
    "y contabilizacion en el sistema.\n"
    "2. El monto del gasto registrado debe ser estrictamente mayor a cero pesos.\n"
    "3. Cada participante debe pertenecer al grupo del hogar configurado previamente "
    "por el administrador.\n"
    "4. Los saldos se recalculan automaticamente al registrar un nuevo gasto compartido "
    "entre los miembros del hogar.\n\n"
    "## Atributos de calidad\n"
    "- **Transparencia:** todos los miembros pueden ver el detalle de gastos en tiempo "
    "real de forma clara y sin restricciones de acceso.\n"
    "- **Precision:** los calculos de reparto se realizan con exactitud de centavos "
    "sin errores de redondeo en ningun caso.\n\n"
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


class StubReactLLMClient:
    """Cliente LLM que devuelve respuestas ReAct predefinidas para tests."""

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses: list[str] = responses or []
        self._calls: list[PromptTemplate] = []
        self._index = 0

    @property
    def call_count(self) -> int:
        return len(self._calls)

    async def complete(
        self,
        prompt: PromptTemplate,
        temperature: float = 0.3,  # noqa: ARG002
        max_tokens: int = 4096,  # noqa: ARG002
    ) -> LLMResponse:
        self._calls.append(prompt)
        if self._index < len(self._responses):
            text = self._responses[self._index]
            self._index += 1
        else:
            text = _discovery_final_json(_DISCOVERY_VALID)
        return LLMResponse(
            text=text,
            usage=LLMUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        )

    async def complete_json(
        self,
        prompt: PromptTemplate,
        temperature: float = 0.1,  # noqa: ARG002
        max_tokens: int = 4096,  # noqa: ARG002
    ) -> LLMResponse:
        return await self.complete(prompt, temperature, max_tokens)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_kosmo_agent_execute_single_step_success() -> None:
    # Arrange
    llm = StubReactLLMClient(responses=[_discovery_final_json(_DISCOVERY_VALID)])
    registry = ToolRegistry()
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=3,
    )
    agent._modes[SpecPhase.DESCUBRIMIENTO] = _make_discovery_mode()  # type: ignore[reportPrivateUsage]

    # Act
    result = await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
    )

    # Assert
    assert isinstance(result, DiscoveryPhaseOutput)
    assert result.validation_result.is_valid is True
    assert result.generation_metadata.llm_calls == 1
    assert len(result.generation_metadata.reasoning_log) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_kosmo_agent_execute_with_tool_call() -> None:
    # Arrange
    responses = [
        json.dumps(
            {
                "reasoning": "Necesito verificar la estructura",
                "action": "validate_structure",
                "input": {"document": _DISCOVERY_VALID},
            }
        ),
        _discovery_final_json(_DISCOVERY_VALID),
    ]
    llm = StubReactLLMClient(responses=responses)
    registry = ToolRegistry()
    registry.register(
        "validate_structure",
        lambda _: {"is_valid": True, "errors": []},
    )
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=3,
    )
    agent._modes[SpecPhase.DESCUBRIMIENTO] = _make_discovery_mode()  # type: ignore[reportPrivateUsage]

    # Act
    result = await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
    )

    # Assert
    assert isinstance(result, DiscoveryPhaseOutput)
    assert result.validation_result.is_valid is True
    assert llm.call_count == 2
    assert result.generation_metadata.llm_calls == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_kosmo_agent_execute_retries_on_validation_failure() -> None:
    # Arrange
    invalid_doc = "## Vision del producto\n\nAPI REST"
    valid_doc = _DISCOVERY_VALID
    responses = [
        _discovery_final_json(invalid_doc),
        _discovery_final_json(valid_doc),
    ]
    llm = StubReactLLMClient(responses=responses)
    registry = ToolRegistry()
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=3,
    )
    agent._modes[SpecPhase.DESCUBRIMIENTO] = _make_discovery_mode()  # type: ignore[reportPrivateUsage]

    # Act
    result = await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
    )

    # Assert
    assert result.validation_result.is_valid is True
    assert llm.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_kosmo_agent_execute_stops_at_max_iterations() -> None:
    # Arrange
    responses = [
        json.dumps(
            {
                "reasoning": "Intento 1",
                "action": "validate_structure",
                "input": {"document": "## Test"},
            }
        ),
        json.dumps(
            {
                "reasoning": "Intento 2",
                "action": "validate_structure",
                "input": {"document": "## Test"},
            }
        ),
        json.dumps(
            {
                "reasoning": "Intento 3",
                "action": "validate_structure",
                "input": {"document": "## Test"},
            }
        ),
    ]
    llm = StubReactLLMClient(responses=responses)
    registry = ToolRegistry()
    registry.register(
        "validate_structure",
        lambda _: {"is_valid": False, "errors": ["Falta contenido"]},
    )
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=2,
    )
    agent._modes[SpecPhase.DESCUBRIMIENTO] = _make_discovery_mode()  # type: ignore[reportPrivateUsage]

    # Act
    result = await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
    )

    # Assert
    assert result.validation_result.is_valid is False
    assert llm.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_kosmo_agent_execute_traces_steps() -> None:
    # Arrange
    responses = [
        json.dumps(
            {
                "reasoning": "Verificando estructura",
                "action": "validate_structure",
                "input": {"document": _DISCOVERY_VALID},
            }
        ),
        _discovery_final_json(_DISCOVERY_VALID),
    ]
    llm = StubReactLLMClient(responses=responses)
    registry = ToolRegistry()
    registry.register(
        "validate_structure",
        lambda _: {"is_valid": True, "errors": []},
    )
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
        max_iterations=3,
    )
    agent._modes[SpecPhase.DESCUBRIMIENTO] = _make_discovery_mode()  # type: ignore[reportPrivateUsage]

    # Act
    result = await agent.execute(
        phase=SpecPhase.DESCUBRIMIENTO,
        context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
    )

    # Assert
    assert result.generation_metadata.reasoning_log is not None
    assert len(result.generation_metadata.reasoning_log) >= 1
    assert any("validate_structure" in log for log in result.generation_metadata.reasoning_log)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_kosmo_agent_raises_when_mode_missing() -> None:
    # Arrange
    llm = StubReactLLMClient()
    registry = ToolRegistry()
    agent = KOSMOAgent(
        llm_client=llm,  # type: ignore[reportArgumentType]
        registry=registry,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="No hay modo"):
        await agent.execute(
            phase=SpecPhase.DESCUBRIMIENTO,
            context=DiscoveryPhaseContext(project_name="Test", project_description="Test"),
        )


def _make_discovery_mode() -> Any:
    from kosmo.domain.pipeline.phase_modes.discovery_mode import DiscoveryMode

    return DiscoveryMode()
