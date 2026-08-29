from __future__ import annotations


def format_site_config(
    name: str,
    description: str,
    archetype: str = "saas_tool",
    primary_color: str = "#0f766e",
) -> str:
    """Genera el contenido TypeScript para src/lib/site.ts respetando el esquema del template."""
    sanitized_name = name.replace('"', '\\"')
    sanitized_desc = description.replace('"', '\\"')
    return (
        "export const siteConfig = {\n"
        f'  name: "{sanitized_name}",\n'
        f'  description: "{sanitized_desc}",\n'
        f'  archetype: "{archetype}" as\n'
        '    | "storefront"\n'
        '    | "dashboard"\n'
        '    | "workflow"\n'
        '    | "saas_tool"\n'
        '    | "content",\n'
        f'  primaryColor: "{primary_color}",\n'
        "} as const;\n"
    )
