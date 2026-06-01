from enum import StrEnum

from pydantic import BaseModel

from kosmo.contracts.sdd.ids import BoundaryName, RequirementId, TaskId


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class ImplementationNote(BaseModel):
    task_id: TaskId
    content: str
    author_role: str = ""


class Task(BaseModel):
    id: TaskId
    title: str
    description: str
    boundary: BoundaryName
    depends_on: list[TaskId] = []
    requirements: list[RequirementId] = []
    acceptance_criteria: list[str] = []
    status: TaskStatus = TaskStatus.PENDING
    parallelizable: bool = False
    implementation_notes: list[ImplementationNote] = []
