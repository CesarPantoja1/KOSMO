from __future__ import annotations

from dataclasses import dataclass

from kosmo.application.codegen.delete_feature_code import DeleteFeatureCodeUseCase
from kosmo.application.codegen.generate_feature_implementation import (
    GenerateFeatureImplementationUseCase,
)
from kosmo.application.codegen.validate_workspace import ValidateWorkspaceUseCase
from kosmo.config import Settings
from kosmo.contracts.codegen import CodeRunnerPort
from kosmo.infrastructure.codegen.opencode_client import OpenCodeHttpClient
from kosmo.infrastructure.codegen.workspace import LocalWorkspaceManager
from kosmo.infrastructure.persistence.postgres.registry import RepositoryRegistry
from kosmo.infrastructure.sandbox.code_runner import SubprocessCodeRunner
from kosmo.infrastructure.sandbox.remote_code_runner import RemoteCodeRunner


@dataclass(frozen=True, slots=True)
class CodegenComponents:
    """Dependencias cableadas del subsistema de generación de código."""

    generate_feature_implementation: GenerateFeatureImplementationUseCase
    validate_workspace: ValidateWorkspaceUseCase
    delete_feature_code: DeleteFeatureCodeUseCase
    workspace_manager: LocalWorkspaceManager
    opencode_client: OpenCodeHttpClient
    code_runner: CodeRunnerPort


def build_codegen_components(settings: Settings, repos: RepositoryRegistry) -> CodegenComponents:
    opencode_client = OpenCodeHttpClient(
        base_url=settings.opencode_base_url,
        server_username=settings.opencode_server_username,
        server_password=(
            settings.opencode_server_password.get_secret_value()
            if settings.opencode_server_password is not None
            else None
        ),
        model=settings.opencode_model,
    )
    if settings.code_runner_base_url and settings.code_runner_token is not None:
        code_runner: CodeRunnerPort = RemoteCodeRunner(
            settings.code_runner_base_url,
            settings.code_runner_token.get_secret_value(),
        )
    else:
        code_runner = SubprocessCodeRunner()
    workspace_manager = LocalWorkspaceManager(
        workspaces_root=settings.kosmo_workspaces_dir,
        workspace_repo=repos.workspaces,
        mcp_url=settings.kosmo_mcp_base_url,
        project_repo=repos.projects,
        code_runner=code_runner,
    )
    use_case = GenerateFeatureImplementationUseCase(
        feature_repo=repos.features,
        requirement_repo=repos.requirements,
        activity_diagram_repo=repos.diagrams,
        workspace_manager=workspace_manager,
        opencode_client=opencode_client,
        code_runner=code_runner,
        implementation_repo=repos.implementations,
        traceability_repo=repos.traceability,
        project_repo=repos.projects,
        document_repo=repos.documents,
    )
    return CodegenComponents(
        generate_feature_implementation=use_case,
        validate_workspace=ValidateWorkspaceUseCase(
            code_runner=code_runner,
            workspace_manager=workspace_manager,
        ),
        delete_feature_code=DeleteFeatureCodeUseCase(
            workspace_manager=workspace_manager,
            code_runner=code_runner,
            opencode_client=opencode_client,
            implementation_repo=repos.implementations,
        ),
        workspace_manager=workspace_manager,
        opencode_client=opencode_client,
        code_runner=code_runner,
    )
