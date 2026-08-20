from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from pydantic import SecretStr

from kosmo.config import Settings

_CODEGEN_ENV_VARS = (
    "OPENCODE_BASE_URL",
    "OPENCODE_SERVER_PASSWORD",
    "OPENCODE_SERVER_USERNAME",
    "OPENCODE_MODEL",
    "KOSMO_WORKSPACES_DIR",
    "KOSMO_MCP_BASE_URL",
)


@pytest.fixture(autouse=True)
def _minimal_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aísla la construcción de Settings del entorno real y limpia las variables de codegen."""
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/kosmo_test")
    monkeypatch.setenv("LLM_PROVIDER", "noop")
    monkeypatch.setenv("LLM_MODEL", "noop")
    for var in _CODEGEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def _make_settings() -> Settings:
    return Settings(_env_file=None)


@pytest.mark.unit
def test_codegen_settings_usan_valores_por_defecto() -> None:
    # Arrange
    expected_workspaces_dir = Path(tempfile.gettempdir()) / "kosmo-workspaces"

    # Act
    settings = _make_settings()

    # Assert
    assert settings.opencode_base_url == "http://127.0.0.1:4096"
    assert settings.opencode_server_password is None
    assert settings.opencode_server_username == "opencode"
    assert settings.opencode_model is None
    assert settings.kosmo_workspaces_dir == expected_workspaces_dir
    assert settings.kosmo_mcp_base_url == "http://127.0.0.1:8000/mcp"


@pytest.mark.unit
def test_codegen_settings_se_leen_desde_entorno(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    workspace_dir = tmp_path / "workspaces"
    monkeypatch.setenv("OPENCODE_BASE_URL", "http://opencode.local:4096")
    monkeypatch.setenv("OPENCODE_SERVER_PASSWORD", "tok-secreto")
    monkeypatch.setenv("OPENCODE_SERVER_USERNAME", "kosmo-agent")
    monkeypatch.setenv("OPENCODE_MODEL", "deepseek/deepseek-v4-flash")
    monkeypatch.setenv("KOSMO_WORKSPACES_DIR", str(workspace_dir))
    monkeypatch.setenv("KOSMO_MCP_BASE_URL", "http://api.local:8000/mcp")

    # Act
    settings = _make_settings()

    # Assert
    assert settings.opencode_base_url == "http://opencode.local:4096"
    assert settings.opencode_server_password == SecretStr("tok-secreto")
    assert settings.opencode_server_username == "kosmo-agent"
    assert settings.opencode_model == "deepseek/deepseek-v4-flash"
    assert settings.kosmo_workspaces_dir == workspace_dir
    assert settings.kosmo_mcp_base_url == "http://api.local:8000/mcp"


@pytest.mark.unit
def test_codegen_settings_workspaces_dir_acepta_ruta_relativa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    relative_dir = "workspaces"
    monkeypatch.setenv("KOSMO_WORKSPACES_DIR", relative_dir)

    # Act
    settings = _make_settings()

    # Assert
    assert settings.kosmo_workspaces_dir == Path(relative_dir)
