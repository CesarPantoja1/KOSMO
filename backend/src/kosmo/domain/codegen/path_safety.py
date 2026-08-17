from __future__ import annotations

import os
import re
from pathlib import Path


class UnsafePathError(ValueError):
    """Lanzada cuando una ruta intenta escapar del directorio raíz del workspace."""


def _is_absolute_path_str(raw_path: str) -> bool:
    """Detecta si una ruta es absoluta en formato POSIX, Windows o UNC."""
    if raw_path.startswith(("/", "\\", "//", "\\\\")):
        return True
    return bool(re.match(r"^[a-zA-Z]:", raw_path))


def validate_safe_path(path: str | Path, workspace_root: str | Path) -> bool:
    """Valida puramente si una ruta reside de forma segura dentro del workspace_root.

    Rechaza:
    - Rutas vacías o con bytes nulos.
    - Intentos de navegación al directorio padre (..).
    - Rutas absolutas que resuelven fuera del workspace.
    - Symlinks que apunten fuera del workspace.
    """
    raw_path = str(path).strip()
    raw_root = str(workspace_root).strip()

    if not raw_path or not raw_root:
        return False

    if "\0" in raw_path or "\0" in raw_root:
        return False

    normalized_path_str = raw_path.replace("\\", "/")

    # Rechazar explícitamente componentes de navegación hacia arriba
    path_obj = Path(normalized_path_str)
    if any(part == ".." for part in path_obj.parts):
        return False

    # Si tiene letra de unidad Windows pero estamos en entorno POSIX, no puede residir en workspace_root POSIX
    if bool(re.match(r"^[a-zA-Z]:", raw_path)) and os.name != "nt":
        return False

    try:
        root_resolved = Path(raw_root).resolve()
        is_abs = _is_absolute_path_str(raw_path) or path_obj.is_absolute()
        target_resolved = Path(raw_path).resolve() if is_abs else (root_resolved / path_obj).resolve()

        return target_resolved.is_relative_to(root_resolved)
    except (ValueError, OSError, RuntimeError):
        return False


def is_safe_path(path: str | Path, workspace_root: str | Path) -> bool:
    """Alias de conveniencia para validate_safe_path."""
    return validate_safe_path(path, workspace_root)


def ensure_safe_path(path: str | Path, workspace_root: str | Path) -> Path:
    """Valida y retorna el Path resuelto y seguro dentro del workspace_root.

    Lanza UnsafePathError si la ruta es insegura o escapa del workspace.
    """
    if not validate_safe_path(path, workspace_root):
        raise UnsafePathError(f"Unsafe path detected: '{path}' escapes workspace root '{workspace_root}'")

    raw_path = str(path).strip()
    root_resolved = Path(workspace_root).resolve()
    is_abs = _is_absolute_path_str(raw_path) or Path(raw_path).is_absolute()
    if is_abs:
        return Path(raw_path).resolve()
    normalized_rel = raw_path.replace("\\", "/")
    return (root_resolved / normalized_rel).resolve()


def sanitize_relative_path(path: str) -> str:
    """Normaliza y sanitiza una ruta relativa interna del workspace.

    - Convierte separadores a barras normales (/).
    - Elimina barras iniciales redundantes y './'.
    - Colapsa barras duplicadas.
    - Lanza UnsafePathError si contiene '..' o es inválida.
    """
    raw = path.strip()
    if not raw:
        raise UnsafePathError("Empty path cannot be sanitized")

    if "\0" in raw:
        raise UnsafePathError("Null byte in path is not allowed")

    normalized = raw.replace("\\", "/")
    # Colapsar barras múltiples consecutivas
    normalized = re.sub(r"/+", "/", normalized)

    # Eliminar prefijos / o ./
    if normalized.startswith("./"):
        normalized = normalized[2:]
    elif normalized.startswith("/"):
        normalized = normalized[1:]

    parts = normalized.split("/")
    if any(part == ".." for part in parts):
        raise UnsafePathError(f"Directory traversal detected in path: '{path}'")

    clean_parts = [p for p in parts if p and p != "."]
    if not clean_parts:
        raise UnsafePathError("Path resolves to empty relative path")

    return "/".join(clean_parts)
