from __future__ import annotations

import re

_PUNCT = ".,;:!?¿¡()[]{}\"'«»…"
_MARKDOWN_NOISE = re.compile(r"[*_`#>|~\-]+")


def derive_session_title(content: str, max_words: int = 4) -> str:
    """Deriva un título corto del primer prompt del usuario.

    Limpia markdown y puntuación, colapsa espacios y conserva las primeras
    ``max_words`` palabras en formato oración. Devuelve cadena vacía si no
    hay texto útil.
    """
    cleaned = _MARKDOWN_NOISE.sub(" ", content)
    words: list[str] = []
    for raw in cleaned.split():
        word = raw.strip(_PUNCT)
        if word:
            words.append(word)
    if not words:
        return ""
    title = " ".join(words[:max_words])
    return title[0].upper() + title[1:].lower()
