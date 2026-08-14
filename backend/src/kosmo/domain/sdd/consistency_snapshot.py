from __future__ import annotations

import hashlib


def compute_snapshot_hash(*parts: str) -> str:
    """Hash determinista de las entradas de una evaluacion de consistencia."""
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
