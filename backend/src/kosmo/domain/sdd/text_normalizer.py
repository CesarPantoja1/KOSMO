from __future__ import annotations

import re


def normalize_for_match(text: str) -> str:
    """Normaliza texto para comparaciones tolerantes a formato."""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()


def strip_origin_line(text: str) -> str:
    """Elimina la sección 'Origen: ...' final de una descripción de característica.

    El origen es metadato interno del agente (se deriva automáticamente) y nunca
    debe mostrarse al usuario ni persistirse en la descripción. Solo se elimina
    cuando la línea de origen está al final del texto.
    """
    lines = text.splitlines()
    while lines and lines[-1].strip().startswith(("Origen:", "**Origen:**")):
        lines.pop()
    while lines and lines[-1].strip() == "":
        lines.pop()
    return "\n".join(lines)
