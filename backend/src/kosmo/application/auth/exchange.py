from dataclasses import dataclass
from datetime import UTC, datetime

from kosmo.application.auth.use_cases import IssueTokenPair
from kosmo.contracts.auth import (
    AuthorizationCodeError,
    AuthorizationCodeStore,
    PkceMismatchError,
    TokenPair,
)
from kosmo.domain.auth import verify_s256


@dataclass(frozen=True, slots=True)
class ExchangeAuthorizationCode:
    authorization_code_store: AuthorizationCodeStore
    issue_token_pair: IssueTokenPair

    async def execute(self, *, code: str, code_verifier: str) -> TokenPair:
        entry = await self.authorization_code_store.consume(code)
        if entry is None:
            raise AuthorizationCodeError("Código de autorización inválido o expirado")
        if entry.expires_at < datetime.now(UTC):
            raise AuthorizationCodeError("Código de autorización expirado")
        if not verify_s256(code_verifier, entry.code_challenge):
            raise PkceMismatchError("El code_verifier no coincide con el code_challenge")
        return await self.issue_token_pair.execute(
            subject=entry.subject,
            scopes=entry.scopes,
        )
