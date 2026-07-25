import pytest

from kosmo.domain.auth import s256_challenge, verify_s256


@pytest.mark.unit
def test_s256_challenge_matches_rfc7636_example() -> None:
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    expected = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    assert s256_challenge(verifier) == expected


@pytest.mark.unit
def test_verify_s256_accepts_matching_pair() -> None:
    verifier = "a" * 64
    challenge = s256_challenge(verifier)
    assert verify_s256(verifier, challenge) is True


@pytest.mark.unit
def test_verify_s256_rejects_mismatched_pair() -> None:
    challenge = s256_challenge("a" * 64)
    assert verify_s256("b" * 64, challenge) is False
