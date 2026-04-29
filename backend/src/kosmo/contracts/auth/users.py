from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class User:
    id: str
    email: str
    hashed_password: str
    created_at: datetime
    disabled_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.disabled_at is None
