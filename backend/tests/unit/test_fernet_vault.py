from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from kosmo.contracts.auth import EncryptedSecret, InvalidTokenError
from kosmo.infrastructure.security import FernetSecretCipher


@pytest.mark.unit
def test_encrypt_then_decrypt_roundtrip() -> None:
    cipher = FernetSecretCipher(Fernet.generate_key().decode("utf-8"))
    secret = cipher.encrypt(b"sk-anthropic-abcdef")
    assert cipher.decrypt(secret) == b"sk-anthropic-abcdef"


@pytest.mark.unit
def test_encrypt_string_then_decrypt_string_roundtrip() -> None:
    cipher = FernetSecretCipher(Fernet.generate_key().decode("utf-8"))
    secret = cipher.encrypt_string("sk-proj-super-secret-key-12345")
    assert isinstance(secret, EncryptedSecret)
    assert cipher.decrypt_string(secret) == "sk-proj-super-secret-key-12345"


@pytest.mark.unit
def test_decrypt_string_from_raw_bytes_and_str() -> None:
    cipher = FernetSecretCipher(Fernet.generate_key().decode("utf-8"))
    secret = cipher.encrypt_string("api_key_value")

    # Descifrar pasando EncryptedSecret
    assert cipher.decrypt_string(secret) == "api_key_value"

    # Descifrar pasando raw ciphertext bytes
    assert cipher.decrypt_string(secret.ciphertext) == "api_key_value"

    # Descifrar pasando ciphertext decodificado como string
    assert cipher.decrypt_string(secret.ciphertext.decode("utf-8")) == "api_key_value"


@pytest.mark.unit
def test_decrypt_with_wrong_key_raises() -> None:
    cipher_a = FernetSecretCipher(Fernet.generate_key().decode("utf-8"))
    cipher_b = FernetSecretCipher(Fernet.generate_key().decode("utf-8"))
    secret = cipher_a.encrypt(b"payload")
    with pytest.raises(InvalidTokenError, match="Cifrado inválido o expirado"):
        cipher_b.decrypt(secret)


@pytest.mark.unit
def test_decrypt_tampered_ciphertext_raises() -> None:
    cipher = FernetSecretCipher(Fernet.generate_key().decode("utf-8"))
    with pytest.raises(InvalidTokenError, match="Cifrado inválido o expirado"):
        cipher.decrypt(EncryptedSecret(ciphertext=b"not-a-fernet-token"))


@pytest.mark.unit
def test_master_key_as_secret_str() -> None:
    key_str = Fernet.generate_key().decode("utf-8")
    secret_key = SecretStr(key_str)
    cipher = FernetSecretCipher(secret_key)
    secret = cipher.encrypt_string("my-api-key")
    assert cipher.decrypt_string(secret) == "my-api-key"


@pytest.mark.unit
def test_master_key_as_bytes() -> None:
    key_bytes = Fernet.generate_key()
    cipher = FernetSecretCipher(key_bytes)
    secret = cipher.encrypt_string("bytes-key-test")
    assert cipher.decrypt_string(secret) == "bytes-key-test"


@pytest.mark.unit
def test_generate_master_key() -> None:
    generated = FernetSecretCipher.generate_master_key()
    assert isinstance(generated, str)
    assert len(generated) == 44  # Base64 encoding of 32 bytes

    # Comprobar que inicializa un cipher válido
    cipher = FernetSecretCipher(generated)
    secret = cipher.encrypt_string("test-generated-key")
    assert cipher.decrypt_string(secret) == "test-generated-key"


@pytest.mark.unit
def test_invalid_master_key_raises_value_error() -> None:
    # Clave vacía
    with pytest.raises(ValueError, match="La clave maestra Fernet no puede estar vacía"):
        FernetSecretCipher("")

    with pytest.raises(ValueError, match="La clave maestra Fernet no puede estar vacía"):
        FernetSecretCipher(b"")

    with pytest.raises(ValueError, match="La clave maestra Fernet no puede estar vacía"):
        FernetSecretCipher(SecretStr(""))

    # Clave corrupta o longitud no válida
    with pytest.raises(ValueError, match="La clave maestra Fernet es inválida"):
        FernetSecretCipher("invalid-key-format")

    with pytest.raises(ValueError, match="La clave maestra Fernet es inválida"):
        FernetSecretCipher(b"too-short")


@pytest.mark.unit
def test_to_and_from_storage_str() -> None:
    cipher = FernetSecretCipher(Fernet.generate_key().decode("utf-8"))
    secret = cipher.encrypt_string("store-me-in-database")

    storage_str = FernetSecretCipher.to_storage_str(secret)
    assert isinstance(storage_str, str)
    assert storage_str.startswith("gAAAAA")

    reconstructed = FernetSecretCipher.from_storage_str(storage_str)
    assert isinstance(reconstructed, EncryptedSecret)
    assert reconstructed.ciphertext == secret.ciphertext
    assert cipher.decrypt_string(reconstructed) == "store-me-in-database"
