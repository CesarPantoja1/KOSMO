from pydantic import BaseModel, Field


class TextMark(BaseModel):
    """Marca de formato inline (bold, italic, strike, code, link)."""

    type: str
    attrs: dict[str, str] | None = None


class DocumentNode(BaseModel):
    """Nodo del árbol de documento (compatible con ProseMirror/TipTap)."""

    type: str
    attrs: dict[str, object] | None = None
    content: list["DocumentNode"] | None = None
    marks: list[TextMark] | None = None
    text: str | None = None


class RichTextDocument(BaseModel):
    """Documento enriquecido completo — fuente de verdad del editor."""

    type: str = "doc"
    content: list[DocumentNode]
    version: int = Field(default=1, ge=1)


class SectionHeading(BaseModel):
    """Entrada del índice de navegación lateral (anclas)."""

    title: str
    anchor: str
    level: int
    children: list["SectionHeading"] = []


class DocumentResponse(BaseModel):
    """Respuesta de API: documento + índice de navegación."""

    document: RichTextDocument
    sections: list[SectionHeading]
    updated_at: str
