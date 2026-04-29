import pytest
from cryptography.fernet import Fernet

from kosmo.contracts.auth import EncryptedSecret, InvalidTokenError
from kosmo.infrastructure.security import FernetSecretCipher


def test_encrypt_then_decrypt_roundtrip() -> None:
    cipher = FernetSecretCipher(Fernet.generate_key().decode("utf-8"))
    secret = cipher.encrypt(b"sk-anthropic-abcdef")
    assert cipher.decrypt(secret) == b"sk-anthropic-abcdef"


def test_decrypt_with_wrong_key_raises() -> None:
    cipher_a = FernetSecretCipher(Fernet.generate_key().decode("utf-8"))
    cipher_b = FernetSecretCipher(Fernet.generate_key().decode("utf-8"))
    secret = cipher_a.encrypt(b"payload")
    with pytest.raises(InvalidTokenError):
        cipher_b.decrypt(secret)


def test_decrypt_tampered_ciphertext_raises() -> None:
    cipher = FernetSecretCipher(Fernet.generate_key().decode("utf-8"))
    with pytest.raises(InvalidTokenError):
        cipher.decrypt(EncryptedSecret(ciphertext=b"not-a-fernet-token"))
