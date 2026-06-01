from cryptography.fernet import Fernet

from kosmo.contracts.sdd.ids import UserId


class FernetApiKeyVault:
    def __init__(self, fernet: Fernet) -> None:
        self._fernet = fernet
        self._store: dict[str, tuple[str, UserId, str]] = {}

    async def encrypt(self, plaintext: str, key_id: str, user_id: UserId) -> str:
        cipher_text = self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")
        self._store[key_id] = (user_id, cipher_text, plaintext)
        return cipher_text

    async def decrypt(self, key_id: str) -> str:
        entry = self._store.get(key_id)
        if entry is None:
            raise Exception(f"Clave no encontrada: {key_id}")
        return entry[2]

    async def delete(self, key_id: str) -> None:
        self._store.pop(key_id, None)
