from dataclasses import dataclass

from argon2 import PasswordHasher as _Argon2Hasher
from argon2 import Type
from argon2.exceptions import InvalidHashError, VerifyMismatchError


@dataclass(frozen=True, slots=True)
class Argon2idParameters:
    memory_kib: int
    time_cost: int
    parallelism: int


class Argon2idPasswordHasher:
    def __init__(self, params: Argon2idParameters) -> None:
        self._hasher = _Argon2Hasher(
            time_cost=params.time_cost,
            memory_cost=params.memory_kib,
            parallelism=params.parallelism,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )

    def hash(self, plain: str) -> str:
        return self._hasher.hash(plain)

    def verify(self, hashed: str, plain: str) -> bool:
        try:
            return self._hasher.verify(hashed, plain)
        except (VerifyMismatchError, InvalidHashError):
            return False

    def needs_rehash(self, hashed: str) -> bool:
        return self._hasher.check_needs_rehash(hashed)
