from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from kosmo.contracts.auth import User, UserAlreadyExistsError
from kosmo.infrastructure.persistence.postgres.models import UserModel


def _to_entity(row: UserModel) -> User:
    return User(
        id=str(row.id),
        email=row.email,
        hashed_password=row.hashed_password,
        created_at=row.created_at,
        disabled_at=row.disabled_at,
    )


class SqlAlchemyUserRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def by_email(self, email: str) -> User | None:
        async with self._session_factory() as session:
            result = await session.execute(select(UserModel).where(UserModel.email == email))
            row = result.scalar_one_or_none()
            return _to_entity(row) if row is not None else None

    async def by_id(self, user_id: str) -> User | None:
        try:
            uid = UUID(user_id)
        except ValueError:
            return None
        async with self._session_factory() as session:
            result = await session.execute(select(UserModel).where(UserModel.id == uid))
            row = result.scalar_one_or_none()
            return _to_entity(row) if row is not None else None

    async def create(self, user: User) -> None:
        stmt = pg_insert(UserModel).values(
            id=UUID(user.id),
            email=user.email,
            hashed_password=user.hashed_password,
            created_at=user.created_at,
            disabled_at=user.disabled_at,
        )
        async with self._session_factory() as session:
            try:
                await session.execute(stmt)
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise UserAlreadyExistsError("Email ya registrado") from exc

    async def update_password(self, *, user_id: str, hashed_password: str) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.id == UUID(user_id)).with_for_update()
            )
            row = result.scalar_one_or_none()
            if row is None:
                return
            row.hashed_password = hashed_password
            await session.commit()
