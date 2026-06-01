"""
Prueba End-to-End del pipeline SDD en KOSMO.

Ejecutar con:
    uv run python tests/e2e/test_sdd_pipeline.py

Verifica el flujo completo: Discovery -> Requirements EARS -> Design UML -> Tasks.
Usa implementaciones en memoria para evitar dependencias externas.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from kosmo.application.sdd.capture import CaptureDiscoveryUseCase
from kosmo.application.sdd.design import GenerateDesignUseCase
from kosmo.application.sdd.requirements import GenerateRequirementsUseCase
from kosmo.application.sdd.tasks import DecomposeTasksUseCase
from kosmo.contracts.llm.ports import PromptTemplate
from kosmo.contracts.sdd.ids import ProjectId


class RealisticLLMClient:
    """LLMClient que devuelve respuestas realistas predefinidas para pruebas."""

    def __init__(self) -> None:
        self._call_count = 0

    async def complete(
        self,
        prompt: PromptTemplate,
        response_schema: type | None = None,
        temperature: float = 0,
        max_tokens: int | None = None,
        cache_key: str | None = None,
    ) -> object:
        self._call_count += 1
        from kosmo.contracts.llm.ports import LLMResponse, LLMUsage

        sys_msg = prompt.system_prompt.lower()

        if "analista" in sys_msg and "sdd" in sys_msg:
            content = json.dumps(
                {
                    "vision": "Sistema de gestion de tareas con autenticacion segura.",
                    "problem_space": "Usuarios necesitan gestionar tareas de forma colaborativa.",
                    "actors": "Administradores y usuarios regulares.",
                    "value_proposition": "Plataforma centralizada para gestion de tareas.",
                    "use_cases": "Crear, editar, eliminar y asignar tareas.",
                    "core_capabilities": "CRUD de tareas, Autenticacion JWT, Asignacion.",
                    "business_rules": "Solo el asignador puede modificar la tarea.",
                    "quality_attributes": "Alta disponibilidad, seguridad de datos.",
                    "scope": "Gestion de tareas con autenticacion basica.",
                }
            )
        elif "ears" in sys_msg and "ingeniero" in sys_msg:
            content = json.dumps(
                [
                    {
                        "id": "R-1",
                        "pattern": "event",
                        "trigger": "WHEN el usuario envia sus credenciales",
                        "system": "El sistema",
                        "response": "validara el email y contrasena contra la base de datos",
                        "acceptance_criteria": [
                            {"description": "Credenciales correctas retornan token JWT"},
                            {"description": "Credenciales incorrectas retornan error 401"},
                        ],
                        "source_statement": "WHEN el usuario envia sus credenciales, el sistema validara el email y contrasena contra la base de datos.",
                        "traceability": ["goal: Autenticar usuarios con JWT"],
                    },
                    {
                        "id": "R-2",
                        "pattern": "ubiquitous",
                        "trigger": None,
                        "system": "El sistema",
                        "response": "permitira crear, leer, actualizar y eliminar tareas",
                        "acceptance_criteria": [
                            {"description": "POST /tasks crea una tarea y retorna 201"},
                            {"description": "GET /tasks lista todas las tareas del usuario"},
                        ],
                        "source_statement": "El sistema permitira crear, leer, actualizar y eliminar tareas mediante una API REST.",
                        "traceability": ["goal: CRUD de tareas"],
                    },
                    {
                        "id": "R-3",
                        "pattern": "ubiquitous",
                        "trigger": None,
                        "system": "El sistema",
                        "response": "asociara cada tarea a un usuario autenticado",
                        "acceptance_criteria": [
                            {"description": "Cada tarea tiene un campo assigned_to"},
                        ],
                        "source_statement": "El sistema asociara cada tarea a un usuario autenticado.",
                        "traceability": ["goal: Asignacion de tareas"],
                    },
                ]
            )
        elif "arquitecto" in sys_msg and "ddd" in sys_msg:
            content = json.dumps(
                {
                    "classes": [
                        {
                            "id": "cls-1",
                            "name": "Task",
                            "attributes": [
                                {"name": "id", "type": "str"},
                                {"name": "title", "type": "str"},
                                {"name": "status", "type": "str"},
                            ],
                            "operations": [],
                        },
                        {
                            "id": "cls-2",
                            "name": "User",
                            "attributes": [
                                {"name": "id", "type": "str"},
                                {"name": "email", "type": "str"},
                            ],
                            "operations": [],
                        },
                        {
                            "id": "cls-3",
                            "name": "TaskService",
                            "attributes": [],
                            "operations": [
                                {"name": "create_task", "return_type": "Task"},
                                {"name": "list_tasks", "return_type": "list[Task]"},
                            ],
                        },
                        {
                            "id": "cls-4",
                            "name": "AuthService",
                            "attributes": [],
                            "operations": [
                                {"name": "authenticate", "return_type": "str"},
                            ],
                        },
                    ],
                    "relationships": [
                        {
                            "id": "rel-1",
                            "source_class_id": "cls-3",
                            "target_class_id": "cls-1",
                            "relationship_type": "association",
                            "source_cardinality": "1",
                            "target_cardinality": "*",
                            "label": "manages",
                        },
                        {
                            "id": "rel-2",
                            "source_class_id": "cls-3",
                            "target_class_id": "cls-4",
                            "relationship_type": "association",
                            "source_cardinality": "1",
                            "target_cardinality": "1",
                            "label": "uses",
                        },
                    ],
                    "boundaries": [
                        {
                            "name": "tasks",
                            "owned_modules": ["tasks.service", "tasks.model"],
                            "contract": {
                                "name": "TasksBoundary",
                                "methods": ["create_task", "list_tasks"],
                            },
                        },
                        {
                            "name": "auth",
                            "owned_modules": ["auth.service", "auth.model"],
                            "contract": {"name": "AuthBoundary", "methods": ["authenticate"]},
                        },
                    ],
                }
            )
        elif "planificador" in sys_msg and "descomposicion" in sys_msg:
            content = json.dumps(
                [
                    {
                        "id": "T-1",
                        "title": "Implementar entidad User",
                        "description": "Crear la clase User con email y password_hash",
                        "boundary": "auth",
                        "depends_on": [],
                        "requirements": ["R-1"],
                        "acceptance_criteria": ["User tiene campos id, email, password_hash"],
                        "parallelizable": True,
                    },
                    {
                        "id": "T-2",
                        "title": "Implementar AuthService",
                        "description": "Crear servicio de autenticacion con JWT",
                        "boundary": "auth",
                        "depends_on": ["T-1"],
                        "requirements": ["R-1"],
                        "acceptance_criteria": ["Login retorna JWT valido"],
                        "parallelizable": False,
                    },
                    {
                        "id": "T-3",
                        "title": "Implementar entidad Task",
                        "description": "Crear la clase Task con CRUD",
                        "boundary": "tasks",
                        "depends_on": [],
                        "requirements": ["R-2", "R-3"],
                        "acceptance_criteria": ["Task tiene campos id, title, status, assigned_to"],
                        "parallelizable": True,
                    },
                    {
                        "id": "T-4",
                        "title": "Implementar TaskService",
                        "description": "Crear servicio CRUD de tareas",
                        "boundary": "tasks",
                        "depends_on": ["T-3", "T-2"],
                        "requirements": ["R-2", "R-3"],
                        "acceptance_criteria": [
                            "POST /tasks crea tarea",
                            "GET /tasks lista tareas del usuario",
                        ],
                        "parallelizable": False,
                    },
                ]
            )
        elif sys_msg.startswith("corrige"):
            content = json.dumps(
                {
                    "id": "R-99",
                    "pattern": "ubiquitous",
                    "trigger": None,
                    "system": "El sistema",
                    "response": "corregira el error detectado",
                    "acceptance_criteria": [{"description": "Correccion aplicada"}],
                    "source_statement": "El sistema corregira el error detectado.",
                    "traceability": [],
                }
            )
        else:
            content = "{}"

        return LLMResponse(
            content=content,
            usage=LLMUsage(prompt_tokens=100, completion_tokens=200, total_tokens=300),
            model_id="mock-realistic",
        )

    async def stream(
        self, prompt: PromptTemplate, temperature: float = 0, max_tokens: int | None = None
    ) -> object:
        class _EmptyStream:
            async def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        return _EmptyStream()


class InMemorySpecRepository:
    """Repositorio en memoria para pruebas sin PostgreSQL."""

    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    async def add(self, spec: object) -> None:
        self._store[spec.id] = spec  # type: ignore[attr-defined]

    async def get(self, spec_id: object) -> object | None:
        return self._store.get(spec_id)  # type: ignore[return-value]

    async def update(self, spec: object) -> None:
        self._store[spec.id] = spec  # type: ignore[attr-defined]

    async def list_by_project(self, project_id: str) -> list[object]:
        return list(self._store.values())


async def main() -> None:
    llm = RealisticLLMClient()
    repo = InMemorySpecRepository()
    project_id = ProjectId("test-project-1")

    capture_uc = CaptureDiscoveryUseCase(spec_repo=repo, llm_client=llm)  # type: ignore[arg-type]
    spec = await capture_uc.execute(
        project_id=project_id,
        description="API REST para gestion de tareas con autenticacion JWT.",
    )

    assert spec.discovery is not None

    req_uc = GenerateRequirementsUseCase(spec_repo=repo, llm_client=llm)  # type: ignore[arg-type]
    spec = await req_uc.execute(spec.id)

    assert len(spec.requirements) > 0
    for _req in spec.requirements:
        pass

    design_uc = GenerateDesignUseCase(spec_repo=repo, llm_client=llm)  # type: ignore[arg-type]
    spec = await design_uc.execute(spec.id)

    assert spec.design is not None
    for _cls in spec.design.classes:
        pass
    for _b in spec.design.boundaries:
        pass

    assert spec.design.plantuml, "PlantUML no debe estar vacio"
    assert spec.design.xmi, "XMI no debe estar vacio"

    tasks_uc = DecomposeTasksUseCase(spec_repo=repo, llm_client=llm)  # type: ignore[arg-type]
    spec = await tasks_uc.execute(spec.id)

    assert len(spec.tasks) > 0
    for _task in spec.tasks:
        pass

    task_ids = {t.id for t in spec.tasks}
    for t in spec.tasks:
        for dep in t.depends_on:
            assert dep in task_ids, f"Tarea {t.id} depende de {dep} que no existe"


if __name__ == "__main__":
    asyncio.run(main())
