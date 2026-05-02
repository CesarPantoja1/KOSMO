"""Algoritmos puros de PKCE (RFC 7636).

Pertenecen al dominio porque codifican una regla criptográfica sin
dependencias de infraestructura: dado un ``code_verifier``, calculan o
verifican el ``code_challenge`` correspondiente con ``S256``.
"""

import base64
import hashlib
import hmac


def s256_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def verify_s256(verifier: str, challenge: str) -> bool:
    return hmac.compare_digest(s256_challenge(verifier), challenge)
