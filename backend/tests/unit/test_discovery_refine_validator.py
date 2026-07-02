import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.contracts.sdd.document import DocumentNode, RichTextDocument, SectionHeading
from kosmo.domain.pipeline.phase_validators.discovery_refine_validator import (
    validate_business_level,
)


@pytest.mark.unit
def test_validate_business_level_passes_for_business_document() -> None:
    # Arrange
    doc = RichTextDocument(
        nodes=[
            DocumentNode(
                type="heading",
                heading=SectionHeading(text="Vision del producto", level=2, slug="vision"),
                content="El producto ayuda a las familias a repartir gastos de forma justa.",
            ),
        ]
    )

    # Act
    result = validate_business_level(doc)

    # Assert
    assert result.is_valid is True
    assert result.errors == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "term",
    [
        "API",
        "base de datos",
        "backend",
        "PostgreSQL",
        "Docker",
        "microservicios",
    ],
)
def test_validate_business_level_flags_technical_term(term: str) -> None:
    # Arrange
    doc = RichTextDocument(
        nodes=[
            DocumentNode(
                type="heading",
                heading=SectionHeading(text="Metas del producto", level=2, slug="metas"),
                content=f"El sistema usa {term} para operar.",
            ),
        ]
    )

    # Act
    result = validate_business_level(doc)

    # Assert
    assert result.is_valid is False
    assert any(term in e for e in result.errors)


@pytest.mark.unit
def test_validate_business_level_flags_technical_term_in_heading() -> None:
    # Arrange
    doc = RichTextDocument(
        nodes=[
            DocumentNode(
                type="heading",
                heading=SectionHeading(text="Arquitectura del API", level=2, slug="arquitectura"),
                content="Contenido de negocio sin jerga.",
            ),
        ]
    )

    # Act
    result = validate_business_level(doc)

    # Assert
    assert result.is_valid is False
    assert any("API" in e for e in result.errors)


@pytest.mark.unit
def test_validate_business_level_passes_for_empty_document() -> None:
    # Arrange
    doc = RichTextDocument(nodes=[])

    # Act
    result = validate_business_level(doc)

    # Assert
    assert result.is_valid is True
    assert result.errors == []
