from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kosmo.contracts.sdd.discovery import DiscoveryDocument
    from kosmo.contracts.sdd.requirements_document import RequirementsDocument


def slugify_spanish(text: str, max_length: int = 80) -> str:
    normalizada = unicodedata.normalize("NFKD", text.lower().strip())
    sin_tildes = "".join(c for c in normalizada if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9ñ]+", "-", sin_tildes).strip("-")
    if max_length > 0 and len(slug) > max_length:
        slug = slug[:max_length]
        ultimo_guion = slug.rfind("-")
        if ultimo_guion > 0:
            slug = slug[:ultimo_guion]
    return slug


def extract_sections(document: dict) -> list[dict]:
    secciones: list[dict] = []
    stack: list[dict] = []
    _walk_document(document.get("content", []), secciones, stack)
    return secciones


def _walk_document(nodes: list[dict], raiz: list[dict], stack: list[dict]) -> None:
    for node in nodes:
        if node.get("type") == "heading":
            attrs = node.get("attrs") or {}
            nivel = attrs.get("level", 1) if isinstance(attrs, dict) else 1
            texto = _extract_plain_text(node.get("content", []))
            attrs_dict = node.get("attrs", {}) if isinstance(node.get("attrs"), dict) else {}
            ancla = attrs_dict.get("id", "")
            if not ancla:
                ancla = slugify_spanish(texto)

            entrada: dict = {
                "title": texto,
                "anchor": ancla,
                "level": nivel,
                "children": [],
            }

            while stack and stack[-1]["level"] >= nivel:
                stack.pop()

            if stack:
                stack[-1]["children"].append(entrada)
            else:
                raiz.append(entrada)

            stack.append(entrada)


def _extract_plain_text(nodes: list[dict]) -> str:
    partes: list[str] = []
    for node in nodes:
        if node.get("type") == "text":
            partes.append(node.get("text", ""))
        elif node.get("content"):
            partes.append(_extract_plain_text(node["content"]))
    return "".join(partes)


def document_to_markdown(node: dict) -> str:
    return _node_to_markdown(node).strip()


def _node_to_markdown(node: dict, indent: int = 0) -> str:
    tipo = node.get("type", "")
    contenido = node.get("content", []) or []
    attrs = node.get("attrs") or {}
    if not isinstance(attrs, dict):
        attrs = {}

    if tipo == "doc":
        return "\n\n".join(_node_to_markdown(c, indent) for c in contenido)

    if tipo == "heading":
        nivel = attrs.get("level", 1)
        texto = _render_inline_content(contenido)
        prefijo = "#" * nivel
        return f"{prefijo} {texto}"

    if tipo == "paragraph":
        texto = _render_inline_content(contenido)
        return texto

    if tipo == "bulletList":
        items = [_render_list_item(c, indent, ordered=False) for c in contenido]
        return "\n".join(items)

    if tipo == "orderedList":
        items = [
            _render_list_item(c, idx + 1, indent, ordered=True) for idx, c in enumerate(contenido)
        ]
        return "\n".join(items)

    if tipo == "listItem":
        return _render_inline_content(contenido)

    if tipo == "blockquote":
        texto = "\n".join(_node_to_markdown(c, indent) for c in contenido)
        lineas = texto.split("\n")
        return "\n".join(f"> {linea}" for linea in lineas)

    if tipo == "codeBlock":
        lenguaje = attrs.get("language", "")
        texto = _extract_plain_text(contenido)
        return f"```{lenguaje}\n{texto}\n```"

    if tipo == "horizontalRule":
        return "---"

    if tipo == "text":
        return _apply_marks(node.get("text", ""), node.get("marks") or [])

    if tipo == "hardBreak":
        return "\n"

    return _extract_plain_text(contenido)


def _render_list_item(node: dict, idx: int, indent: int = 0, ordered: bool = False) -> str:
    prefijo_espacios = "  " * indent
    marcador = f"{idx}." if ordered else "-"
    contenido = node.get("content", []) or []

    lineas: list[str] = []
    for child in contenido:
        child_tipo = child.get("type", "")
        if child_tipo == "paragraph":
            texto = _render_inline_content(child.get("content", []) or [])
            lineas.append(f"{prefijo_espacios}{marcador} {texto}")
        elif child_tipo in ("bulletList", "orderedList"):
            inner = _node_to_markdown(child, indent + 1)
            lineas.append(inner)

    return "\n".join(lineas)


def _render_inline_content(nodes: list[dict]) -> str:
    return "".join(_node_to_markdown(n) for n in nodes)


def _apply_marks(texto: str, marks: list[dict]) -> str:
    resultado = texto
    for mark in marks:
        tipo = mark.get("type", "")
        if tipo == "bold":
            resultado = f"**{resultado}**"
        elif tipo == "italic":
            resultado = f"*{resultado}*"
        elif tipo == "strike":
            resultado = f"~~{resultado}~~"
        elif tipo == "code":
            resultado = f"`{resultado}`"
        elif tipo == "link":
            attrs = mark.get("attrs") or {}
            href = attrs.get("href", "") if isinstance(attrs, dict) else ""
            resultado = f"[{resultado}]({href})"
    return resultado


def markdown_to_document(markdown: str) -> dict:
    try:
        from markdown_it import MarkdownIt
    except ImportError:
        return _fallback_markdown_to_document(markdown)

    md = MarkdownIt("commonmark", {"html": False})
    tokens = md.parse(markdown)

    return {
        "type": "doc",
        "content": _tokens_to_nodes(tokens),
    }


def _tokens_to_nodes(tokens: list) -> list[dict]:
    nodos: list[dict] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        ttype = token.type

        if ttype == "heading_open":
            nivel = int(token.tag[1])
            contenido = _collect_inline_content(tokens, i + 1)
            i = _skip_to("heading_close", tokens, i)
            heading_id = slugify_spanish(
                "".join(t.get("content", "") for t in contenido if t.get("type") == "text")
            )
            nodos.append(
                {
                    "type": "heading",
                    "attrs": {"level": nivel, "id": heading_id},
                    "content": contenido,
                }
            )

        elif ttype == "paragraph_open":
            contenido = _collect_inline_content(tokens, i + 1)
            i = _skip_to("paragraph_close", tokens, i)
            if contenido:
                nodos.append({"type": "paragraph", "content": contenido})

        elif ttype == "bullet_list_open":
            items: list[dict] = []
            j = i + 1
            while j < len(tokens) and tokens[j].type != "bullet_list_close":
                if tokens[j].type == "list_item_open":
                    j += 1
                    item_content: list[dict] = []
                    while j < len(tokens) and tokens[j].type != "list_item_close":
                        if tokens[j].type == "paragraph_open":
                            inner = _collect_inline_content(tokens, j + 1)
                            item_content.append({"type": "paragraph", "content": inner})
                            j = _skip_to("paragraph_close", tokens, j)
                        else:
                            j += 1
                    items.append({"type": "listItem", "content": item_content})
                else:
                    j += 1
            nodos.append({"type": "bulletList", "content": items})
            i = _skip_to("bullet_list_close", tokens, i)

        elif ttype == "ordered_list_open":
            items: list[dict] = []
            j = i + 1
            while j < len(tokens) and tokens[j].type != "ordered_list_close":
                if tokens[j].type == "list_item_open":
                    j += 1
                    item_content: list[dict] = []
                    while j < len(tokens) and tokens[j].type != "list_item_close":
                        if tokens[j].type == "paragraph_open":
                            inner = _collect_inline_content(tokens, j + 1)
                            item_content.append({"type": "paragraph", "content": inner})
                            j = _skip_to("paragraph_close", tokens, j)
                        else:
                            j += 1
                    items.append({"type": "listItem", "content": item_content})
                else:
                    j += 1
            nodos.append({"type": "orderedList", "content": items})
            i = _skip_to("ordered_list_close", tokens, i)

        elif ttype == "blockquote_open":
            contenido: list[dict] = []
            j = i + 1
            while j < len(tokens) and tokens[j].type != "blockquote_close":
                if tokens[j].type == "paragraph_open":
                    inner = _collect_inline_content(tokens, j + 1)
                    contenido.append({"type": "paragraph", "content": inner})
                    j = _skip_to("paragraph_close", tokens, j)
                else:
                    j += 1
            nodos.append({"type": "blockquote", "content": contenido})
            i = _skip_to("blockquote_close", tokens, i)

        elif ttype == "fence":
            lenguaje = token.info if token.info else ""
            nodos.append(
                {
                    "type": "codeBlock",
                    "attrs": {"language": lenguaje},
                    "content": [{"type": "text", "text": token.content}],
                }
            )

        elif ttype == "hr":
            nodos.append({"type": "horizontalRule"})

        elif ttype == "hardbreak":
            nodos.append({"type": "hardBreak"})

        i += 1

    return nodos


def _collect_inline_content(tokens: list, start: int) -> list[dict]:
    nodos: list[dict] = []
    i = start
    while i < len(tokens):
        token = tokens[i]
        ttype = token.type

        if ttype == "inline":
            if token.children:
                nodos.extend(_process_inline_children(token.children))
        elif ttype in (
            "paragraph_close",
            "heading_close",
            "list_item_close",
            "bullet_list_close",
            "ordered_list_close",
            "blockquote_close",
        ):
            break

        i += 1

    return nodos


def _process_inline_children(children: list) -> list[dict]:
    nodos: list[dict] = []
    for child in children:
        if child.type == "text":
            nodos.append({"type": "text", "text": child.content})
        elif child.type == "strong_open":
            contenido = _process_inline_until(children, children.index(child) + 1, "strong_close")
            if contenido:
                for c in contenido:
                    existing = c.get("marks") or []
                    existing.append({"type": "bold"})
                    c["marks"] = existing
                nodos.extend(contenido)
        elif child.type == "em_open":
            contenido = _process_inline_until(children, children.index(child) + 1, "em_close")
            if contenido:
                for c in contenido:
                    existing = c.get("marks") or []
                    existing.append({"type": "italic"})
                    c["marks"] = existing
                nodos.extend(contenido)
        elif child.type == "s_open":
            contenido = _process_inline_until(children, children.index(child) + 1, "s_close")
            if contenido:
                for c in contenido:
                    existing = c.get("marks") or []
                    existing.append({"type": "strike"})
                    c["marks"] = existing
                nodos.extend(contenido)
        elif child.type == "code_inline":
            nodos.append(
                {
                    "type": "text",
                    "text": child.content,
                    "marks": [{"type": "code"}],
                }
            )
        elif child.type == "link_open":
            idx = children.index(child)
            href = child.attrs.get("href", "") if child.attrs else ""
            inner = _process_inline_until(children, idx + 1, "link_close")
            if inner:
                for c in inner:
                    existing = c.get("marks") or []
                    existing.append({"type": "link", "attrs": {"href": href}})
                    c["marks"] = existing
                nodos.extend(inner)
        elif child.type == "softbreak" and nodos and nodos[-1].get("type") == "text":
            nodos[-1]["text"] += " "
        elif child.type == "hardbreak":
            nodos.append({"type": "hardBreak"})
    return nodos


def _process_inline_until(children: list, start: int, close_type: str) -> list[dict]:
    nodos: list[dict] = []
    i = start
    while i < len(children):
        child = children[i]
        if child.type == close_type:
            break
        if child.type == "text":
            nodos.append({"type": "text", "text": child.content})
        elif child.type == "code_inline":
            nodos.append(
                {
                    "type": "text",
                    "text": child.content,
                    "marks": [{"type": "code"}],
                }
            )
        elif child.type == "softbreak" and nodos and nodos[-1].get("type") == "text":
            nodos[-1]["text"] += " "
        i += 1
    return nodos


def _skip_to(target_type: str, tokens: list, start: int) -> int:
    j = start
    while j < len(tokens):
        if tokens[j].type == target_type:
            return j
        j += 1
    return start


def _fallback_markdown_to_document(markdown: str) -> dict:
    def _es_inicio_lista(ln: str, prefijos: tuple[str, ...]) -> bool:
        return ln.strip().startswith(prefijos)

    lineas = markdown.split("\n")
    nodos: list[dict] = []
    i = 0
    while i < len(lineas):
        linea = lineas[i].strip()
        if not linea:
            i += 1
            continue

        if linea.startswith("#"):
            nivel = len(linea) - len(linea.lstrip("#"))
            texto = linea.lstrip("#").strip()
            heading_id = slugify_spanish(texto)
            nodos.append(
                {
                    "type": "heading",
                    "attrs": {"level": nivel, "id": heading_id},
                    "content": [{"type": "text", "text": texto}],
                }
            )

        elif linea.startswith(">"):
            texto = linea[1:].strip()
            nodos.append(
                {
                    "type": "blockquote",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": texto}],
                        }
                    ],
                }
            )

        elif linea.startswith("- ") or linea.startswith("* "):
            items: list[dict] = []
            while i < len(lineas) and _es_inicio_lista(lineas[i], ("- ", "* ")):
                texto = lineas[i].strip()[2:]
                items.append(
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": _parse_inline_marks_fallback(texto),
                            }
                        ],
                    }
                )
                i += 1
            nodos.append({"type": "bulletList", "content": items})
            continue

        elif re.match(r"^\d+\.\s", linea):
            items: list[dict] = []
            while i < len(lineas) and re.match(r"^\d+\.\s", lineas[i].strip()):
                texto = re.sub(r"^\d+\.\s", "", lineas[i].strip())
                items.append(
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": _parse_inline_marks_fallback(texto),
                            }
                        ],
                    }
                )
                i += 1
            nodos.append({"type": "orderedList", "content": items})
            continue

        elif linea == "---" or linea == "***" or linea == "___":
            nodos.append({"type": "horizontalRule"})

        else:
            nodos.append(
                {
                    "type": "paragraph",
                    "content": _parse_inline_marks_fallback(linea),
                }
            )

        i += 1

    return {"type": "doc", "content": nodos}


def _parse_inline_marks_fallback(texto: str) -> list[dict]:
    import re as _re

    nodos: list[dict] = []
    patron = _re.compile(
        r"(\*\*\*(.+?)\*\*\*)|"  # bold + italic
        r"(\*\*(.+?)\*\*)|"  # bold
        r"(~~(.+?)~~)|"  # strike
        r"(\*(.+?)\*)|"  # italic
        r"(`(.+?)`)"  # code
    )

    ultimo = 0
    for m in patron.finditer(texto):
        inicio, fin = m.span()
        if inicio > ultimo:
            nodos.append({"type": "text", "text": texto[ultimo:inicio]})

        if m.group(1):  # ***Text***
            nodos.append(
                {
                    "type": "text",
                    "text": m.group(2),
                    "marks": [{"type": "bold"}, {"type": "italic"}],
                }
            )
        elif m.group(3):  # **Text**
            nodos.append(
                {
                    "type": "text",
                    "text": m.group(4),
                    "marks": [{"type": "bold"}],
                }
            )
        elif m.group(5):  # ~~Text~~
            nodos.append(
                {
                    "type": "text",
                    "text": m.group(6),
                    "marks": [{"type": "strike"}],
                }
            )
        elif m.group(7):  # *Text*
            nodos.append(
                {
                    "type": "text",
                    "text": m.group(8),
                    "marks": [{"type": "italic"}],
                }
            )
        elif m.group(9):  # `Text`
            nodos.append(
                {
                    "type": "text",
                    "text": m.group(10),
                    "marks": [{"type": "code"}],
                }
            )

        ultimo = fin

    if ultimo < len(texto):
        nodos.append({"type": "text", "text": texto[ultimo:]})

    return nodos or [{"type": "text", "text": texto}]


def validate_document_structure(document: dict) -> list[str]:
    hallazgos: list[str] = []

    if document.get("type") != "doc":
        hallazgos.append("El nodo raíz debe ser de tipo 'doc'")

    if "content" not in document:
        hallazgos.append("El documento debe tener un campo 'content'")

    elif not isinstance(document["content"], list):
        hallazgos.append("El campo 'content' debe ser una lista")

    else:
        for i, node in enumerate(document["content"]):
            _validate_node(node, f"content[{i}]", hallazgos)

    return hallazgos


_TIPOS_VALIDOS = frozenset(
    {
        "doc",
        "heading",
        "paragraph",
        "bulletList",
        "orderedList",
        "listItem",
        "blockquote",
        "codeBlock",
        "horizontalRule",
        "hardBreak",
        "text",
        "table",
        "tableRow",
        "tableCell",
        "image",
    }
)

_TIPOS_MARCA = frozenset({"bold", "italic", "strike", "code", "link"})


def _validate_node(node: dict, ruta: str, hallazgos: list[str]) -> None:
    if not isinstance(node, dict):
        hallazgos.append(f"{ruta}: no es un objeto")
        return

    tipo = node.get("type", "")
    if tipo not in _TIPOS_VALIDOS:
        hallazgos.append(f"{ruta}: tipo '{tipo}' no es válido")

    if tipo == "text":
        if "text" not in node:
            hallazgos.append(f"{ruta}: nodo 'text' sin campo 'text'")
        for mark in node.get("marks") or []:
            if mark.get("type") not in _TIPOS_MARCA:
                hallazgos.append(f"{ruta}: marca '{mark.get('type')}' no válida")

    contenido = node.get("content")
    if contenido is not None:
        if not isinstance(contenido, list):
            hallazgos.append(f"{ruta}: 'content' debe ser una lista")
        else:
            for j, child in enumerate(contenido):
                _validate_node(child, f"{ruta}.content[{j}]", hallazgos)


def discovery_to_markdown(discovery: DiscoveryDocument) -> str:
    secciones: list[tuple[str, str]] = [
        ("Visión del producto", discovery.vision),
        ("Espacio del problema", discovery.problem_space),
        ("Actores", discovery.actors),
        ("Propuesta de valor", discovery.value_proposition),
        ("Casos de uso", discovery.use_cases),
        ("Capacidades principales", discovery.core_capabilities),
        ("Reglas de negocio", discovery.business_rules),
        ("Atributos de calidad", discovery.quality_attributes),
        ("Alcance", discovery.scope),
    ]

    partes: list[str] = ["# Descubrimiento de Producto\n"]
    for titulo, contenido in secciones:
        if contenido.strip():
            partes.append(f"## {titulo}\n\n{contenido.strip()}")

    return "\n\n".join(partes)


def requirements_document_to_markdown(
    doc: RequirementsDocument,
    feature_title: str,
) -> str:
    categorias: list[tuple[str, str, list]] = [
        ("Requisitos Ubicuos", "Ubiquitous", doc.ubiquitous),
        ("Requisitos Basados en Eventos", "Event-driven", doc.event),
        ("Requisitos Determinados por el Estado", "State-driven", doc.state),
        ("Requisitos Opcionales", "Optional features", doc.optional),
        (
            "Requisitos de Respuestas Deseadas ante Fallos",
            "Unwanted behaviors",
            doc.unwanted,
        ),
        ("Requisitos Complejos", "Complex", doc.complex),
    ]

    req_counter = 0
    partes: list[str] = [f"# Requisitos: {feature_title}\n"]

    for titulo, _subtitulo, reqs in categorias:
        if not reqs:
            continue
        partes.append(f"## {titulo}\n")
        for i, req in enumerate(reqs):
            req_counter += 1
            resumen = _extract_summary(req.response)
            linea = f"### Requisito {req_counter} — {resumen}\n\n"
            linea += f"**Sistema:** {req.system}\n\n"
            if req.trigger:
                linea += f"**Disparador:** {req.trigger}\n\n"
            linea += f"**Respuesta:** {req.response}\n\n"
            if req.acceptance_criteria:
                linea += "**Criterios de aceptacion:**\n"
                for ac in req.acceptance_criteria:
                    linea += f"- {ac.description}"
                    if ac.expected_result:
                        linea += f"\n  Resultado esperado: {ac.expected_result}"
                    if ac.scenario:
                        linea += f"\n  Escenario: {ac.scenario}"
                    if ac.verified_by:
                        linea += f" _(verificado por: {ac.verified_by})_"
                    linea += "\n"
                linea += "\n"
            if i < len(reqs) - 1:
                linea += "---\n\n"
            partes.append(linea)

    return "\n".join(partes)


def _extract_summary(response: str) -> str:
    if not response:
        return "Sin descripcion"
    words = response.strip().split()
    if not words:
        return "Sin descripcion"
    summary = " ".join(words[:8])
    if len(words) > 8:
        summary += "..."
    return summary[0].upper() + summary[1:] if summary else summary


def extract_discovery_from_document(document: dict) -> dict:
    content = document.get("content", [])
    heading_map: dict[str, str] = {}
    current_heading: str | None = None
    current_parts: list[str] = []

    for node in content:
        if node.get("type") != "heading":
            is_content = node.get("type") in (
                "paragraph",
                "bulletList",
                "orderedList",
                "blockquote",
            )
            if is_content and current_heading:
                current_parts.append(document_to_markdown(node))
            continue

        attrs = node.get("attrs") or {}
        nivel = attrs.get("level", 0) if isinstance(attrs, dict) else 0
        if nivel in (1, 2):
            if current_heading:
                heading_map[current_heading] = "\n".join(current_parts).strip()
            current_heading = _extract_plain_text(node.get("content", []))
            current_parts = []

    if current_heading:
        heading_map[current_heading] = "\n".join(current_parts).strip()

    _search_keys = {
        "visión del producto": "vision",
        "espacio del problema": "problem_space",
        "actores": "actors",
        "propuesta de valor": "value_proposition",
        "casos de uso": "use_cases",
        "capacidades principales": "core_capabilities",
        "reglas de negocio": "business_rules",
        "atributos de calidad": "quality_attributes",
        "alcance": "scope",
    }

    result: dict = {}
    for raw_title, content_str in heading_map.items():
        key = raw_title.strip().lower()
        field = _search_keys.get(key)
        if field:
            result[field] = content_str

    for field in _search_keys.values():
        result.setdefault(field, "")

    return result


def clean_document_tree(document: dict) -> dict:
    if "content" in document and isinstance(document["content"], list):
        document["content"] = _clean_content_nodes(document["content"])
    return document


def _clean_content_nodes(nodes: list[dict]) -> list[dict]:
    cleaned: list[dict] = []
    for node in nodes:
        if isinstance(node, dict):
            node_type = node.get("type", "")
            children = node.get("content")
            if isinstance(children, list):
                if node_type in ("paragraph", "heading"):
                    node["content"] = _dedup_bold_and_merge(children)
                else:
                    node["content"] = _clean_content_nodes(children)
            cleaned.append(node)
    return cleaned


def _dedup_bold_and_merge(nodes: list[dict]) -> list[dict]:
    result: list[dict] = []
    i = 0
    while i < len(nodes):
        node = dict(nodes[i])
        i += 1

        if node.get("type") != "text":
            result.append(node)
            continue

        text = node.get("text", "")
        marks = node.get("marks") or []
        has_bold = any(m.get("type") == "bold" for m in marks) if marks else False

        if not has_bold:
            if text.strip():
                result.append(node)
            continue

        bold_text = text.strip().rstrip(":").strip()
        merged_plain = None

        while i < len(nodes):
            peek = nodes[i]
            if not isinstance(peek, dict) or peek.get("type") != "text":
                break
            peek_text = peek.get("text", "")
            peek_marks = peek.get("marks") or []
            if any(m.get("type") == "bold" for m in peek_marks) if peek_marks else False:
                break
            stripped = peek_text.lstrip(": ").strip()
            if stripped.lower().startswith(bold_text.lower()):
                remainder = stripped[len(bold_text):].strip()
                if remainder:
                    merged_plain = remainder
                i += 1
                break
            else:
                merged_plain = peek_text
                i += 1
                break

        result.append({"type": "text", "text": text, "marks": marks})
        if merged_plain is not None:
            result.append({"type": "text", "text": merged_plain})

        while i < len(nodes):
            peek = nodes[i]
            if isinstance(peek, dict) and peek.get("type") == "text" and peek.get("text", "").strip() and not (peek.get("marks") or []):
                merged = dict(peek)
                i += 1
                if result and result[-1].get("type") == "text" and not result[-1].get("marks"):
                    prev = result[-1].get("text", "")
                    curr = merged.get("text", "")
                    needs = prev and not prev.endswith(" ") and not curr.startswith(" ")
                    result[-1]["text"] = prev + (" " if needs else "") + curr
                else:
                    result.append(merged)
            else:
                break

    return result
