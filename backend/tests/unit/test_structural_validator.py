from __future__ import annotations

import pytest

from kosmo.domain.codegen.structural_validator import (
    StructuralValidationResult,
    validate_feature_structure,
)


@pytest.mark.unit
def test_validate_feature_structure_all_present() -> None:
    # Arrange
    slug = "registrar-gastos"
    files = [
        "src/app/registrar-gastos/page.tsx",
        "src/features/registrar-gastos/manifest.ts",
        "src/features/registrar-gastos/logic.ts",
        "src/lib/feature-registry.ts",
    ]
    registry_content = (
        'import { gastosManifest } from "@/features/registrar-gastos/manifest";\n'
        "export const featureRegistry = [gastosManifest];\n"
    )

    # Act
    result = validate_feature_structure(
        feature_slug=slug,
        files=files,
        registry_content=registry_content,
    )

    # Assert
    assert isinstance(result, StructuralValidationResult)
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert result.missing_page is False
    assert result.missing_slice is False
    assert result.missing_registry is False


@pytest.mark.unit
def test_validate_feature_structure_missing_page() -> None:
    # Arrange
    slug = "registrar-gastos"
    files = [
        "src/features/registrar-gastos/manifest.ts",
        "src/features/registrar-gastos/logic.ts",
        "src/lib/feature-registry.ts",
    ]
    registry_content = 'import { gastosManifest } from "@/features/registrar-gastos/manifest";\n'

    # Act
    result = validate_feature_structure(
        feature_slug=slug,
        files=files,
        registry_content=registry_content,
    )

    # Assert
    assert result.is_valid is False
    assert result.missing_page is True
    assert result.missing_slice is False
    assert result.missing_registry is False
    assert any("page.tsx" in err for err in result.errors)


@pytest.mark.unit
def test_validate_feature_structure_missing_slice() -> None:
    # Arrange
    slug = "registrar-gastos"
    files = [
        "src/app/registrar-gastos/page.tsx",
        "src/lib/feature-registry.ts",
    ]
    registry_content = 'import { gastosManifest } from "@/features/registrar-gastos/manifest";\n'

    # Act
    result = validate_feature_structure(
        feature_slug=slug,
        files=files,
        registry_content=registry_content,
    )

    # Assert
    assert result.is_valid is False
    assert result.missing_page is False
    assert result.missing_slice is True
    assert result.missing_registry is False
    assert any("src/features/registrar-gastos/" in err for err in result.errors)


@pytest.mark.unit
def test_validate_feature_structure_missing_registry() -> None:
    # Arrange
    slug = "registrar-gastos"
    files = [
        "src/app/registrar-gastos/page.tsx",
        "src/features/registrar-gastos/manifest.ts",
        "src/lib/feature-registry.ts",
    ]
    registry_content = "export const featureRegistry = [];\n"

    # Act
    result = validate_feature_structure(
        feature_slug=slug,
        files=files,
        registry_content=registry_content,
    )

    # Assert
    assert result.is_valid is False
    assert result.missing_page is False
    assert result.missing_slice is False
    assert result.missing_registry is True
    assert any("feature-registry.ts" in err for err in result.errors)


@pytest.mark.unit
def test_validate_feature_structure_missing_all() -> None:
    # Arrange
    slug = "registrar-gastos"
    files = ["src/other.ts"]
    registry_content = ""

    # Act
    result = validate_feature_structure(
        feature_slug=slug,
        files=files,
        registry_content=registry_content,
    )

    # Assert
    assert result.is_valid is False
    assert result.missing_page is True
    assert result.missing_slice is True
    assert result.missing_registry is True
    assert len(result.errors) == 3


@pytest.mark.unit
def test_validate_feature_structure_handles_windows_separators() -> None:
    # Arrange
    slug = "reportes-mensuales"
    files = [
        r"src\app\reportes-mensuales\page.tsx",
        r"src\features\reportes-mensuales\components\Chart.tsx",
        r"src\lib\feature-registry.ts",
    ]
    registry_content = 'import { reportes } from "@/features/reportes-mensuales/manifest";'

    # Act
    result = validate_feature_structure(
        feature_slug=slug,
        files=files,
        registry_content=registry_content,
    )

    # Assert
    assert result.is_valid is True
    assert result.missing_page is False
    assert result.missing_slice is False
    assert result.missing_registry is False


@pytest.mark.unit
def test_validate_feature_structure_missing_export_default() -> None:
    # Arrange
    slug = "registrar-gastos"
    files = [
        "src/app/registrar-gastos/page.tsx",
        "src/features/registrar-gastos/manifest.ts",
        "src/features/registrar-gastos/logic.ts",
        "src/lib/feature-registry.ts",
    ]
    registry_content = 'import { gastosManifest } from "@/features/registrar-gastos/manifest";\n'
    page_content = "export function Page() { return <div>Gastos</div>; }"

    # Act
    result = validate_feature_structure(
        feature_slug=slug,
        files=files,
        registry_content=registry_content,
        page_content=page_content,
    )

    # Assert
    assert result.is_valid is False
    assert result.missing_page is True
    assert any("export default" in err for err in result.errors)


@pytest.mark.unit
def test_validate_feature_structure_with_valid_export_default() -> None:
    # Arrange
    slug = "registrar-gastos"
    files = [
        "src/app/registrar-gastos/page.tsx",
        "src/features/registrar-gastos/manifest.ts",
        "src/features/registrar-gastos/logic.ts",
        "src/lib/feature-registry.ts",
    ]
    registry_content = 'import { gastosManifest } from "@/features/registrar-gastos/manifest";\n'
    page_content = "export default function GastosPage() { return <div>Gastos</div>; }"

    # Act
    result = validate_feature_structure(
        feature_slug=slug,
        files=files,
        registry_content=registry_content,
        page_content=page_content,
    )

    # Assert
    assert result.is_valid is True
    assert result.missing_page is False
    assert len(result.errors) == 0
