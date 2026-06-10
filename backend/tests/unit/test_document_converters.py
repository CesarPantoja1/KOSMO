"""Tests unitarios para document_converters — lógica pura de dominio."""

from __future__ import annotations

from kosmo.domain.sdd.document_converters import (
    _fallback_markdown_to_document,
    _parse_inline_marks_fallback,
    document_to_markdown,
    extract_sections,
    markdown_to_document,
    slugify_spanish,
    validate_document_structure,
)


class TestSlugifySpanish:
    def test_slugify_accents(self) -> None:
        assert slugify_spanish("Visión del Producto") == "vision-del-producto"

    def test_slugify_enye(self) -> None:
        assert slugify_spanish("Diseño del Año") == "diseno-del-ano"

    def test_slugify_dieresis(self) -> None:
        assert slugify_spanish("Lingüística Aplicada") == "linguistica-aplicada"

    def test_slugify_mayusculas(self) -> None:
        assert slugify_spanish("ÁRBOL ÉPICO") == "arbol-epico"

    def test_slugify_simbolos(self) -> None:
        assert slugify_spanish("¿Qué es KOSMO?") == "que-es-kosmo"

    def test_slugify_puntuacion(self) -> None:
        assert slugify_spanish("  Espacios  múltiples -- guiones  ") == "espacios-multiples-guiones"


class TestExtractSections:
    def test_extract_sections_flat(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 1, "id": "intro"},
                    "content": [{"type": "text", "text": "Introducción"}],
                },
                {
                    "type": "heading",
                    "attrs": {"level": 2, "id": "detalle"},
                    "content": [{"type": "text", "text": "Detalle"}],
                },
            ],
        }
        sections = extract_sections(doc)
        assert len(sections) == 1
        assert sections[0]["title"] == "Introducción"
        assert sections[0]["level"] == 1
        assert len(sections[0]["children"]) == 1
        assert sections[0]["children"][0]["title"] == "Detalle"

    def test_extract_sections_nested(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Sección"}],
                },
                {
                    "type": "heading",
                    "attrs": {"level": 3},
                    "content": [{"type": "text", "text": "Sub-sección"}],
                },
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Otra sección"}],
                },
            ],
        }
        sections = extract_sections(doc)
        assert len(sections) == 2
        assert sections[0]["title"] == "Sección"
        assert len(sections[0]["children"]) == 1
        assert sections[1]["title"] == "Otra sección"

    def test_extract_sections_auto_anchor(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 1},
                    "content": [{"type": "text", "text": "Visión del Producto"}],
                },
            ],
        }
        sections = extract_sections(doc)
        assert sections[0]["anchor"] == "vision-del-producto"


class TestDocumentToMarkdown:
    def test_heading(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Visión del Producto"}],
                },
            ],
        }
        md = document_to_markdown(doc)
        assert md == "## Visión del Producto"

    def test_paragraph_with_marks(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Texto "},
                        {
                            "type": "text",
                            "text": "negrita",
                            "marks": [{"type": "bold"}],
                        },
                        {"type": "text", "text": " y "},
                        {
                            "type": "text",
                            "text": "cursiva",
                            "marks": [{"type": "italic"}],
                        },
                        {"type": "text", "text": "."},
                    ],
                },
            ],
        }
        md = document_to_markdown(doc)
        assert md == "Texto **negrita** y *cursiva*."

    def test_bullet_list(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Item 1"}],
                                }
                            ],
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Item 2"}],
                                }
                            ],
                        },
                    ],
                },
            ],
        }
        md = document_to_markdown(doc)
        assert "- Item 1" in md
        assert "- Item 2" in md

    def test_blockquote(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "blockquote",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Cita importante"}],
                        },
                    ],
                },
            ],
        }
        md = document_to_markdown(doc)
        assert md == "> Cita importante"

    def test_horizontal_rule(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {"type": "horizontalRule"},
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Después"}],
                },
            ],
        }
        md = document_to_markdown(doc)
        assert "---" in md

    def test_code_block(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "codeBlock",
                    "attrs": {"language": "python"},
                    "content": [{"type": "text", "text": "print('hola')"}],
                },
            ],
        }
        md = document_to_markdown(doc)
        assert "```python" in md
        assert "print('hola')" in md
        assert md.endswith("```")

    def test_strikethrough(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "obsoleto",
                            "marks": [{"type": "strike"}],
                        },
                    ],
                },
            ],
        }
        md = document_to_markdown(doc)
        assert md == "~~obsoleto~~"

    def test_inline_code(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "variable",
                            "marks": [{"type": "code"}],
                        },
                    ],
                },
            ],
        }
        md = document_to_markdown(doc)
        assert md == "`variable`"


class TestMarkdownToDocument:
    def test_heading(self) -> None:
        doc = markdown_to_document("# Introducción")
        assert doc["type"] == "doc"
        assert doc["content"][0]["type"] == "heading"
        assert doc["content"][0]["attrs"]["level"] == 1
        assert doc["content"][0]["content"][0]["text"] == "Introducción"

    def test_paragraph(self) -> None:
        doc = markdown_to_document("Este es un párrafo de prueba.")
        assert doc["content"][0]["type"] == "paragraph"

    def test_bold(self) -> None:
        doc = markdown_to_document("Texto **negrita** aquí.")
        paragraph = doc["content"][0]
        texts = [n for n in paragraph["content"] if n["type"] == "text"]
        marks = [n.get("marks") for n in texts]
        assert any(m and m[0]["type"] == "bold" for m in marks if m)

    def test_bullet_list(self) -> None:
        doc = markdown_to_document("- Item A\n- Item B")
        list_node = doc["content"][0]
        assert list_node["type"] == "bulletList"
        assert len(list_node["content"]) == 2

    def test_blockquote(self) -> None:
        doc = markdown_to_document("> Una cita")
        assert doc["content"][0]["type"] == "blockquote"

    def test_horizontal_rule(self) -> None:
        doc = markdown_to_document("---\n\ntexto después")
        types = [n["type"] for n in doc["content"]]
        assert "horizontalRule" in types

    def test_spanish_roundtrip(self) -> None:
        md = "## Visión del Producto\n\nUna solución **innovadora** para la gestión ágil."
        doc = markdown_to_document(md)
        result = document_to_markdown(doc)
        assert "Visión del Producto" in result
        assert "innovadora" in result
        assert "gestión ágil" in result


class TestFallbackMarkdownToDocument:
    def test_fallback_heading(self) -> None:
        doc = _fallback_markdown_to_document("# Título")
        assert doc["content"][0]["type"] == "heading"

    def test_fallback_list(self) -> None:
        doc = _fallback_markdown_to_document("- Uno\n- Dos")
        assert doc["content"][0]["type"] == "bulletList"

    def test_fallback_ordered_list(self) -> None:
        doc = _fallback_markdown_to_document("1. Primero\n2. Segundo")
        assert doc["content"][0]["type"] == "orderedList"


class TestValidateDocumentStructure:
    def test_valid_document(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Hola"}],
                },
            ],
        }
        findings = validate_document_structure(doc)
        assert findings == []

    def test_missing_content(self) -> None:
        doc: dict = {"type": "doc"}
        findings = validate_document_structure(doc)
        assert len(findings) > 0

    def test_invalid_node_type(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {"type": "invalidType", "content": [{"type": "text", "text": "x"}]},
            ],
        }
        findings = validate_document_structure(doc)
        assert len(findings) > 0

    def test_text_without_text_field(self) -> None:
        doc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text"}],
                },
            ],
        }
        findings = validate_document_structure(doc)
        assert len(findings) > 0


class TestParseInlineMarksFallback:
    def test_bold(self) -> None:
        result = _parse_inline_marks_fallback("Hola **mundo**")
        assert any(
            n.get("marks") and n["marks"][0]["type"] == "bold" for n in result if n.get("marks")
        )

    def test_italic(self) -> None:
        result = _parse_inline_marks_fallback("Hola *mundo*")
        assert any(
            n.get("marks") and n["marks"][0]["type"] == "italic" for n in result if n.get("marks")
        )

    def test_strike(self) -> None:
        result = _parse_inline_marks_fallback("Hola ~~mundo~~")
        assert any(
            n.get("marks") and n["marks"][0]["type"] == "strike" for n in result if n.get("marks")
        )
