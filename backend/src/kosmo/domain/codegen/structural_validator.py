from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class StructuralValidationResult:
    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    missing_page: bool = False
    missing_slice: bool = False
    missing_registry: bool = False


def validate_feature_structure(
    feature_slug: str,
    files: Iterable[str],
    registry_content: str | None = None,
    page_content: str | None = None,
) -> StructuralValidationResult:
    """Valida determinísticamente la estructura requerida para una funcionalidad en el workspace.

    Verifica:
    1. Existencia de la página principal en `src/app/<slug>/page.tsx` y su export default.
    2. Existencia de al menos un archivo en el slice de la feature en `src/features/<slug>/`.
    3. Presencia del slug o import de la feature en `src/lib/feature-registry.ts` (si se provee el contenido).
    """
    normalized_slug = feature_slug.strip().lower()
    normalized_files = [f.replace("\\", "/").strip("./") for f in files]

    # 1. Verificar page.tsx
    valid_page_suffixes = (
        f"src/app/{normalized_slug}/page.tsx",
        f"src/app/{normalized_slug}/page.jsx",
        f"src/app/{normalized_slug}/page.ts",
        f"src/app/{normalized_slug}/page.js",
    )
    has_page = any(
        f.lower() in valid_page_suffixes or any(f.lower().endswith(f"/{suffix}") for suffix in valid_page_suffixes)
        for f in normalized_files
    )

    page_has_export_default = True
    if page_content is not None:
        page_has_export_default = "export default" in page_content

    # 2. Verificar feature slice
    slice_prefix = f"src/features/{normalized_slug}/"
    has_slice = any(f.lower().startswith(slice_prefix) or f"/{slice_prefix}" in f.lower() for f in normalized_files)

    # 3. Verificar feature registry
    has_registry = True
    if registry_content is not None:
        has_registry = normalized_slug in registry_content.lower()
    else:
        registry_file = "src/lib/feature-registry.ts"
        has_registry_file = any(
            f.lower() == registry_file or f.lower().endswith(f"/{registry_file}") for f in normalized_files
        )
        if not has_registry_file:
            has_registry = False

    errors: list[str] = []
    if not has_page:
        errors.append(f"Falta la página principal de la funcionalidad: src/app/{normalized_slug}/page.tsx")
    elif not page_has_export_default:
        errors.append(
            f"La página 'src/app/{normalized_slug}/page.tsx' debe tener exportación por defecto ('export default')."
        )
    if not has_slice:
        errors.append(f"Falta el módulo de la funcionalidad: src/features/{normalized_slug}/")
    if not has_registry:
        errors.append(f"La funcionalidad '{normalized_slug}' no está registrada en src/lib/feature-registry.ts")

    return StructuralValidationResult(
        is_valid=len(errors) == 0,
        errors=tuple(errors),
        missing_page=not has_page or not page_has_export_default,
        missing_slice=not has_slice,
        missing_registry=not has_registry,
    )


def validate_workspace_feature_structure(
    workspace_dir: str | Path,
    feature_slug: str,
    extra_files: Iterable[str] = (),
) -> StructuralValidationResult:
    """Inspecciona el filesystem del workspace para validar la estructura de la feature."""
    ws_path = Path(workspace_dir)
    found_files: set[str] = set(extra_files)

    if ws_path.is_dir():
        for p in ws_path.rglob("*"):
            if p.is_file():
                try:
                    rel = p.relative_to(ws_path).as_posix()
                    found_files.add(rel)
                except ValueError:
                    pass

    normalized_slug = feature_slug.strip().lower()
    page_candidates = (
        ws_path / "src" / "app" / normalized_slug / "page.tsx",
        ws_path / "src" / "app" / normalized_slug / "page.jsx",
        ws_path / "src" / "app" / normalized_slug / "page.ts",
        ws_path / "src" / "app" / normalized_slug / "page.js",
    )
    page_content: str | None = None
    for candidate in page_candidates:
        if candidate.is_file():
            try:
                page_content = candidate.read_text(encoding="utf-8")
                break
            except Exception:
                pass

    registry_path = ws_path / "src" / "lib" / "feature-registry.ts"
    registry_content: str | None = None
    if registry_path.is_file():
        try:
            registry_content = registry_path.read_text(encoding="utf-8")
        except Exception:
            registry_content = None

    return validate_feature_structure(
        feature_slug=feature_slug,
        files=found_files,
        registry_content=registry_content,
        page_content=page_content,
    )
