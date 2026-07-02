import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.contracts.pipeline.orchestrator_ports import Skill
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.pipeline.phase_modes.discovery_mode import DiscoveryMode
from kosmo.domain.pipeline.phase_modes.discovery_refine_mode import (
    DiscoveryRefineMode,
)
from kosmo.domain.pipeline.skill_registry import SkillRegistry


@pytest.mark.unit
def test_skill_creation() -> None:
    mode = DiscoveryMode()
    skill = Skill(
        name="discovery_generate",
        description="Genera el documento de descubrimiento desde cero",
        phase=SpecPhase.DESCUBRIMIENTO,
        mode=mode,
    )

    assert skill.name == "discovery_generate"
    assert skill.description == "Genera el documento de descubrimiento desde cero"
    assert skill.phase == SpecPhase.DESCUBRIMIENTO
    assert skill.mode is mode


@pytest.mark.unit
def test_skill_registry_register_and_get() -> None:
    registry = SkillRegistry()
    mode = DiscoveryMode()
    skill = Skill(
        name="discovery_generate",
        description="Genera el documento de descubrimiento desde cero",
        phase=SpecPhase.DESCUBRIMIENTO,
        mode=mode,
    )

    registry.register(skill)
    retrieved = registry.get("discovery_generate")

    assert retrieved is not None
    assert retrieved.name == "discovery_generate"
    assert retrieved.mode is mode


@pytest.mark.unit
def test_skill_registry_get_nonexistent_returns_none() -> None:
    registry = SkillRegistry()

    result = registry.get("nonexistent")

    assert result is None


@pytest.mark.unit
def test_skill_registry_get_for_phase() -> None:
    registry = SkillRegistry()
    registry.register(
        Skill(
            name="discovery_generate",
            description="Genera desde cero",
            phase=SpecPhase.DESCUBRIMIENTO,
            mode=DiscoveryMode(),
        )
    )
    registry.register(
        Skill(
            name="discovery_refine",
            description="Refina documento existente",
            phase=SpecPhase.DESCUBRIMIENTO,
            mode=DiscoveryRefineMode(),
        )
    )
    registry.register(
        Skill(
            name="ears_generate",
            description="Genera requisitos EARS",
            phase=SpecPhase.REQUISITOS,
            mode=DiscoveryMode(),
        )
    )

    discovery_skills = registry.get_for_phase(SpecPhase.DESCUBRIMIENTO)
    requirements_skills = registry.get_for_phase(SpecPhase.REQUISITOS)
    features_skills = registry.get_for_phase(SpecPhase.CARACTERISTICAS)

    assert len(discovery_skills) == 2
    assert len(requirements_skills) == 1
    assert len(features_skills) == 0
    assert {s.name for s in discovery_skills} == {"discovery_generate", "discovery_refine"}


@pytest.mark.unit
def test_skill_registry_resolve_returns_mode() -> None:
    registry = SkillRegistry()
    mode = DiscoveryMode()
    registry.register(
        Skill(
            name="discovery_generate",
            description="Genera desde cero",
            phase=SpecPhase.DESCUBRIMIENTO,
            mode=mode,
        )
    )

    resolved = registry.resolve("discovery_generate")

    assert resolved is mode


@pytest.mark.unit
def test_skill_registry_resolve_nonexistent_raises() -> None:
    registry = SkillRegistry()

    with pytest.raises(ValueError, match="Skill 'nonexistent' no encontrado"):
        registry.resolve("nonexistent")


@pytest.mark.unit
def test_skill_registry_unregister() -> None:
    registry = SkillRegistry()
    registry.register(
        Skill(
            name="discovery_generate",
            description="Genera desde cero",
            phase=SpecPhase.DESCUBRIMIENTO,
            mode=DiscoveryMode(),
        )
    )

    registry.unregister("discovery_generate")

    assert registry.get("discovery_generate") is None
    assert registry.get_for_phase(SpecPhase.DESCUBRIMIENTO) == []


@pytest.mark.unit
def test_skill_registry_list_all() -> None:
    registry = SkillRegistry()
    registry.register(
        Skill(
            name="discovery_generate",
            description="Genera desde cero",
            phase=SpecPhase.DESCUBRIMIENTO,
            mode=DiscoveryMode(),
        )
    )
    registry.register(
        Skill(
            name="requirements_generate",
            description="Genera EARS",
            phase=SpecPhase.REQUISITOS,
            mode=DiscoveryMode(),
        )
    )

    all_skills = registry.list_all()

    assert len(all_skills) == 2
    assert {s.name for s in all_skills} == {"discovery_generate", "requirements_generate"}
