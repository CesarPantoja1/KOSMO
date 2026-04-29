from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EncryptedSecret:
    ciphertext: bytes


class SecretCipher(Protocol):
    def encrypt(self, plaintext: bytes) -> EncryptedSecret: ...

    def decrypt(self, secret: EncryptedSecret) -> bytes: ...
