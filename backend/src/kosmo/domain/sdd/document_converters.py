from __future__ import annotations

import re

from kosmo.contracts.sdd.document import (
    DocumentNode,
    MarkType,
    RichTextDocument,
    SectionHeading,
    TextMark,
)

_SLUG_RE = re.compile(r"[^\w\s-]", re.UNICODE)
_SPACES_RE = re.compile(r"[-\s]+")


def slugify_spanish(text: str) -> str:
    normalized = _SLUG_RE.sub("", text.lower().strip())
    return _SPACES_RE.sub("-", normalized)


def document_to_markdown(doc: RichTextDocument) -> str:
    lines: list[str] = []
    for node in doc.nodes:
        line = _node_to_markdown(node)
        if line:
            lines.append(line)
    return "\n\n".join(lines)


def markdown_to_document(markdown: str) -> RichTextDocument:
    nodes: list[DocumentNode] = []
    sections = markdown.split("\n\n")
    for section in sections:
        section = section.strip()
        if not section:
            continue
        lines = section.split("\n")
        if lines and lines[0].startswith("#"):
            heading_text = lines[0].lstrip("#").strip()
            level = len(lines[0]) - len(lines[0].lstrip("#"))
            slug = slugify_spanish(heading_text)
            heading = SectionHeading(text=heading_text, level=level, slug=slug)
            content = "\n".join(lines[1:]).strip()
            nodes.append(DocumentNode(type="heading", heading=heading, content=content))
        else:
            nodes.append(DocumentNode(type="paragraph", content=section))
    return RichTextDocument(nodes=nodes)


def _node_to_markdown(node: DocumentNode) -> str:
    if node.type == "heading" and node.heading:
        prefix = "#" * node.heading.level
        parts = [f"{prefix} {node.heading.text}"]
        if node.content:
            parts.append(node.content)
        for child in node.children:
            parts.append(_node_to_markdown(child))
        return "\n".join(parts)

    if node.type == "paragraph":
        text = _apply_marks(node.content, node.marks)
        parts = [text]
        for child in node.children:
            parts.append(_node_to_markdown(child))
        return "\n".join(parts)

    return node.content


def _apply_marks(text: str, marks: list[TextMark]) -> str:
    for mark in marks:
        if mark.type == MarkType.bold:
            text = f"**{text}**"
        elif mark.type == MarkType.italic:
            text = f"*{text}*"
        elif mark.type == MarkType.code:
            text = f"`{text}`"
        elif mark.type == MarkType.link:
            href = mark.attrs.get("href", "")
            text = f"[{text}]({href})"
    return text


def validate_document_structure(
    doc: RichTextDocument, required_sections: list[str], min_words_per_section: int = 50
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    found_sections: dict[str, int] = {}

    for node in doc.nodes:
        if node.type == "heading" and node.heading:
            heading_lower = node.heading.text.lower()
            for required in required_sections:
                required_lower = required.lower()
                if required_lower in heading_lower:
                    word_count = len(node.content.split()) if node.content else 0
                    found_sections[required] = word_count

    for section in required_sections:
        if section not in found_sections:
            errors.append(f"Seccion faltante: {section}")
        elif found_sections[section] < min_words_per_section:
            errors.append(
                f"Seccion '{section}' tiene solo {found_sections[section]} palabras "
                f"(minimo {min_words_per_section})"
            )

    return len(errors) == 0, errors
