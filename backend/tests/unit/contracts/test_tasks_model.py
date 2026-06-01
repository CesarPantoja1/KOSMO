from kosmo.contracts.sdd.ids import BoundaryName, RequirementId, TaskId
from kosmo.contracts.sdd.tasks import ImplementationNote, Task, TaskStatus


class TestTaskModel:
    def test_task_minimal(self) -> None:
        task = Task(
            id=TaskId("T-1"),
            title="Implement ProductService",
            description="Create the ProductService class",
            boundary=BoundaryName("product"),
        )
        assert task.id == TaskId("T-1")
        assert task.status == TaskStatus.PENDING
        assert task.depends_on == []
        assert task.parallelizable is False

    def test_task_with_dependencies(self) -> None:
        task = Task(
            id=TaskId("T-2"),
            title="Implement ProductController",
            description="REST controller",
            boundary=BoundaryName("product"),
            depends_on=[TaskId("T-1")],
            requirements=[RequirementId("R-1")],
            parallelizable=True,
        )
        assert len(task.depends_on) == 1
        assert task.parallelizable is True
        assert len(task.requirements) == 1

    def test_task_status_enum(self) -> None:
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.IN_PROGRESS == "in_progress"
        assert TaskStatus.DONE == "done"
        assert TaskStatus.BLOCKED == "blocked"

    def test_implementation_note(self) -> None:
        note = ImplementationNote(
            task_id=TaskId("T-1"),
            content="Use repository pattern",
            author_role="architect",
        )
        assert note.task_id == TaskId("T-1")
        assert note.author_role == "architect"
