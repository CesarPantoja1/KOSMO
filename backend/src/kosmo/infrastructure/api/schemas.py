"""DTOs Pydantic expuestos por la API HTTP.

Pertenecen al adaptador de entrada (FastAPI), por lo que viven en infraestructura
y pueden referenciar entidades de dominio para conversión I/O sin invertir capas.
"""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from kosmo.contracts.auth import TokenPair

# Enumeraciones de negocio


class CodeChallengeMethod(StrEnum):
    """Método de transformación PKCE permitido por el servidor.

    Actualmente solo se acepta S256 (SHA-256), que es el estándar
    recomendado por RFC 7636 y el único permitido en KOSMO.
    """

    S256 = "S256"


class GrantType(StrEnum):
    """Tipo de concesión OAuth 2.0 soportado en el endpoint /token."""

    authorization_code = "authorization_code"


class RefreshGrantType(StrEnum):
    """Tipo de concesión para renovar un par de tokens mediante refresh token."""

    refresh_token = "refresh_token"


class TokenType(StrEnum):
    """Esquema de autenticación que debe adjuntarse en el header Authorization."""

    Bearer = "Bearer"


# Scopes de acceso disponibles en KOSMO

KNOWN_SCOPES: list[str] = [
    "profile:read",
    "profile:write",
    "agent:run",
    "agent:read",
    "admin",
]
"""Scopes reconocidos por el sistema.

El servidor no rechaza scopes desconocidos para permitir extensibilidad, pero
el Frontend debe presentar únicamente los de esta lista al usuario (se puede
extender, no está definido ni cerrado al cambio).
"""

# Requests


class RegisterRequest(BaseModel):
    """Payload para crear una nueva cuenta de usuario en KOSMO."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(
        description=(
            "Dirección de correo electrónico del nuevo usuario. "
            "Debe ser única en el sistema; intentar registrar un email ya existente "
            "devuelve 409 Conflict."
        ),
        examples=["usuario@ejemplo.com"],
    )
    password: str = Field(
        min_length=12,
        max_length=128,
        description=(
            "Contraseña en texto plano. El servidor la procesa con Argon2id "
            "(OWASP 2025) antes de persistirla; jamás se almacena en claro. "
            "Mínimo 12 caracteres, máximo 128."
        ),
        examples=["M1ContraseñaSegura!"],
    )


class AuthorizeRequest(BaseModel):
    """Payload para iniciar el flujo PKCE y obtener un código de autorización.

    El cliente genera un ``code_verifier`` aleatorio (43-128 chars, Base64URL),
    calcula ``code_challenge = BASE64URL(SHA256(code_verifier))`` y envía
    el challenge aquí. El verifier se usa después en ``/token``.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(
        description="Email del usuario que intenta autenticarse.",
        examples=["usuario@ejemplo.com"],
    )
    password: str = Field(
        min_length=1,
        max_length=128,
        description="Contraseña en texto plano del usuario.",
        examples=["M1ContraseñaSegura!"],
    )
    code_challenge: str = Field(
        min_length=43,
        max_length=128,
        description=(
            "Hash SHA-256 del ``code_verifier``, codificado en Base64URL sin padding. "
            "Se almacena en caché por 5 minutos y se valida en el intercambio de tokens."
        ),
        examples=["E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"],
    )
    code_challenge_method: CodeChallengeMethod = Field(
        default=CodeChallengeMethod.S256,
        description="Método de transformación del code_challenge. Solo se acepta 'S256'.",
        examples=["S256"],
    )
    scopes: list[str] = Field(
        default_factory=list,
        description=(
            "Lista de permisos solicitados para la sesión. "
            f"Valores reconocidos: {', '.join(KNOWN_SCOPES)}. "
            "Se pueden solicitar múltiples scopes en la misma llamada."
        ),
        examples=[["profile:read", "agent:run"]],
    )


class TokenExchangeRequest(BaseModel):
    """Payload para intercambiar el código de autorización por un par de tokens JWT."""

    model_config = ConfigDict(extra="forbid")

    grant_type: GrantType = Field(
        description="Debe ser exactamente 'authorization_code'.",
        examples=["authorization_code"],
    )
    code: str = Field(
        min_length=1,
        max_length=256,
        description=(
            "Código de autorización opaco devuelto por ``/authorize``. "
            "Es de un solo uso y expira en 5 minutos."
        ),
        examples=["a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"],
    )
    code_verifier: str = Field(
        min_length=43,
        max_length=128,
        description=(
            "Secreto original generado por el cliente antes de calcular el challenge. "
            "El servidor recalcula SHA-256 y compara con el challenge almacenado."
        ),
        examples=["dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"],
    )


class TokenRefreshRequest(BaseModel):
    """Payload para renovar un par de tokens usando el refresh token activo."""

    model_config = ConfigDict(extra="forbid")

    grant_type: RefreshGrantType = Field(
        description="Debe ser exactamente 'refresh_token'.",
        examples=["refresh_token"],
    )
    refresh_token: str = Field(
        min_length=1,
        description=(
            "JWT de tipo refresh emitido previamente por ``/token`` o ``/refresh``. "
            "Cada refresh token es de un solo uso; el servidor emite un par nuevo "
            "y revoca el token consumido. Si se detecta reutilización, toda la "
            "familia de tokens queda revocada (Token Rotation)."
        ),
        examples=[
            "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJ1c3ItMDFIWFlaQVpCQ0RFRkdISUpLTE1OT1AiLCJqdGkiOiJydGktMDFIWFlaQVpCQ0RFRkdISUpLTE1OT1EiLCJ0eXAiOiJyZWZyZXNoIn0."
            "SIGNATURE"
        ],
    )


class LogoutRequest(BaseModel):
    """Payload para cerrar la sesión activa del usuario autenticado.

    El header ``Authorization: Bearer <access_token>`` es obligatorio.
    El ``refresh_token`` es opcional pero recomendado para revocar ambos tokens
    simultáneamente y garantizar cierre de sesión completo.
    """

    model_config = ConfigDict(extra="forbid")

    refresh_token: str | None = Field(
        default=None,
        description=(
            "JWT de tipo refresh a revocar junto con el access token. "
            "Si se omite, solo se revoca el access token del header."
        ),
        examples=[
            "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJ1c3ItMDFIWFlaQVpCQ0RFRkdISUpLTE1OT1AiLCJqdGkiOiJydGktMDFIWFlaQVpCQ0RFRkdISUpLTE1OT1EiLCJ0eXAiOiJyZWZyZXNoIn0."
            "SIGNATURE"
        ],
    )


# Responses


class AuthorizationCodeResponse(BaseModel):
    """Resultado exitoso de ``POST /authorize``.

    El ``authorization_code`` debe intercambiarse por tokens en ``/token``
    antes de que expire ``expires_in`` segundos.
    """

    authorization_code: str = Field(
        description=(
            "Código de autorización opaco de un solo uso. "
            "Válido únicamente para el ``code_verifier`` generado en la misma sesión."
        ),
        examples=["a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"],
    )
    expires_in: int = Field(
        ge=1,
        le=600,
        description="Segundos que quedan hasta que el código expire. Máximo 600 (10 min).",
        examples=[300],
    )


class TokenView(BaseModel):
    """Representación serializable de un token JWT emitido."""

    token: str = Field(
        description=(
            "Token JWT firmado con RS256. Incluye claims estándar (sub, iat, exp, jti) "
            "más claims propietarios de KOSMO (typ, scopes, family_id para refresh)."
        ),
        examples=[
            "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJ1c3ItMDFIWFlaQVpCQ0RFRkdISUpLTE1OT1AiLCJqdGkiOiJhdGktMDFIWFlaQVpCQ0RFRkdISUpLTE1OT1EiLCJ0eXAiOiJhY2Nlc3MiLCJzY29wZXMiOlsicHJvZmlsZTpyZWFkIl0sImlhdCI6MTc0NjE0MDAwMCwiZXhwIjoxNzQ2MTQwOTAwfQ."
            "SIGNATURE"
        ],
    )
    jti: str = Field(
        description=(
            "JWT ID — identificador único del token (UUID v4). "
            "Se usa como clave en Redis para la lista de revocación; "
            "permite invalidar un token individual sin rotar las claves RSA."
        ),
        examples=["ati-01HXYAZABCDEFGHIJKLMNOP"],
    )
    expires_at: datetime = Field(
        description=(
            "Timestamp ISO-8601 (UTC) en que el token expira. "
            "El access token tiene TTL de 15 min; el refresh token, 7 días."
        ),
        examples=["2025-12-31T23:59:59Z"],
    )


class TokenPairResponse(BaseModel):
    """Par de tokens emitido tras autenticación exitosa o renovación.

    El ``access`` token se adjunta en el header ``Authorization: Bearer``
    en cada petición autenticada. El ``refresh`` token se usa exclusivamente
    en ``POST /refresh`` para renovar la sesión.
    """

    access: TokenView = Field(
        description="Token de acceso de corta vida (TTL: 15 minutos). Uso: Authorization header."
    )
    refresh: TokenView = Field(
        description=(
            "Token de renovación de larga vida (TTL: 7 días). "
            "Almacenar en almacenamiento seguro (HttpOnly cookie o Secure storage)."
        )
    )
    token_type: Literal["Bearer"] = Field(
        default="Bearer",
        description="Esquema de autenticación. Siempre 'Bearer' según RFC 6750.",
        examples=["Bearer"],
    )

    @classmethod
    def from_pair(cls, pair: TokenPair) -> "TokenPairResponse":
        return cls(
            access=TokenView(
                token=pair.access.token,
                jti=pair.access.jti,
                expires_at=pair.access.expires_at,
            ),
            refresh=TokenView(
                token=pair.refresh.token,
                jti=pair.refresh.jti,
                expires_at=pair.refresh.expires_at,
            ),
        )


class PrincipalView(BaseModel):
    """Identidad del usuario autenticado extraída del access token verificado."""

    subject: str = Field(
        description=(
            "Identificador opaco del usuario propietario del token. "
            "Corresponde al claim ``sub`` del JWT y al ``id`` en ``UserPublic``. "
            "Formato: prefijo de recurso + ULID (ej: ``usr-01HXYAZABCDEFGHIJKLMNOP``)."
        ),
        examples=["usr-01HXYAZABCDEFGHIJKLMNOP"],
    )
    scopes: list[str] = Field(
        description=(
            "Permisos concedidos en esta sesión, ordenados alfabéticamente. "
            f"Valores posibles: {', '.join(KNOWN_SCOPES)}."
        ),
        examples=[["agent:run", "profile:read"]],
    )


class UserPublic(BaseModel):
    """Datos públicos del usuario recién registrado. No incluye información sensible."""

    id: str = Field(
        description=(
            "Identificador único del usuario en el sistema. "
            "Formato: 'usr-' + ULID de 26 chars. Inmutable tras la creación."
        ),
        examples=["usr-01HXYAZABCDEFGHIJKLMNOP"],
    )
    email: EmailStr = Field(
        description="Dirección de correo verificada y normalizada del usuario.",
        examples=["usuario@ejemplo.com"],
    )
    created_at: datetime = Field(
        description="Timestamp ISO-8601 (UTC) de creación de la cuenta.",
        examples=["2025-01-15T10:30:00Z"],
    )


class OAuthErrorResponse(BaseModel):
    """Respuesta de error compatible con RFC 6749 §5.2.

    Todos los endpoints de autenticación devuelven este esquema cuando
    falla la operación, permitiendo al cliente manejar errores de forma
    estructurada y consistente.
    """

    error: str = Field(
        description=(
            "Código de error máquina-legible según OAuth 2.0 RFC 6749. "
            "Valores comunes: ``invalid_grant``, ``invalid_token``, "
            "``account_locked``, ``email_already_registered``."
        ),
        examples=["invalid_grant"],
    )
    error_description: str = Field(
        description="Descripción legible por humanos del error, útil para logging y debugging.",
        examples=["Credenciales inválidas"],
    )


class HttpErrorResponse(BaseModel):
    """Respuesta de error HTTP genérica para errores de infraestructura (4xx/5xx).

    Se emite cuando el error no está dentro del flujo OAuth (ej: error interno
    del servidor, acceso prohibido a un recurso).
    """

    detail: str = Field(
        description="Mensaje descriptivo del error de infraestructura.",
        examples=["Error interno del servidor. Por favor contacte al soporte."],
    )
