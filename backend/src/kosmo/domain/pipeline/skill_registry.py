from __future__ import annotations

from kosmo.contracts.pipeline.orchestrator_ports import PhaseMode, Skill
from kosmo.contracts.sdd.document import SpecPhase


class SkillRegistry:
    """Registro de habilidades del agente que mapea nombres a Skills.

    Soporta registro dinamico, consulta por fase, carga/descarga bajo demanda
    y resolucion del PhaseMode subyacente para ejecucion.
    """

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def unregister(self, name: str) -> None:
        self._skills.pop(name, None)

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def resolve(self, name: str) -> PhaseMode:
        skill = self._skills.get(name)
        if skill is None:
            raise ValueError(f"Skill '{name}' no encontrado")
        return skill.mode

    def get_for_phase(self, phase: SpecPhase) -> list[Skill]:
        return [s for s in self._skills.values() if s.phase == phase]

    def list_all(self) -> list[Skill]:
        return list(self._skills.values())
