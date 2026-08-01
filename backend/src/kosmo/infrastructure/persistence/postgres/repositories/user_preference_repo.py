from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.memory.user_preference import UserPreference
from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.infrastructure.persistence.postgres.models import UserPreferenceModel


class SqlAlchemyUserPreferenceRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_by_user(self, user_id: str) -> list[UserPreference]:
        async with self._session_factory() as session:
            stmt = (
                select(UserPreferenceModel)
                .where(UserPreferenceModel.user_id == user_id)
                .order_by(UserPreferenceModel.created_at)
            )
            result = await session.execute(stmt)
            return [
                UserPreference(id=m.id, user_id=m.user_id, rule_text=m.rule_text)
                for m in result.scalars().all()
            ]

    async def save(self, user_id: str, rule_text: str) -> UserPreference:
        model = UserPreferenceModel(
            id=IdGenerator.generate("user_pref"),
            user_id=user_id,
            rule_text=rule_text,
        )
        async with self._session_factory() as session:
            session.add(model)
            await session.commit()
            return UserPreference(id=model.id, user_id=user_id, rule_text=rule_text)
