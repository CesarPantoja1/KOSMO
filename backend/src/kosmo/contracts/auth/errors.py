class AuthError(Exception):
    """Raíz de errores del flujo de autenticación."""


class InvalidTokenError(AuthError):
    """Token mal formado, firma inválida o claims que no superan validación."""


class TokenExpiredError(AuthError):
    """Token sintácticamente válido cuyo `exp` ya transcurrió."""


class TokenRevokedError(AuthError):
    """Token revocado de forma explícita antes de expirar."""


class MissingTokenError(AuthError):
    """No se presentó credencial en la solicitud."""


class TokenReusedError(AuthError):
    """Refresh token reutilizado: indica posible compromiso. La familia se revoca."""


class UserAlreadyExistsError(AuthError):
    """Email ya registrado."""


class InvalidCredentialsError(AuthError):
    """Email no encontrado, contraseña incorrecta o usuario deshabilitado."""


class AuthorizationCodeError(AuthError):
    """Código de autorización inválido, expirado o ya consumido."""


class PkceMismatchError(AuthError):
    """`code_verifier` no satisface el `code_challenge` registrado."""


class AccountLockedError(AuthError):
    """Cuenta bloqueada temporalmente por demasiados intentos fallidos de autenticación."""

    def __init__(self, seconds_remaining: int) -> None:
        self.seconds_remaining = seconds_remaining
        super().__init__(f"Cuenta bloqueada. Intente de nuevo en {seconds_remaining} segundos.")
