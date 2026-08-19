from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts.codegen import (
    FeatureImplementation,
    FeatureImplementationRepository,
    FeatureImplementationStatus,
    FileAction,
    FileOperation,
    ImplementationPlan,
    ValidationErrorDetail,
    ValidationRunResult,
    ValidationSeverity,
    ValidationStep,
    ValidationStepResult,
)
from kosmo.contracts.sdd.ids import FeatureId, ImplementationId, ProjectId
from kosmo.infrastructure.persistence.postgres.models import FeatureImplementationModel


def _plan_to_dict(plan: ImplementationPlan | None) -> dict[str, Any] | None:
    if plan is None:
        return None
    return {
        "feature_id": str(plan.feature_id),
        "operations": [
            {
                "path": op.path,
                "action": str(op.action),
                "description": op.description,
                "rationale": op.rationale,
                "target_symbols": list(op.target_symbols),
            }
            for op in plan.operations
        ],
        "summary": plan.summary,
        "estimated_effort": plan.estimated_effort,
        "created_at": plan.created_at.isoformat(),
    }


def _plan_from_dict(data: dict[str, Any] | None) -> ImplementationPlan | None:
    if data is None:
        return None
    return ImplementationPlan(
        feature_id=FeatureId(data["feature_id"]),
        operations=tuple(
            FileOperation(
                path=op["path"],
                action=FileAction(op["action"]),
                description=op.get("description", ""),
                rationale=op.get("rationale", ""),
                target_symbols=tuple(op.get("target_symbols", [])),
            )
            for op in data.get("operations", [])
        ),
        summary=data.get("summary", ""),
        estimated_effort=data.get("estimated_effort", ""),
        created_at=datetime.fromisoformat(data["created_at"]),
    )


def _validation_to_dict(validation: ValidationRunResult | None) -> dict[str, Any] | None:
    if validation is None:
        return None
    return {
        "steps": [
            {
                "step": str(step.step),
                "success": step.success,
                "duration_ms": step.duration_ms,
                "exit_code": step.exit_code,
                "raw_output": step.raw_output,
                "errors": [
                    {
                        "file": error.file,
                        "line": error.line,
                        "column": error.column,
                        "message": error.message,
                        "severity": str(error.severity),
                        "code": error.code,
                    }
                    for error in step.errors
                ],
                "error_messages": list(step.error_messages),
            }
            for step in validation.steps
        ],
        "all_passed": validation.all_passed,
        "total_duration_ms": validation.total_duration_ms,
        "executed_at": validation.executed_at.isoformat(),
        "error_summary": list(validation.error_summary),
    }


def _validation_from_dict(data: dict[str, Any] | None) -> ValidationRunResult | None:
    if data is None:
        return None
    return ValidationRunResult(
        steps=tuple(
            ValidationStepResult(
                step=ValidationStep(step["step"]),
                success=step["success"],
                duration_ms=step["duration_ms"],
                exit_code=step["exit_code"],
                raw_output=step["raw_output"],
                errors=tuple(
                    ValidationErrorDetail(
                        file=error["file"],
                        line=error["line"],
                        column=error["column"],
                        message=error["message"],
                        severity=ValidationSeverity(error["severity"]),
                        code=error["code"],
                    )
                    for error in step.get("errors", [])
                ),
                error_messages=tuple(step.get("error_messages", [])),
            )
            for step in data.get("steps", [])
        ),
        all_passed=data["all_passed"],
        total_duration_ms=data["total_duration_ms"],
        executed_at=datetime.fromisoformat(data["executed_at"]),
        error_summary=tuple(data.get("error_summary", [])),
    )


class SqlAlchemyFeatureImplementationRepository(FeatureImplementationRepository):
    """Adaptador de persistencia PostgreSQL para FeatureImplementation."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        if session_factory is None and session is None:
            raise ValueError("Se requiere session_factory o session")
        self._session_factory = session_factory
        self._session = session

    @asynccontextmanager
    async def _session_ctx(self) -> AsyncGenerator[AsyncSession]:
        if self._session is not None:
            yield self._session
            return
        assert self._session_factory is not None
        async with self._session_factory() as session:
            yield session

    async def _commit(self, session: AsyncSession) -> None:
        if self._session is None:
            await session.commit()

    @staticmethod
    def _to_entity(model: FeatureImplementationModel) -> FeatureImplementation:
        return FeatureImplementation(
            id=ImplementationId(model.id),
            feature_id=FeatureId(model.feature_id),
            project_id=ProjectId(model.project_id),
            status=FeatureImplementationStatus(model.status),
            session_id=model.session_id,
            plan=_plan_from_dict(model.plan),
            last_validation=_validation_from_dict(model.last_validation),
            attempt_count=model.attempt_count,
            max_attempts=model.max_attempts,
            generated_files=tuple(model.generated_files),
            retry_history=tuple(tuple(errors) for errors in model.retry_history),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def by_feature_id(self, feature_id: FeatureId | str) -> FeatureImplementation | None:
        async with self._session_ctx() as session:
            stmt = select(FeatureImplementationModel).where(FeatureImplementationModel.feature_id == str(feature_id))
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._to_entity(model)

    async def by_id(self, implementation_id: ImplementationId | str) -> FeatureImplementation | None:
        async with self._session_ctx() as session:
            stmt = select(FeatureImplementationModel).where(FeatureImplementationModel.id == str(implementation_id))
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._to_entity(model)

    async def list_by_project(self, project_id: ProjectId | str) -> list[FeatureImplementation]:
        async with self._session_ctx() as session:
            stmt = select(FeatureImplementationModel).where(FeatureImplementationModel.project_id == str(project_id))
            result = await session.execute(stmt)
            models = result.scalars().all()
            return [self._to_entity(model) for model in models]

    async def save(self, implementation: FeatureImplementation) -> FeatureImplementation:
        async with self._session_ctx() as session:
            stmt = select(FeatureImplementationModel).where(FeatureImplementationModel.id == str(implementation.id))
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            now = datetime.now(UTC)
            if model is None:
                model = FeatureImplementationModel(
                    id=str(implementation.id),
                    feature_id=str(implementation.feature_id),
                    project_id=str(implementation.project_id),
                    status=str(implementation.status),
                    session_id=implementation.session_id,
                    plan=_plan_to_dict(implementation.plan),
                    last_validation=_validation_to_dict(implementation.last_validation),
                    attempt_count=implementation.attempt_count,
                    max_attempts=implementation.max_attempts,
                    generated_files=list(implementation.generated_files),
                    retry_history=[list(errors) for errors in implementation.retry_history],
                    created_at=implementation.created_at,
                    updated_at=implementation.updated_at or now,
                )
                session.add(model)
            else:
                model.status = str(implementation.status)
                model.session_id = implementation.session_id
                model.plan = _plan_to_dict(implementation.plan)
                model.last_validation = _validation_to_dict(implementation.last_validation)
                model.attempt_count = implementation.attempt_count
                model.max_attempts = implementation.max_attempts
                model.generated_files = list(implementation.generated_files)
                model.retry_history = [list(errors) for errors in implementation.retry_history]
                model.updated_at = now

            await self._commit(session)
            return implementation

    async def delete(self, feature_id: FeatureId | str) -> None:
        async with self._session_ctx() as session:
            stmt = delete(FeatureImplementationModel).where(FeatureImplementationModel.feature_id == str(feature_id))
            await session.execute(stmt)
            await self._commit(session)
