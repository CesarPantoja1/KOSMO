from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from kosmo.contracts.memory.user_preference import UserPreference
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.infrastructure.persistence.postgres.models import (
    UserPreferenceModel,
)


class SqlAlchemyUserPreferenceRepository:
    def __init__(self, session_factory: object) -> None:  # type: ignore[override]
        self._session_factory = session_factory  # type: ignore[assignment]

    async def add(self, preference: UserPreference) -> None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            model = UserPreferenceModel(  # type: ignore[call-arg]
                id=preference.id,
                user_id=preference.user_id,
                project_id=preference.project_id,
                document_type=preference.document_type,
                rule_text=preference.rule_text,
                corpus=preference.corpus,
                context_snippet=preference.context_snippet,
                confidence=preference.confidence,
                usage_count=preference.usage_count,
                created_at=preference.created_at,
            )
            session.add(model)
            await session.commit()

    async def get_by_user(
        self,
        user_id: str,
        project_id: ProjectId | None = None,
        document_type: str | None = None,
        limit: int = 20,
    ) -> list[UserPreference]:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            query = (
                select(UserPreferenceModel).where(UserPreferenceModel.user_id == user_id)  # type: ignore[arg-type,union-attr]
            )
            if project_id is not None:
                from sqlalchemy import or_

                query = query.where(
                    or_(
                        UserPreferenceModel.project_id == project_id,  # type: ignore[arg-type,union-attr]
                        UserPreferenceModel.project_id.is_(None),
                    )
                )
            if document_type is not None:
                query = query.where(
                    UserPreferenceModel.document_type == document_type  # type: ignore[arg-type,union-attr]
                )
            query = query.order_by(
                UserPreferenceModel.usage_count.desc(),  # type: ignore[arg-type,union-attr]
                UserPreferenceModel.created_at.desc(),  # type: ignore[arg-type,union-attr]
            ).limit(limit)

            result = await session.execute(query)
            models = result.scalars().all()
            return [self._to_preference(m) for m in models]

    async def increment_usage(self, preference_ids: list[str]) -> None:
        if not preference_ids:
            return
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            await session.execute(
                update(UserPreferenceModel)  # type: ignore[arg-type,union-attr]
                .where(UserPreferenceModel.id.in_(preference_ids))  # type: ignore[arg-type,union-attr]
                .values(usage_count=UserPreferenceModel.usage_count + 1)  # type: ignore[arg-type,union-attr]
            )
            await session.commit()

    async def delete(self, preference_id: str) -> None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            result = await session.execute(
                select(UserPreferenceModel).where(
                    UserPreferenceModel.id == preference_id  # type: ignore[arg-type,union-attr]
                )
            )
            model = result.scalar_one_or_none()
            if model is not None:
                await session.delete(model)
                await session.commit()

    async def update_confidence(self, preference_id: str, delta: float) -> None:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            await session.execute(
                update(UserPreferenceModel)  # type: ignore[arg-type,union-attr]
                .where(UserPreferenceModel.id == preference_id)  # type: ignore[arg-type,union-attr]
                .values(confidence=UserPreferenceModel.confidence + delta)  # type: ignore[arg-type,union-attr]
            )
            await session.commit()

    async def delete_expired(self, threshold_confidence: float = 0.1) -> int:
        session: AsyncSession = self._session_factory()  # type: ignore[call-arg,misc]
        async with session:
            result = await session.execute(
                select(UserPreferenceModel).where(
                    UserPreferenceModel.confidence < threshold_confidence  # type: ignore[arg-type,union-attr]
                )
            )
            models = result.scalars().all()
            count = len(models)
            for model in models:
                await session.delete(model)
            await session.commit()
            return count

    @staticmethod
    def _to_preference(model: object) -> UserPreference:  # type: ignore[no-untyped-def]
        return UserPreference(
            id=model.id,  # type: ignore[arg-type,union-attr]
            user_id=model.user_id,  # type: ignore[arg-type,union-attr]
            project_id=model.project_id,  # type: ignore[arg-type,union-attr]
            document_type=model.document_type,  # type: ignore[arg-type,union-attr]
            rule_text=model.rule_text,  # type: ignore[arg-type,union-attr]
            corpus=model.corpus,  # type: ignore[arg-type,union-attr]
            context_snippet=model.context_snippet,  # type: ignore[arg-type,union-attr]
            confidence=model.confidence,  # type: ignore[arg-type,union-attr]
            usage_count=model.usage_count,  # type: ignore[arg-type,union-attr]
            created_at=model.created_at,  # type: ignore[arg-type,union-attr]
        )
