from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from kosmo.contracts.sdd.ids import FeatureId, ImplementationId, ProjectId, WorkspaceId


class WorkspaceStatus(StrEnum):
    NOT_CREATED = "not_created"
    READY = "ready"
    IN_USE = "in_use"
    VALIDATING = "validating"


class FeatureImplementationStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    REQUIRES_REVIEW = "requires_review"
    FAILED = "failed"


class FileAction(StrEnum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


class ValidationStep(StrEnum):
    TYPECHECK = "typecheck"
    LINT = "lint"
    TESTS = "tests"
    BUILD = "build"


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class FileOperation:
    path: str
    action: FileAction
    description: str = ""
    rationale: str = ""
    target_symbols: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ImplementationPlan:
    feature_id: FeatureId
    operations: tuple[FileOperation, ...] = field(default_factory=tuple)
    summary: str = ""
    estimated_effort: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class ValidationErrorDetail:
    file: str
    line: int = 0
    column: int = 0
    message: str = ""
    severity: ValidationSeverity = ValidationSeverity.ERROR
    code: str | None = None


@dataclass(frozen=True)
class ValidationStepResult:
    step: ValidationStep
    success: bool
    duration_ms: int = 0
    exit_code: int = 0
    raw_output: str = ""
    errors: tuple[ValidationErrorDetail, ...] = field(default_factory=tuple)
    error_messages: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ValidationRunResult:
    steps: tuple[ValidationStepResult, ...] = field(default_factory=tuple)
    all_passed: bool = False
    total_duration_ms: int = 0
    executed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    error_summary: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CodeWorkspace:
    id: WorkspaceId
    project_id: ProjectId
    status: WorkspaceStatus = WorkspaceStatus.NOT_CREATED
    workspace_dir: str | None = None
    manifest_files: tuple[str, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class FeatureImplementation:
    id: ImplementationId
    feature_id: FeatureId
    project_id: ProjectId
    status: FeatureImplementationStatus = FeatureImplementationStatus.PENDING
    session_id: str | None = None
    plan: ImplementationPlan | None = None
    last_validation: ValidationRunResult | None = None
    attempt_count: int = 0
    max_attempts: int = 3
    generated_files: tuple[str, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
