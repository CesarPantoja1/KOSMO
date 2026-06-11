from __future__ import annotations

import re
import unicodedata


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


def _strip_accents(text: str) -> str:
    normalizada = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalizada if not unicodedata.combining(c))


def clean_markdown(markdown: str) -> str:
    markdown = re.sub(r":{2,}", ":", markdown)
    markdown = re.sub(r":\s+:", ":", markdown)
    return markdown


# ── Funciones de arbol ProseMirror (solo para requirements) ──


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
    i = 0
    while i < len(children):
        child = children[i]
        ttype = child.type

        if ttype == "text":
            nodos.append({"type": "text", "text": child.content})
            i += 1
        elif ttype in ("strong_open", "em_open", "s_open"):
            close_type = ttype.replace("_open", "_close")
            _mark_map = {"strong_open": "bold", "em_open": "italic", "s_open": "strike"}
            mark_type = _mark_map[ttype]
            j = i + 1
            while j < len(children) and children[j].type != close_type:
                j += 1
            contenido = _process_inline_children(children[i + 1 : j])
            for c in contenido:
                existing = c.get("marks") or []
                existing.append({"type": mark_type})
                c["marks"] = existing
            nodos.extend(contenido)
            i = j + 1
        elif ttype in ("strong_close", "em_close", "s_close"):
            i += 1
        elif ttype == "code_inline":
            nodos.append(
                {
                    "type": "text",
                    "text": child.content,
                    "marks": [{"type": "code"}],
                }
            )
            i += 1
        elif ttype == "link_open":
            j = i + 1
            while j < len(children) and children[j].type != "link_close":
                j += 1
            href = child.attrs.get("href", "") if child.attrs else ""
            contenido = _process_inline_children(children[i + 1 : j])
            for c in contenido:
                existing = c.get("marks") or []
                existing.append({"type": "link", "attrs": {"href": href}})
                c["marks"] = existing
            nodos.extend(contenido)
            i = j + 1
        elif ttype == "link_close":
            i += 1
        elif ttype == "softbreak" and nodos and nodos[-1].get("type") == "text":
            nodos[-1]["text"] += " "
            i += 1
        elif ttype == "hardbreak":
            nodos.append({"type": "hardBreak"})
            i += 1
        else:
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
        r"(\*\*\*(.+?)\*\*\*)|"
        r"(\*\*(.+?)\*\*)|"
        r"(~~(.+?)~~)|"
        r"(\*(.+?)\*)|"
        r"(`(.+?)`)"
    )

    ultimo = 0
    for m in patron.finditer(texto):
        inicio, fin = m.span()
        if inicio > ultimo:
            nodos.append({"type": "text", "text": texto[ultimo:inicio]})

        if m.group(1):
            nodos.append(
                {
                    "type": "text",
                    "text": m.group(2),
                    "marks": [{"type": "bold"}, {"type": "italic"}],
                }
            )
        elif m.group(3):
            nodos.append(
                {
                    "type": "text",
                    "text": m.group(4),
                    "marks": [{"type": "bold"}],
                }
            )
        elif m.group(5):
            nodos.append(
                {
                    "type": "text",
                    "text": m.group(6),
                    "marks": [{"type": "strike"}],
                }
            )
        elif m.group(7):
            nodos.append(
                {
                    "type": "text",
                    "text": m.group(8),
                    "marks": [{"type": "italic"}],
                }
            )
        elif m.group(9):
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

    for n in nodos:
        if n.get("type") == "text" and "text" in n:
            n["text"] = re.sub(r":{2,}", ":", n["text"])

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
