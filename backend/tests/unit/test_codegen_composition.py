from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import async_sessionmaker

from kosmo.application.codegen.generate_feature_implementation import GenerateFeatureImplementationUseCase
from kosmo.config import Settings
from kosmo.infrastructure.api.composition import build_app_components
from kosmo.infrastructure.api.composition.codegen import CodegenComponents, build_codegen_components
from kosmo.infrastructure.codegen.opencode_client import OpenCodeHttpClient
from kosmo.infrastructure.codegen.workspace import LocalWorkspaceManager
from kosmo.infrastructure.persistence.postgres.registry import RepositoryRegistry
from kosmo.infrastructure.sandbox.code_runner import SubprocessCodeRunner
from kosmo.infrastructure.sandbox.remote_code_runner import RemoteCodeRunner

_CODEGEN_ENV_VARS = (
    "OPENCODE_BASE_URL",
    "OPENCODE_SERVER_PASSWORD",
    "OPENCODE_SERVER_USERNAME",
    "OPENCODE_MODEL",
    "KOSMO_WORKSPACES_DIR",
    "KOSMO_MCP_BASE_URL",
    "CODE_RUNNER_BASE_URL",
    "CODE_RUNNER_TOKEN",
)


@pytest.fixture(autouse=True)
def _minimal_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/kosmo_test")
    monkeypatch.setenv("LLM_PROVIDER", "noop")
    monkeypatch.setenv("LLM_MODEL", "noop")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "none")
    for var in _CODEGEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def _make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)


def _make_repos() -> RepositoryRegistry:
    return RepositoryRegistry.build(MagicMock(spec=async_sessionmaker))


@pytest.mark.unit
def test_build_codegen_components_cablea_use_case_con_adaptadores() -> None:
    # Arrange
    settings = _make_settings()
    repos = _make_repos()

    # Act
    components = build_codegen_components(settings, repos)

    # Assert
    assert isinstance(components, CodegenComponents)
    use_case = components.generate_feature_implementation
    assert isinstance(use_case, GenerateFeatureImplementationUseCase)
    assert isinstance(components.opencode_client, OpenCodeHttpClient)
    assert isinstance(components.workspace_manager, LocalWorkspaceManager)
    assert isinstance(components.code_runner, SubprocessCodeRunner)
    assert use_case._feature_repo is repos.features
    assert use_case._requirement_repo is repos.requirements
    assert use_case._activity_diagram_repo is repos.diagrams
    assert use_case._workspace_manager is components.workspace_manager
    assert use_case._opencode_client is components.opencode_client
    assert use_case._code_runner is components.code_runner
    assert use_case._implementation_repo is repos.implementations
    assert use_case._register_traceability._traceability_repo is repos.traceability


@pytest.mark.unit
def test_build_codegen_components_propaga_settings_a_adaptadores(tmp_path) -> None:
    # Arrange
    workspaces_dir = tmp_path / "workspaces"
    settings = _make_settings(
        opencode_base_url="http://opencode.local:4096",
        opencode_server_password=SecretStr("tok"),
        opencode_server_username="kosmo-agent",
        opencode_model="deepseek/deepseek-v4-flash",
        kosmo_workspaces_dir=workspaces_dir,
        kosmo_mcp_base_url="http://api.local:8000/mcp",
    )
    repos = _make_repos()

    # Act
    components = build_codegen_components(settings, repos)

    # Assert
    assert components.opencode_client._base_url == "http://opencode.local:4096"
    assert components.opencode_client._server_username == "kosmo-agent"
    assert components.opencode_client._server_password == "tok"
    assert components.opencode_client._model == "deepseek/deepseek-v4-flash"
    assert components.workspace_manager._workspaces_root == workspaces_dir
    assert components.workspace_manager._mcp_url == "http://api.local:8000/mcp"
    assert components.workspace_manager._workspace_repo is repos.workspaces
    assert components.workspace_manager._project_repo is repos.projects


@pytest.mark.unit
def test_build_codegen_components_uses_remote_runner_when_configured(tmp_path) -> None:
    settings = _make_settings(
        kosmo_workspaces_dir=tmp_path / "workspaces",
        code_runner_base_url="http://runner.local:8081",
        code_runner_token=SecretStr("runner-token"),
    )

    components = build_codegen_components(settings, _make_repos())

    assert isinstance(components.code_runner, RemoteCodeRunner)
    assert components.code_runner._base_url == "http://runner.local:8081"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_app_components_incluye_codegen() -> None:
    # Arrange
    settings = _make_settings()

    # Act
    container = build_app_components(settings)

    try:
        # Assert
        assert isinstance(container.codegen, CodegenComponents)
        assert isinstance(
            container.codegen.generate_feature_implementation,
            GenerateFeatureImplementationUseCase,
        )
    finally:
        await container.close()
