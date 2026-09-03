from __future__ import annotations

import json


def _typescript_string(value: str) -> str:
    """Devuelve un literal de cadena TypeScript seguro para contenido proporcionado por usuarios."""
    return json.dumps(value, ensure_ascii=False)


def format_site_config(
    name: str,
    description: str,
    archetype: str = "saas_tool",
    primary_color: str = "#0f766e",
) -> str:
    """Genera el contenido TypeScript para src/lib/site.ts respetando el esquema del template."""
    return (
        "export const siteConfig = {\n"
        f"  name: {_typescript_string(name)},\n"
        f"  description: {_typescript_string(description)},\n"
        f"  archetype: {_typescript_string(archetype)} as\n"
        '    | "storefront"\n'
        '    | "dashboard"\n'
        '    | "workflow"\n'
        '    | "saas_tool"\n'
        '    | "content",\n'
        f"  primaryColor: {_typescript_string(primary_color)},\n"
        "} as const;\n"
    )
