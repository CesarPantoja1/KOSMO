from __future__ import annotations

import re

_IMPORT_PATTERN = re.compile(
    r"^\s*import\s*\{([^}]*)\}\s*from\s*[\"'][^\"']*/features/(?P<slug>[^\"']+)/manifest[\"']\s*;?\s*$"
)


def remove_feature_from_registry(content: str, slug: str) -> str:
    """Elimina el import y la entrada del array de una feature del feature-registry.ts.

    Sigue la convención del workspace generado:
    `import { <name> } from "@/features/<slug>/manifest";` + `<name>,` en el array.
    Si el import no matchea la convención, elimina por fallback cualquier línea
    que referencie `@/features/<slug>/`.
    """
    lines = content.splitlines()
    removed_names: list[str] = []
    kept: list[str] = []

    for line in lines:
        match = _IMPORT_PATTERN.match(line)
        if match and match.group("slug") == slug:
            names = [part.strip().split(" as ")[-1].strip() for part in match.group(1).split(",") if part.strip()]
            removed_names.extend(names)
            continue
        kept.append(line)

    if not removed_names:
        kept = [line for line in kept if f"@/features/{slug}/" not in line]
        return _join_preserving_trailing_newline(kept, content)

    result: list[str] = []
    for line in kept:
        stripped = line.strip()
        if any(stripped == name or stripped.startswith(f"{name},") for name in removed_names):
            continue
        result.append(line)

    return _join_preserving_trailing_newline(result, content)


def _join_preserving_trailing_newline(lines: list[str], original: str) -> str:
    joined = "\n".join(lines)
    if original.endswith("\n") and not joined.endswith("\n"):
        joined += "\n"
    return joined
