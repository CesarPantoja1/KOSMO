import base64
from dataclasses import dataclass

from kosmo.contracts.auth.ports import UserRepository
from kosmo.contracts.auth.principal import Principal
from kosmo.contracts.auth.secrets import SecretCipher
from kosmo.contracts.integrations.github import (
    GitHubAuthenticationError,
    GitHubClientPort,
    GitHubPermissionError,
    UserGitHubIntegration,
    UserGitHubIntegrationRepository,
)
from kosmo.contracts.sdd.ids import UserId


@dataclass(frozen=True, slots=True)
class LinkGitHubAccountCommand:
    code: str


class LinkGitHubAccountUseCase:
    """Intercambia un código de autorización OAuth por un token de acceso y lo persiste cifrado."""

    def __init__(
        self,
        oauth_client: GitHubClientPort,
        cipher: SecretCipher,
        repo: UserGitHubIntegrationRepository,
        client_id: str,
        client_secret: str,
        user_repo: UserRepository | None = None,
    ) -> None:
        self._oauth_client = oauth_client
        self._cipher = cipher
        self._repo = repo
        self._client_id = client_id
        self._client_secret = client_secret
        self._user_repo = user_repo

    async def execute(self, principal: Principal, cmd: LinkGitHubAccountCommand) -> UserGitHubIntegration:
        if not self._client_id or not self._client_secret:
            raise GitHubAuthenticationError(
                "La integración con GitHub no está configurada en el servidor "
                "(faltan GITHUB_CLIENT_ID o GITHUB_CLIENT_SECRET en las variables de entorno)."
            )

        token = await self._oauth_client.exchange_oauth_code(
            client_id=self._client_id,
            client_secret=self._client_secret,
            code=cmd.code,
        )

        scopes = [s.strip() for s in token.scope.split(",") if s.strip()]
        if "repo" not in scopes:
            raise GitHubPermissionError("El token de acceso no tiene el permiso 'repo' requerido.")

        user = await self._oauth_client.get_authenticated_user(token.access_token)

        encrypted = self._cipher.encrypt(token.access_token.encode("utf-8"))
        encrypted_token_str = base64.b64encode(encrypted.ciphertext).decode("utf-8")

        integration = UserGitHubIntegration(
            user_id=UserId(principal.subject),
            github_username=user.login,
            encrypted_token=encrypted_token_str,
        )

        await self._repo.save(integration)

        if self._user_repo is not None:
            await self._user_repo.update_profile(
                user_id=principal.subject,
                name=user.name if user.name else None,
                avatar_url=user.avatar_url if user.avatar_url else None,
            )

        return integration
