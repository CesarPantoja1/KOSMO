from fastapi import Request

from kosmo.application.ai.manage_ai_preferences import ManageAIPreferencesUseCase
from kosmo.application.ai.validate_ai_connection import ValidateAIConnectionUseCase
from kosmo.infrastructure.api.dependencies.container import get_container
from kosmo.infrastructure.llm.connection_tester import HttpAIConnectionTester


def get_manage_ai_preferences_use_case(request: Request) -> ManageAIPreferencesUseCase:
    container = get_container(request)
    if container.auth is None:
        raise RuntimeError("Authentication must be enabled to manage AI preferences")
    return ManageAIPreferencesUseCase(
        config_repo=container.repos.user_ai_configs,
        cipher=container.auth.secret_cipher,
    )


def get_validate_ai_connection_use_case(request: Request) -> ValidateAIConnectionUseCase:
    container = get_container(request)
    cipher = container.auth.secret_cipher if container.auth else None
    return ValidateAIConnectionUseCase(
        connection_tester=HttpAIConnectionTester(),
        config_repo=container.repos.user_ai_configs,
        cipher=cipher,
    )
