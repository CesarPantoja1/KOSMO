from kosmo.contracts.sdd.domain_model import DomainModel
from kosmo.contracts.sdd.tasks import Task


class ValidationFinding:
    def __init__(self, code: str, severity: str, message: str, field: str = "") -> None:
        self.code = code
        self.severity = severity
        self.message = message
        self.field = field


def validate_task_dag(
    tasks: list[Task], model: DomainModel | None = None
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    task_ids = {t.id for t in tasks}
    if len(task_ids) < len(tasks):
        findings.append(ValidationFinding("TD001", "error", "IDs de tarea duplicados", "tasks"))

    for task in tasks:
        if not task.boundary:
            findings.append(
                ValidationFinding(
                    "TD002", "error", f"Tarea {task.id}: sin frontera asignada", "boundary"
                )
            )

        for dep_id in task.depends_on:
            if dep_id not in task_ids:
                findings.append(
                    ValidationFinding(
                        "TD003",
                        "error",
                        f"Tarea {task.id}: depende de tarea inexistente {dep_id}",
                        "depends_on",
                    )
                )

    if model and model.boundaries:
        boundary_names = {b.name for b in model.boundaries}
        for task in tasks:
            if task.boundary and task.boundary not in boundary_names:
                findings.append(
                    ValidationFinding(
                        "TD004",
                        "warning",
                        f"Tarea {task.id}: frontera '{task.boundary}' no declarada en el modelo",
                        "boundary",
                    )
                )

    findings.extend(_check_cycles(tasks))

    return findings


def _check_cycles(tasks: list[Task]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    graph: dict[str, list[str]] = {t.id: [str(d) for d in t.depends_on] for t in tasks}
    visited: set[str] = set()
    stack: set[str] = set()

    def dfs(node: str) -> bool:
        visited.add(node)
        stack.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in stack:
                findings.append(
                    ValidationFinding(
                        "TD005", "error", "Ciclo detectado en el DAG de tareas", "depends_on"
                    )
                )
                return True
        stack.discard(node)
        return False

    for task_id in graph:
        if task_id not in visited and dfs(task_id):
            break

    return findings
