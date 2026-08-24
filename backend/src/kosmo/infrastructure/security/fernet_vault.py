from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from pydantic import SecretStr

from kosmo.contracts.auth import EncryptedSecret, InvalidTokenError


class FernetSecretCipher:
    """Adaptador de seguridad para cifrado y descifrado simétrico de credenciales con Fernet."""

    def __init__(self, master_key: str | bytes | SecretStr) -> None:
        if isinstance(master_key, SecretStr):
            raw_key = master_key.get_secret_value().encode("utf-8")
        elif isinstance(master_key, str):
            raw_key = master_key.strip().encode("utf-8")
        else:
            raw_key = master_key.strip()

        if not raw_key:
            msg = "La clave maestra Fernet no puede estar vacía."
            raise ValueError(msg)

        try:
            self._fernet = Fernet(raw_key)
        except Exception as exc:
            msg = "La clave maestra Fernet es inválida. Debe ser de 32 bytes codificados en base64 url-safe."
            raise ValueError(msg) from exc

    @classmethod
    def generate_master_key(cls) -> str:
        """Genera una clave maestra válida para inicializar FernetSecretCipher."""
        return Fernet.generate_key().decode("utf-8")

    def encrypt(self, plaintext: bytes) -> EncryptedSecret:
        """Cifra un arreglo de bytes en un EncryptedSecret autenticado."""
        return EncryptedSecret(ciphertext=self._fernet.encrypt(plaintext))

    def decrypt(self, secret: EncryptedSecret) -> bytes:
        """Descifra un EncryptedSecret retornando los bytes originales."""
        try:
            return self._fernet.decrypt(secret.ciphertext)
        except InvalidToken as exc:
            raise InvalidTokenError("Cifrado inválido o expirado") from exc

    def encrypt_string(self, plaintext: str) -> EncryptedSecret:
        """Cifra una cadena de texto (e.g. API key en claro) en un EncryptedSecret."""
        return self.encrypt(plaintext.encode("utf-8"))

    def decrypt_string(self, secret: EncryptedSecret | bytes | str) -> str:
        """Descifra una credencial protegida y devuelve la cadena en texto plano."""
        if isinstance(secret, EncryptedSecret):
            enc = secret
        elif isinstance(secret, str):
            enc = EncryptedSecret(ciphertext=secret.encode("utf-8"))
        else:
            enc = EncryptedSecret(ciphertext=secret)

        decrypted_bytes = self.decrypt(enc)
        return decrypted_bytes.decode("utf-8")

    @staticmethod
    def to_storage_str(secret: EncryptedSecret) -> str:
        """Serializa el ciphertext de EncryptedSecret a string para almacenamiento en base de datos."""
        return secret.ciphertext.decode("utf-8")

    @staticmethod
    def from_storage_str(stored: str) -> EncryptedSecret:
        """Reconstruye un EncryptedSecret a partir de una cadena almacenada en base de datos."""
        return EncryptedSecret(ciphertext=stored.strip().encode("utf-8"))
