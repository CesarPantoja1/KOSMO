from __future__ import annotations

from importlib import resources

from kosmo.contracts.sdd.document import SpecPhase

_FILES = {
    SpecPhase.DESCUBRIMIENTO: "discovery_example.md",
    SpecPhase.CARACTERISTICAS: "features_example.md",
    SpecPhase.REQUISITOS: "ears_example.md",
    SpecPhase.MODELO: "modelo_example.md",
}


def load_example(phase: SpecPhase) -> str | None:
    name = _FILES.get(phase)
    if name is None:
        return None
    try:
        return (
            resources.files("kosmo.domain.sdd.few_shot")
            .joinpath(name)
            .read_text(encoding="utf-8")
        )
    except FileNotFoundError:
        return None
