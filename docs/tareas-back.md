# Mapeo de Tareas de Backend - Sprint Planning

Este documento mapea cada tarea de backend del sprint planning con los archivos implementados en la rama `poc-agent`.

---

## HU-01 · Nuevo proyecto

### Tarea HU-01/T1 - Definir entidad Proyecto

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/contracts/sdd/__init__.py` | Exports de entidades y tipos SDD |
| `backend/src/kosmo/contracts/sdd/ids.py` | Definición de `ProjectId`, `UserId` y otros tipos |
| `backend/src/kosmo/contracts/sdd/project.py` | Entidad `Project` con todos sus atributos |
| `backend/src/kosmo/contracts/sdd/errors.py` | Errores transversales (ProjectNotFoundError, etc.) |

### Tarea HU-01/T2 - Establecer puerto ProyectoRepository

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/contracts/sdd/repositories.py` | Interfaz `ProjectRepository` |

### Tarea HU-01/T3 - Implementar ProjectRepository (SQLAlchemy)

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/infrastructure/persistence/postgres/repositories/__init__.py` | Exports de repositorios |
| `backend/src/kosmo/infrastructure/persistence/postgres/repositories/project_repo.py` | Implementación `SqlAlchemyProjectRepository` |

### Tarea HU-01/T4 - Desarrollar CreateProjectUseCase

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/application/projects/__init__.py` | Exports de use cases |
| `backend/src/kosmo/application/projects/create_project.py` | `CreateProjectUseCase` |
| `backend/src/kosmo/application/projects/get_project.py` | `GetProjectUseCase` |
| `backend/src/kosmo/application/projects/list_projects.py` | `ListProjectsUseCase` |

### Tarea HU-01/T5 - Exponer router HTTP de proyectos

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/infrastructure/api/routers/__init__.py` | Init del módulo |
| `backend/src/kosmo/infrastructure/api/routers/projects.py` | Routers POST/GET/GET/{id} |
| `backend/src/kosmo/infrastructure/api/routers/helpers.py` | Helper `resolve_project` |

---

## HU-03 · Creación de la visión del producto software con IA

### Tarea HU-03/T1 - Establecer puertos LLMClient y PhaseMode

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/contracts/llm/__init__.py` | Exports LLM |
| `backend/src/kosmo/contracts/llm/ports.py` | Interfaces `LLMClient`, `LLMResponse`, `PromptTemplate` |
| `backend/src/kosmo/contracts/pipeline/__init__.py` | Exports de pipeline |
| `backend/src/kosmo/contracts/pipeline/orchestrator_ports.py` | Interfaz `PhaseMode`, `ToolDefinition`, `ToolResult` |
| `backend/src/kosmo/contracts/pipeline/phase_contexts.py` | Tipos de contexto (`DiscoveryPhaseContext`, etc.) |
| `backend/src/kosmo/contracts/pipeline/phase_outputs.py` | Tipos de output (`DiscoveryPhaseOutput`, etc.) |
| `backend/src/kosmo/contracts/pipeline/phase_errors.py` | Errores de fase (`PhaseTransitionError`) |

### Tarea HU-03/T2 - Definir entidad DocumentoDescubrimiento y su repositorio

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/contracts/sdd/document.py` | `RichTextDocument`, `DocumentNode`, `SpecPhase`, enums |

### Tarea HU-03/T3 - Orquestar KOSMOAgent y ContextBuilder

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/domain/pipeline/__init__.py` | Exports del pipeline |
| `backend/src/kosmo/domain/pipeline/kosmo_agent.py` | Clase `KOSMOAgent` completa |
| `backend/src/kosmo/domain/pipeline/context_builder.py` | Clase `ContextBuilder` |

### Tarea HU-03/T4 - Construir SequentialOrchestrator y guardrails

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/contracts/sdd/guardrails.py` | Términos prohibidos y `GuardrailResult` |
| `backend/src/kosmo/domain/pipeline/sequential_orchestrator.py` | Clase `SequentialOrchestrator` |
| `backend/src/kosmo/domain/sdd/output_guardrails.py` | Funciones `detect_technical_terms`, `auto_repair_technical_terms` |

### Tarea HU-03/T5 - Elaborar DiscoveryMode

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/domain/pipeline/phase_modes/__init__.py` | Exports de modos de fase |
| `backend/src/kosmo/domain/pipeline/phase_modes/discovery_mode.py` | Clase `DiscoveryMode` con system prompt |

### Tarea HU-03/T6 - Desarrollar validadores de descubrimiento

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/domain/pipeline/phase_validators/__init__.py` | Exports de validadores |
| `backend/src/kosmo/domain/pipeline/phase_validators/discovery_validator.py` | `validate_discovery_structure`, `validate_discovery_quality` |

### Tarea HU-03/T7 - Integrar adaptadores LLM (PydanticAI + Noop)

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/infrastructure/llm/__init__.py` | Exports de adapters |
| `backend/src/kosmo/infrastructure/llm/pydantic_ai_adapter.py` | `PydanticAILLMClient` |
| `backend/src/kosmo/infrastructure/llm/noop_adapter.py` | `NoopLLMClient` (desarrollo) |

### Tarea HU-03/T8 - Configurar cableado de dependencias (composition.py)

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/infrastructure/api/composition.py` | Función `build_pipeline_components` y `build_auth_components` |

### Tarea HU-03/T9 - Implementar DiscoveryDocumentRepository (SQLAlchemy)

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/infrastructure/persistence/postgres/repositories/document_repo.py` | `SqlAlchemyDocumentRepository` |

### Tarea HU-03/T10 - Desarrollar GenerateDiscoveryUseCase

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/application/discovery/__init__.py` | Exports de discovery |
| `backend/src/kosmo/application/discovery/generate_discovery.py` | `GenerateDiscoveryUseCase` |
| `backend/src/kosmo/application/discovery/get_discovery.py` | `GetDiscoveryUseCase` |
| `backend/src/kosmo/application/discovery/save_discovery.py` | `SaveDiscoveryUseCase` |

### Tarea HU-03/T11 - Exponer routers HTTP de descubrimiento

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/infrastructure/api/routers/discovery.py` | Routers POST/GET/PUT discovery |

---

## HU-05 · Creación de las características del producto software con IA

### Tarea HU-05/T1 - Definir entidad Caracteristica y FeatureRepository

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/contracts/sdd/feature.py` | Entidad `Feature` |
| `backend/src/kosmo/contracts/sdd/repositories.py` | Interfaz `FeatureRepository` (ya incluida en HU-01/T2) |

### Tarea HU-05/T2 - Implementar FeatureRepository (SQLAlchemy)

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/infrastructure/persistence/postgres/repositories/feature_repo.py` | `SqlAlchemyFeatureRepository` |

### Tarea HU-05/T3 - Elaborar FeaturesMode y sus validadores

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/domain/pipeline/phase_modes/features_mode.py` | Clase `FeaturesMode` |
| `backend/src/kosmo/domain/pipeline/phase_validators/features_validator.py` | `validate_features_structure`, `validate_features_semantic` |

### Tarea HU-05/T4 - Desarrollar GenerateFeaturesUseCase y SuggestFeaturesUseCase

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/application/features/__init__.py` | Exports de features |
| `backend/src/kosmo/application/features/generate_features.py` | `GenerateFeaturesUseCase` |
| `backend/src/kosmo/application/features/save_features.py` | `SuggestFeaturesUseCase`, `SaveSelectedFeaturesUseCase` |

### Tarea HU-05/T5 - Exponer routers HTTP de características

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/infrastructure/api/routers/features.py` | Routers GET/POST features, suggest, save |

---

## HU-09 · Creación de requisitos del producto software mediante IA

### Tarea HU-09/T1 - Definir entidad Requisito y RequirementRepository

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/contracts/sdd/ears.py` | Entidad `EARSRequirement` |
| `backend/src/kosmo/contracts/sdd/repositories.py` | Interfaz `RequirementRepository` (ya incluida en HU-01/T2) |

### Tarea HU-09/T2 - Implementar RequirementRepository (SQLAlchemy)

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/infrastructure/persistence/postgres/repositories/requirement_repo.py` | `SqlAlchemyRequirementRepository` |

### Tarea HU-09/T3 - Elaborar EARSMode y sus validadores

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/domain/sdd/__init__.py` | Exports de SDD domain |
| `backend/src/kosmo/domain/sdd/id_generator.py` | Clase `IdGenerator` |
| `backend/src/kosmo/domain/sdd/document_converters.py` | Conversores markdown ↔ documento |
| `backend/src/kosmo/domain/sdd/few_shot/__init__.py` | Init vacío |
| `backend/src/kosmo/domain/sdd/validators/__init__.py` | Init vacío |
| `backend/src/kosmo/domain/sdd/validators/ears_validator.py` | `validate_ears_syntax`, `validate_ears_quality` |
| `backend/src/kosmo/domain/pipeline/phase_modes/ears_mode.py` | Clase `EARSMode` con system prompt |

### Tarea HU-09/T4 - Desarrollar GenerateEARSUseCase

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/application/requirements/__init__.py` | Exports de requirements |
| `backend/src/kosmo/application/requirements/generate_ears.py` | `GenerateEARSUseCase`, `GetRequirementsUseCase` |
| `backend/src/kosmo/application/requirements/save_requirements.py` | `SaveRequirementsUseCase` |

### Tarea HU-09/T5 - Exponer routers HTTP de requisitos

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/infrastructure/api/routers/requirements.py` | Routers GET/POST/PUT requirements |

---

## Archivos Transversales (necesarios para el sistema, no asignados a tarea específica)

| Archivo | Descripción |
|---------|-------------|
| `backend/src/kosmo/infrastructure/persistence/postgres/models.py` | Modelos SQLAlchemy (ProjectModel, FeatureModel, RequirementModel, DiscoveryDocumentModel) |
| `backend/src/kosmo/infrastructure/persistence/postgres/__init__.py` | Exports actualizados |
| `backend/alembic/env.py` | Configuración Alembic con dotenv |

---

## Migraciones de Alembic (nuevas en poc-agent, no existen en develop)

| Archivo | Descripción |
|---------|-------------|
| `backend/alembic/versions/0002_pipeline_sdd.py` | Tablas iniciales SDD |
| `backend/alembic/versions/5b5161b3a623_remove_raw_idea_from_pipeline_states.py` | Remover raw_idea |
| `backend/alembic/versions/769f4fa2d80c_rename_discovery_documents_to_discovery.py` | Renombrar tabla |
| `backend/alembic/versions/9313ffd42cf9_add_discovery_documents_table.py` | Añadir discovery |
| `backend/alembic/versions/afd0ad8dfb71_drop_pipeline_states.py` | Drop pipeline_states |
| `backend/alembic/versions/db75f0b14dc8_simplify_requirements_move_blob.py` | Simplificar requirements |
| `backend/alembic/versions/e5e0bda961df_add_slug_to_projects.py` | Añadir slug a projects |
| `backend/alembic/versions/f2f6de23e76e_remove_feature_status.py` | Remover feature status |

**Nota:** Las migraciones `0001_users.py` y `0002_audit_log.py` ya existen en `develop`.

---

## Verificación

- [x] Cada archivo aparece en exactamente una tarea
- [x] No hay duplicaciones de archivos entre tareas
- [x] Todos los archivos SDD del backend están mapeados
- [x] Las migraciones de Alembic están documentadas
- [x] Los archivos transversales están identificados
