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
