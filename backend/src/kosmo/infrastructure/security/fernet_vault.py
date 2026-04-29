from cryptography.fernet import Fernet, InvalidToken

from kosmo.contracts.auth import EncryptedSecret, InvalidTokenError


class FernetSecretCipher:
    def __init__(self, master_key: str) -> None:
        self._fernet = Fernet(master_key.encode("utf-8"))

    def encrypt(self, plaintext: bytes) -> EncryptedSecret:
        return EncryptedSecret(ciphertext=self._fernet.encrypt(plaintext))

    def decrypt(self, secret: EncryptedSecret) -> bytes:
        try:
            return self._fernet.decrypt(secret.ciphertext)
        except InvalidToken as exc:
            raise InvalidTokenError("Cifrado inválido o expirado") from exc
