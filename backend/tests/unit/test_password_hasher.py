from kosmo.infrastructure.security import Argon2idParameters, Argon2idPasswordHasher


def _hasher() -> Argon2idPasswordHasher:
    return Argon2idPasswordHasher(
        Argon2idParameters(memory_kib=65536, time_cost=3, parallelism=4)
    )


def test_hash_then_verify_roundtrip() -> None:
    hasher = _hasher()
    digest = hasher.hash("supersecret-password-123")
    assert hasher.verify(digest, "supersecret-password-123") is True


def test_verify_rejects_wrong_password() -> None:
    hasher = _hasher()
    digest = hasher.hash("supersecret-password-123")
    assert hasher.verify(digest, "another-password-456") is False


def test_verify_rejects_garbage_hash() -> None:
    hasher = _hasher()
    assert hasher.verify("not-an-argon2-hash", "anything") is False


def test_argon2id_parameters_match_owasp_2025() -> None:
    hasher = _hasher()
    digest = hasher.hash("password")
    assert digest.startswith("$argon2id$")
    assert "m=65536" in digest
    assert "t=3" in digest
    assert "p=4" in digest
