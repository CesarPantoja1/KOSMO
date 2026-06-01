from kosmo.contracts.sdd.ids import BoundaryName, TaskId
from kosmo.contracts.sdd.tasks import Task
from kosmo.domain.sdd.validators.task_dag_validator import validate_task_dag


class TestTaskDagValidator:
    def test_empty_tasks_passes(self) -> None:
        findings = validate_task_dag([])
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) == 0

    def test_linear_dag_passes(self) -> None:
        tasks = [
            Task(
                id=TaskId("T-1"),
                title="First",
                description="First task",
                boundary=BoundaryName("b1"),
            ),
            Task(
                id=TaskId("T-2"),
                title="Second",
                description="Second task",
                boundary=BoundaryName("b1"),
                depends_on=[TaskId("T-1")],
            ),
        ]
        findings = validate_task_dag(tasks)
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) == 0

    def test_cycle_detected(self) -> None:
        tasks = [
            Task(
                id=TaskId("T-1"),
                title="A",
                description="A",
                boundary=BoundaryName("b1"),
                depends_on=[TaskId("T-2")],
            ),
            Task(
                id=TaskId("T-2"),
                title="B",
                description="B",
                boundary=BoundaryName("b1"),
                depends_on=[TaskId("T-1")],
            ),
        ]
        findings = validate_task_dag(tasks)
        errors = [f for f in findings if f.severity == "error"]
        assert any("ciclo" in e.message.lower() for e in errors)

    def test_missing_dependency_detected(self) -> None:
        tasks = [
            Task(
                id=TaskId("T-1"),
                title="A",
                description="A",
                boundary=BoundaryName("b1"),
                depends_on=[TaskId("T-99")],
            ),
        ]
        findings = validate_task_dag(tasks)
        errors = [f for f in findings if f.severity == "error"]
        assert any("inexistente" in e.message.lower() for e in errors)

    def test_duplicate_task_ids_detected(self) -> None:
        tasks = [
            Task(
                id=TaskId("T-1"),
                title="A",
                description="A",
                boundary=BoundaryName("b1"),
            ),
            Task(
                id=TaskId("T-1"),
                title="A copy",
                description="A copy",
                boundary=BoundaryName("b1"),
            ),
        ]
        findings = validate_task_dag(tasks)
        errors = [f for f in findings if f.severity == "error"]
        assert any("duplicados" in e.message.lower() for e in errors)
