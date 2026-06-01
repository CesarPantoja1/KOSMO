import json

from kosmo.contracts.llm.ports import LLMResponse, LLMUsage, PromptTemplate

_DISCOVERY_RESPONSE = json.dumps(
    {
        "vision": "Una plataforma web centralizada que permite a equipos gestionar tareas de forma colaborativa con trazabilidad completa y asignacion eficiente de responsabilidades.",
        "problem_space": "Los equipos actualmente gestionan tareas en hojas de calculo, correos electronicos y mensajeria, generando desorden, perdida de informacion y falta de trazabilidad sobre quien hace que y cuando. No existe un mecanismo centralizado que permita crear, asignar, seguir y completar tareas con un flujo claro.",
        "actors": "Administradores de proyecto: crean y asignan tareas, gestionan el equipo. Usuarios regulares: reciben tareas, las ejecutan y reportan avances. Usuarios no autenticados: solo pueden ver informacion publica del proyecto.",
        "value_proposition": "Centralizacion total de la gestion de tareas en una unica plataforma, eliminando la dispersion de informacion en multiples canales. Cada miembro del equipo sabe exactamente que hacer, cuando y para quien. Trazabilidad completa desde la creacion hasta la finalizacion de cada tarea.",
        "use_cases": "Un administrador crea un proyecto e invita a miembros del equipo. Un administrador crea una tarea y la asigna a un usuario. Un usuario recibe una notificacion de nueva tarea asignada. Un usuario marca una tarea como completada. Un administrador genera un reporte de avance del equipo.",
        "core_capabilities": "Gestion de proyectos con miembros del equipo. CRUD completo de tareas con titulo, descripcion y estado. Autenticacion segura mediante JWT con roles de usuario. Asignacion y reasignacion de tareas entre miembros. Dashboard de avance con metricas por usuario y proyecto. Historial de cambios y trazabilidad de cada tarea.",
        "business_rules": "Solo los administradores pueden crear proyectos y asignar tareas. Un usuario no puede modificar una tarea que no le ha sido asignada. Las tareas completadas no pueden ser eliminadas, solo archivadas. Los reportes solo son accesibles para administradores del proyecto. Cada tarea debe tener un responsable unico en todo momento.",
        "quality_attributes": "Disponibilidad del 99.5% durante horario laboral. Tiempo de respuesta menor a 500ms para operaciones CRUD. Autenticacion con tokens JWT rotativos. Interfaz responsive adaptable a dispositivos moviles. Cumplimiento de normativa de proteccion de datos personales.",
        "scope": "Incluye: gestion de tareas con CRUD, autenticacion JWT con roles, asignacion de tareas, dashboard basico de avance, historial de cambios. No incluye: integracion con calendarios externos, notificaciones por email o push, facturacion, integracion con ERP, aplicacion movil nativa.",
    }
)

_REQUIREMENTS_RESPONSE = json.dumps(
    [
        {
            "id": "R-1",
            "pattern": "event",
            "trigger": "WHEN el usuario envía sus credenciales",
            "system": "El sistema",
            "response": "validará el email y contraseña contra la base de datos",
            "acceptance_criteria": [
                {"description": "Credenciales correctas retornan token JWT"},
                {"description": "Credenciales incorrectas retornan error 401"},
            ],
            "source_statement": "WHEN el usuario envía sus credenciales, el sistema validará el email y contraseña contra la base de datos.",
            "traceability": ["goal: Autenticar usuarios con JWT"],
        },
        {
            "id": "R-2",
            "pattern": "ubiquitous",
            "trigger": None,
            "system": "El sistema",
            "response": "permitirá crear, leer, actualizar y eliminar tareas mediante una API REST",
            "acceptance_criteria": [
                {"description": "POST /tasks crea una tarea y retorna 201"},
                {"description": "GET /tasks lista todas las tareas del usuario"},
            ],
            "source_statement": "El sistema permitirá crear, leer, actualizar y eliminar tareas mediante una API REST.",
            "traceability": ["goal: CRUD de tareas"],
        },
        {
            "id": "R-3",
            "pattern": "ubiquitous",
            "trigger": None,
            "system": "El sistema",
            "response": "asociará cada tarea a un usuario autenticado",
            "acceptance_criteria": [
                {"description": "Cada tarea tiene un campo assigned_to"},
            ],
            "source_statement": "El sistema asociará cada tarea a un usuario autenticado.",
            "traceability": ["goal: Asignación de tareas"],
        },
    ]
)

_DESIGN_RESPONSE = json.dumps(
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
                "contract": {"name": "TasksBoundary", "methods": ["create_task", "list_tasks"]},
            },
            {
                "name": "auth",
                "owned_modules": ["auth.service", "auth.model"],
                "contract": {"name": "AuthBoundary", "methods": ["authenticate"]},
            },
        ],
    }
)

_TASKS_RESPONSE = json.dumps(
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
            "description": "Crear servicio de autenticación con JWT",
            "boundary": "auth",
            "depends_on": ["T-1"],
            "requirements": ["R-1"],
            "acceptance_criteria": ["Login retorna JWT válido"],
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

_BRIEF_REQUEST = json.dumps(
    {
        "id": "R-98",
        "pattern": "ubiquitous",
        "system": "El sistema",
        "response": "corregira el error",
        "source_statement": "El sistema corregira.",
        "acceptance_criteria": [],
        "traceability": [],
    }
)

_FEATURE_REQUIREMENTS_RESPONSE = json.dumps(
    {
        "ubiquitous": [
            {
                "pattern": "ubiquitous",
                "trigger": None,
                "system": "El sistema",
                "response": "permitira crear, leer, actualizar y eliminar tareas",
                "acceptance_criteria": [
                    {
                        "description": "POST /tasks crea una tarea y retorna 201",
                        "verified_by": "test de integracion",
                    },
                    {
                        "description": "GET /tasks lista todas las tareas del usuario",
                        "verified_by": "test de integracion",
                    },
                ],
                "source_statement": "El sistema shall permitir crear, leer, actualizar y eliminar tareas mediante una API REST.",
                "traceability": ["feature: Gestion de tareas"],
            },
            {
                "pattern": "ubiquitous",
                "trigger": None,
                "system": "El sistema",
                "response": "asociara cada tarea a un usuario autenticado",
                "acceptance_criteria": [
                    {
                        "description": "Cada tarea tiene un campo assigned_to no nulo",
                        "verified_by": "test unitario",
                    },
                ],
                "source_statement": "El sistema shall asociar cada tarea a un usuario autenticado.",
                "traceability": ["feature: Asignacion de tareas"],
            },
        ],
        "event": [
            {
                "pattern": "event",
                "trigger": "WHEN el usuario envia sus credenciales",
                "system": "El sistema",
                "response": "validara el email y contrasena contra la base de datos",
                "acceptance_criteria": [
                    {
                        "description": "Credenciales correctas retornan token JWT valido",
                        "verified_by": "test de integracion",
                    },
                    {
                        "description": "Credenciales incorrectas retornan error 401",
                        "verified_by": "test unitario",
                    },
                ],
                "source_statement": "WHEN el usuario envia sus credenciales, the system shall validar el email y contrasena contra la base de datos.",
                "traceability": ["feature: Autenticacion de usuarios"],
            },
        ],
        "state": [
            {
                "pattern": "state",
                "trigger": "WHILE la sesion del usuario esta activa",
                "system": "El sistema",
                "response": "renovara automaticamente el token de acceso",
                "acceptance_criteria": [
                    {
                        "description": "Token se renueva antes de expirar durante sesion activa",
                        "verified_by": "test de integracion",
                    },
                ],
                "source_statement": "WHILE la sesion del usuario esta activa, the system shall renovar automaticamente el token de acceso.",
                "traceability": ["feature: Seguridad de sesion"],
            },
        ],
        "optional": [],
        "unwanted": [
            {
                "pattern": "unwanted",
                "trigger": "IF la contrasena es ingresada incorrectamente tres veces",
                "system": "El sistema",
                "response": "bloqueara la cuenta por 15 minutos",
                "acceptance_criteria": [
                    {
                        "description": "Cuenta bloqueada tras 3 intentos fallidos consecutivos",
                        "verified_by": "test unitario",
                    },
                    {
                        "description": "Cuenta desbloqueada automaticamente tras 15 minutos",
                        "verified_by": "test de integracion",
                    },
                ],
                "source_statement": "IF la contrasena es ingresada incorrectamente tres veces, THEN the system shall bloquear la cuenta por 15 minutos.",
                "traceability": ["feature: Proteccion contra fuerza bruta"],
            },
        ],
        "complex": [],
    }
)


_SUGGEST_FROM_IDEA_RESPONSE = json.dumps(
    {
        "title": "Gestion de alertas de stock bajo",
        "description": "Permite a los administradores de inventario configurar umbrales minimos de stock por producto y recibir notificaciones automaticas cuando el inventario alcance niveles criticos, facilitando la reposicion oportuna y evitando quiebres de stock.",
    }
)


class NoopLLMClient:
    async def complete(  # noqa: ARG002
        self,
        prompt: PromptTemplate,
        response_schema: type | None = None,
        temperature: float = 0,
        max_tokens: int | None = None,
        cache_key: str | None = None,
    ) -> LLMResponse:
        sys_msg = prompt.system_prompt.lower()
        if "analista" in sys_msg and "sdd" in sys_msg:
            content = _DISCOVERY_RESPONSE
        elif "ingeniero" in sys_msg and "ears" in sys_msg and "senior" in sys_msg:
            content = _FEATURE_REQUIREMENTS_RESPONSE
        elif "ears" in sys_msg and "ingeniero" in sys_msg:
            content = _REQUIREMENTS_RESPONSE
        elif "ddd" in sys_msg and "arquitecto" in sys_msg:
            content = _DESIGN_RESPONSE
        elif "planificador" in sys_msg and "descomposicion" in sys_msg:
            content = _TASKS_RESPONSE
        elif sys_msg.startswith("corrige"):
            content = _BRIEF_REQUEST
        elif "formalizar" in sys_msg and "ideas" in sys_msg:
            content = _SUGGEST_FROM_IDEA_RESPONSE
        else:
            content = "{}"

        return LLMResponse(
            content=content,
            usage=LLMUsage(prompt_tokens=100, completion_tokens=200, total_tokens=300),
            model_id="noop-mock",
        )

    async def stream(  # noqa: ARG002
        self,
        prompt: PromptTemplate,
        temperature: float = 0,
        max_tokens: int | None = None,
    ) -> object:
        class _FakeStream:
            async def __aiter__(self) -> "_FakeStream":
                return self

            async def __anext__(self) -> str:
                raise StopAsyncIteration

        return _FakeStream()
