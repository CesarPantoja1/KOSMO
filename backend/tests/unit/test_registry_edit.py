from __future__ import annotations

import pytest

from kosmo.domain.codegen.registry_edit import remove_feature_from_registry

_STANDARD_REGISTRY = """import type { FeatureManifest } from "@/features/types";

import { registrarProductos } from "@/features/registrar-productos/manifest";
import { listarVentas } from "@/features/listar-ventas/manifest";

export const features: FeatureManifest[] = [
  registrarProductos,
  listarVentas,
];
"""


@pytest.mark.unit
def test_remove_feature_from_registry_quita_import_y_entrada() -> None:
    # Arrange
    content = _STANDARD_REGISTRY

    # Act
    result = remove_feature_from_registry(content, "registrar-productos")

    # Assert — el import y la entrada del array desaparecen; el resto queda intacto
    assert 'from "@/features/registrar-productos/manifest"' not in result
    assert "registrarProductos," not in result
    assert 'from "@/features/listar-ventas/manifest"' in result
    assert "listarVentas," in result
    assert "export const features: FeatureManifest[] = [" in result


@pytest.mark.unit
def test_remove_feature_from_registry_con_import_aliased() -> None:
    # Arrange
    content = """import type { FeatureManifest } from "@/features/types";

import { registrarProductos as rp } from "@/features/registrar-productos/manifest";

export const features: FeatureManifest[] = [
  rp,
];
"""

    # Act
    result = remove_feature_from_registry(content, "registrar-productos")

    # Assert — el alias también se elimina del array
    assert 'from "@/features/registrar-productos/manifest"' not in result
    assert "rp," not in result
    assert "export const features" in result


@pytest.mark.unit
def test_remove_feature_from_registry_sin_import_usa_fallback_por_referencia() -> None:
    # Arrange — el agente registró la feature sin seguir la convención exacta
    content = """import type { FeatureManifest } from "@/features/types";

import { x } from "@/features/registrar-productos/logic";

export const features: FeatureManifest[] = [
  x,
];
"""

    # Act
    result = remove_feature_from_registry(content, "registrar-productos")

    # Assert — cualquier línea que referencie el slice del slug desaparece
    assert "@/features/registrar-productos" not in result
    assert "export const features" in result


@pytest.mark.unit
def test_remove_feature_from_registry_sin_referencias_no_cambia_nada() -> None:
    # Arrange
    content = """import type { FeatureManifest } from "@/features/types";

import { listarVentas } from "@/features/listar-ventas/manifest";

export const features: FeatureManifest[] = [
  listarVentas,
];
"""

    # Act
    result = remove_feature_from_registry(content, "registrar-productos")

    # Assert — contenido intacto
    assert result == content
