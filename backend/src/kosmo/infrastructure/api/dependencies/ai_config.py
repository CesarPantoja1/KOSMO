from fastapi import Request

from kosmo.application.ai.manage_ai_preferences import ManageAIPreferencesUseCase
from kosmo.application.ai.validate_ai_connection import ValidateAIConnectionUseCase
from kosmo.contracts.auth import SecretCipher
from kosmo.infrastructure.api.dependencies.container import get_container
from kosmo.infrastructure.llm.connection_tester import HttpAIConnectionTester
from kosmo.infrastructure.security import FernetSecretCipher


def _resolve_cipher(request: Request) -> SecretCipher:
    container = get_container(request)
    if container.auth is not None:
        return container.auth.secret_cipher
    if container.settings.fernet_master_key is not None:
        return FernetSecretCipher(container.settings.fernet_master_key.get_secret_value())
    raise RuntimeError("Fernet master key is required to manage AI preferences")


def get_manage_ai_preferences_use_case(request: Request) -> ManageAIPreferencesUseCase:
    container = get_container(request)
    return ManageAIPreferencesUseCase(
        config_repo=container.repos.user_ai_configs,
        cipher=_resolve_cipher(request),
    )


def get_validate_ai_connection_use_case(request: Request) -> ValidateAIConnectionUseCase:
    container = get_container(request)
    return ValidateAIConnectionUseCase(
        connection_tester=HttpAIConnectionTester(),
        config_repo=container.repos.user_ai_configs,
        cipher=_resolve_cipher(request),
    )
