from __future__ import annotations

import json
from typing import Any

from kosmo.contracts.llm.ports import LLMResponse, LLMUsage, PromptTemplate
from kosmo.domain.pipeline.phase_modes.discovery_mode import DiscoveryMode


def make_valid_discovery_json(text: str) -> str:
    return json.dumps({"reasoning": "Documento listo", "final": True, "output": text})


DISCOVERY_VALID = (
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
    "## Metas del producto\n"
    "1. **Reparto equitativo de gastos:** todo gasto compartido se distribuye entre "
    "los participantes con exactitud y cada quien puede consultar el estado de sus "
    "deudas y acreencias en cualquier momento.\n"
    "2. **Control transparente del hogar:** los saldos del grupo se mantienen "
    "actualizados y consultables para que cada integrante conozca su situación "
    "financiera dentro del grupo en todo momento.\n\n"
    "## Reglas de negocio\n"
    "1. Todo gasto debe tener al menos un participante asignado para su registro "
    "y contabilizacion en el grupo.\n"
    "2. El monto del gasto registrado debe ser estrictamente mayor a cero pesos.\n"
    "3. Cada participante debe pertenecer al grupo del hogar configurado previamente "
    "por el administrador.\n"
    "4. Los saldos se recalculan automaticamente al registrar un nuevo gasto compartido "
    "entre los miembros del hogar.\n\n"
    "## Alcance\n"
    "### Incluido\n"
    "- Registro de gastos compartidos del hogar con detalle de participantes\n"
    "### Excluido\n"
    "- Integracion con bancos y entidades financieras externas\n"
    "- Pagos electronicos y transferencias entre cuentas\n"
    "- Sincronizacion con dispositivos externos y otros servicios de terceros\n"
    "- Manejo de multiples monedas y conversion de divisas\n"
    "### Futuro potencial\n"
    "- Exportacion a hoja de calculo para analisis avanzado\n"
)


class StubReactLLMClient:
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
            text = make_valid_discovery_json(DISCOVERY_VALID)
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


def make_discovery_mode() -> Any:
    return DiscoveryMode()
