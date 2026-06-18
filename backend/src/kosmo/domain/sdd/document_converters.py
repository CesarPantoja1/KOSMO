from __future__ import annotations

import re
import unicodedata

from kosmo.contracts.sdd.document import DocumentNode, RichTextDocument, SectionHeading


def slugify_spanish(text: str) -> str:
    """Convierte texto en español a un slug URL-safe."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def document_to_markdown(doc: RichTextDocument) -> str:
    """Convierte un RichTextDocument a markdown plano."""
    if not doc.nodes:
        return ""

    lines: list[str] = []
    for node in doc.nodes:
        if node.type == "heading" and node.heading:
            prefix = "#" * node.heading.level
            lines.append(f"{prefix} {node.heading.text}")
            if node.content:
                lines.append("")
                lines.append(node.content)
        elif node.content:
            lines.append(node.content)

    return "\n\n".join(lines)


def markdown_to_document(markdown: str) -> RichTextDocument:
    """Parsea markdown a un RichTextDocument con nodos heading + párrafo."""
    if not markdown or not markdown.strip():
        return RichTextDocument()

    nodes: list[DocumentNode] = []
    lines = markdown.strip().split("\n")
    current_heading: SectionHeading | None = None
    current_content_lines: list[str] = []

    heading_re = re.compile(r"^(#{1,6})\s+(.+)$")

    def _flush() -> None:
        nonlocal current_heading, current_content_lines
        content = "\n".join(current_content_lines).strip()
        if current_heading is not None:
            nodes.append(
                DocumentNode(
                    type="heading",
                    heading=current_heading,
                    content=content,
                )
            )
        elif content:
            nodes.append(
                DocumentNode(
                    type="paragraph",
                    content=content,
                )
            )
        current_heading = None
        current_content_lines = []

    for line in lines:
        m = heading_re.match(line)
        if m:
            _flush()
            level = len(m.group(1))
            text = m.group(2).strip()
            current_heading = SectionHeading(
                text=text,
                level=level,
                slug=slugify_spanish(text),
            )
        else:
            current_content_lines.append(line)

    _flush()

    return RichTextDocument(nodes=nodes)
