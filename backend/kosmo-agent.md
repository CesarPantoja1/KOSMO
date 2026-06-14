# KOSMO Agent — Documentación técnica

## Visión general

KOSMO tiene **un solo agente** (`KOSMOAgent`) que opera en 3 fases secuenciales: **Descubrimiento → Características → Requisitos EARS**. Usa el patrón **Strategy** para cambiar el prompt, la validación y el comportamiento según la fase.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                       KOSMOAgent                            │
│                                                             │
│  execute(phase, context)                                    │
│    │                                                        │
│    ├─► PhaseMode.system_prompt                              │
│    ├─► PhaseMode.build_user_prompt(context)                 │
│    │                                                        │
│    └─► Loop (max_correction_cycles + 1 intentos):           │
│         1. LLMClient.complete(prompt, temp, max_tokens)     │
│         2. _parse_llm_response(text)                        │
│         3. PhaseMode.validate_output(content)               │
│         4. Si válido → return _build_phase_output()         │
│         5. Si no → build_retry_prompt() → reintentar        │
└─────────────────────────────────────────────────────────────┘
```

---

## Componentes clave

### 1. `KOSMOAgent` (`domain/pipeline/kosmo_agent.py`)

#### Constructor
| Parámetro | Tipo | Descripción |
|---|---|---|
| `llm_client` | `LLMClient` | Adapter al proveedor LLM (DeepSeek, OpenAI, Noop) |
| `context_builder` | `ContextBuilder` | Construye el contexto específico de cada fase |
| `modes` | `dict[SpecPhase, PhaseMode]` | Mapa fase → estrategia de prompt y validación |
| `max_correction_cycles` | `int` (default 1) | Intentos máximos de corrección tras validación fallida |

#### `execute(phase, context)` — async

1. Selecciona el `PhaseMode` según la fase
2. Construye el prompt con `system_prompt` (instrucciones) + `user_prompt` (datos del proyecto)
3. Itera hasta `max_correction_cycles + 1` veces:
   - Llama al LLM con temperatura y max_tokens específicos por fase
   - Parsea la respuesta (JSON → dict; si falla, envuelve en `{"raw_text": text}`)
   - Valida el output con `PhaseMode.validate_output()`
   - Si es válido → retorna `DiscoveryPhaseOutput | FeaturesPhaseOutput | EARSPhaseOutput`
   - Si no → `build_retry_prompt()` + reintenta
4. Si agota todos los intentos, retorna el último output generado (aunque sea inválido)

#### `execute_suggest(context)` — async

Prompt independiente para sugerir 3 features adicionales. No usa `PhaseMode`. Genera el prompt manualmente con el discovery + títulos existentes, y llama al LLM una sola vez.

### 2. `PhaseMode` (protocolo en `contracts/pipeline/orchestrator_ports.py`)

| Método | Propósito |
|---|---|
| `system_prompt` | Instrucciones de rol, formato de salida y guardrails |
| `build_user_prompt(context)` | Construye el prompt con datos del proyecto |
| `validate_output(output)` | Valida estructura y calidad del output del LLM |
| `build_retry_prompt(original, errors, retry_count)` | Construye prompt de corrección con errores detectados |

### 3. Implementaciones de `PhaseMode`

| Fase | Clase | Validación |
|---|---|---|
| `DESCUBRIMIENTO` | `DiscoveryMode` | 9 secciones requeridas, sin términos técnicos, sin formato HU, output directo sin intro |
| `CARACTERISTICAS` | `FeaturesMode` | 5 features en JSON `{"features": [...]}`, título ≤ 6 palabras, slugs únicos |
| `REQUISITOS` | `EARSMode` | JSON con `{"requirements": [...]}`, sintaxis EARS por categoría, 3-15 requisitos, 4+ categorías |

### 4. `ContextBuilder` (`domain/pipeline/context_builder.py`)

Construye el contexto para cada fase consultando las tablas correspondientes:

| Fase | Contexto | Fuentes consultadas |
|---|---|---|
| Descubrimiento | `project_name`, `project_description` | `projects` (tabla) |
| Características | `discovery_document`, `existing_feature_titles` | `discovery` (tabla), `features` (tabla) |
| Requisitos | `discovery_document`, `feature` (por id) | `discovery` (tabla), `features` (tabla) |

### 5. `LLMClient` (adapter en `infrastructure/llm/`)

| Adapter | Uso |
|---|---|
| `PydanticAILLMClient` | Producción — conecta a DeepSeek vía API compatible con OpenAI |
| `NoopLLMClient` | Desarrollo — retorna datos mock sin llamar al LLM |

---

## Flujo completo por fase

### Fase 1: Descubrimiento

```
POST /projects/{id}/discovery/generate
  │
  ▼
GenerateDiscoveryUseCase
  │
  ├─► project_repo.by_id()           → verifica que el proyecto existe
  ├─► project_repo.update_phase()    → marca fase = descubrimiento
  ├─► context_builder.build_context(DESCUBRIMIENTO)
  │     └─► project_repo.by_id() → project_name + project_description
  │
  ├─► agent.execute(DESCUBRIMIENTO, context)
  │     │
  │     ├─► DiscoveryMode.system_prompt     → analista de negocio, ReAct, 9 secciones
  │     ├─► DiscoveryMode.build_user_prompt → "## Proyecto\nNombre: ...\nDescripción: ..."
  │     │
  │     └─► Loop LLM:
  │           1. LLM genera markdown directamente (sin JSON)
  │           2. Validación: ¿9 secciones? ¿sin términos técnicos? ¿sin "Como... quiero..."?
  │           3. Si falla → retry con errores
  │
  ├─► document_repo.save_discovery() → persiste en tabla `discovery`
  │
  └─► Response: { document_markdown: "## Visión del producto\n..." }
```

### Fase 2: Características

```
POST /projects/{id}/features/generate
  │
  ▼
GenerateFeaturesUseCase
  │
  ├─► orchestrator.validate_transition() → ¿existe discovery en tabla `discovery`?
  ├─► context_builder.build_context(CARACTERISTICAS)
  │     ├─► document_repo.get_discovery()      → discovery markdown
  │     └─► feature_repo.list_by_project()     → títulos existentes
  │
  ├─► agent.execute(CARACTERISTICAS, context)
  │     │
  │     ├─► FeaturesMode.system_prompt     → diseñador de producto, 5 features en JSON
  │     ├─► FeaturesMode.build_user_prompt → discovery + títulos existentes
  │     │
  │     └─► Loop LLM:
  │           1. LLM genera JSON {"features": [{"number":1, "title":"...", ...}]}
  │           2. _parse_llm_response → extrae JSON del bloque ```json
  │           3. Validación: ¿dict con "features"? ¿5 features? ¿títulos ≤ 6 palabras?
  │           4. Si falla → retry con errores
  │
  ├─► feature_repo.save() por cada feature  → persiste en tabla `features`
  │
  └─► Response: { features: [{display_id, title, slug, description}], total: 5 }
```

### Fase 3: Requisitos EARS

```
POST /features/{id}/requirements/generate
  │
  ▼
GenerateEARSUseCase
  │
  ├─► Resuelve feature_id (ULID o slug) vía feature_repo
  ├─► orchestrator.validate_transition() → ¿existen features en tabla `features`?
  ├─► context_builder.build_ears_context_for_feature()
  │     ├─► document_repo.get_discovery()  → discovery markdown
  │     └─► feature_repo.by_id()           → feature específica
  │
  ├─► agent.execute(REQUISITOS, context)
  │     │
  │     ├─► EARSMode.system_prompt     → ingeniero de requisitos, 6 categorías EARS
  │     ├─► EARSMode.build_user_prompt → discovery + feature data
  │     │
  │     └─► Loop LLM:
  │           1. LLM genera JSON {"requirements": [{pattern:"ubiquitous", ...}]}
  │           2. Validación: sintaxis EARS por categoría, 3-15 reqs, 4+ categorías
  │           3. Si falla → retry con errores
  │
  ├─► requirement_repo.save()  → persiste markdown en tabla `requirements`
  │
  └─► Response: { feature_id, feature_number, requirements_markdown, total }
```

---

## Temperatura y tokens por fase

| Fase | Temperatura | Max Tokens | Razón |
|---|---|---|---|
| Descubrimiento | 0.3 | 8192 | Documento largo (9 secciones), necesita creatividad controlada |
| Características | 0.2 | 4096 | 5 features en JSON estructurado, más determinístico |
| Requisitos | 0.1 | 4096 | Máximo rigor, sintaxis EARS estricta |

---

## Validación programática

Después de cada respuesta del LLM, se ejecuta validación en 2 niveles:

### Estructura
- ¿El output tiene el formato esperado? (dict con la clave correcta, lista no vacía)
- ¿Están todas las secciones requeridas?
- ¿Hay suficiente contenido? (word count mínimo)

### Calidad
- ¿Hay términos técnicos prohibidos? (`API`, `base de datos`, `endpoint`, etc.)
- ¿Usa formato de historia de usuario en vez de caso de uso?
- ¿Los requisitos siguen la sintaxis EARS de su categoría?
- ¿Hay suficientes categorías EARS representadas?

### Auto-reparación
Antes de validar calidad, se aplica `auto_repair_technical_terms()` que reemplaza fugas comunes:
- `"almacenará en la base de datos"` → `"registrará y mantendrá"`
- `"enviará una petición HTTP"` → `"comunicará a"`

---

## Persistencia

| Entidad | Tabla | Formato |
|---|---|---|
| Proyecto | `projects` | Columnas tipadas (id, name, slug, description, owner_id, phase, status, timestamps) |
| Discovery | `discovery` | `project_id` (PK), `markdown` (TEXT) |
| Features | `features` | Columnas tipadas (id, project_id, number, title, slug, description, rationale, inferred_from, timestamps) |
| Requisitos | `requirements` | `feature_id` (PK), `markdown` (TEXT) |

---

## Flujo de navegación (rutas)

Todas las rutas bajo `/projects/{id_or_slug}` aceptan **ULID** (`prj_01...`) o **slug** (`mi-proyecto`). La resolución se hace con `resolve_project()` que detecta el prefijo.

```
/projects/{id}
  ├─► GET     → obtener proyecto
  ├─► /discovery
  │     ├─► POST /generate  → generar discovery (IA)
  │     ├─► GET             → obtener discovery
  │     └─► PUT             → guardar discovery (edición)
  ├─► /features
  │     ├─► POST /generate  → generar 5 features (IA)
  │     ├─► GET             → listar features
  │     ├─► POST /suggest   → sugerir 3 features (IA)
  │     ├─► POST            → guardar features seleccionadas
  │     └─► GET /{slug}     → obtener feature por slug (detalle completo)
  └─► (requisitos usan /features/{id}/requirements/*)
        ├─► POST /generate  → generar requisitos EARS (IA)
        ├─► GET             → obtener requisitos markdown
        └─► PUT             → guardar requisitos (edición)
```

---

## Stack técnico

| Capa | Tecnología |
|---|---|
| LLM | DeepSeek Chat (vía API OpenAI-compatible con `pydantic-ai`) |
| Backend | Python 3.13 + FastAPI + Uvicorn |
| Persistencia | PostgreSQL 16 + asyncpg (SQLAlchemy asyncio) |
| Caché/Sesiones | Redis 7 |
| Seguridad | Argon2id (passwords), RS256 JWT (tokens), Fernet (secrets) |
| IDs | ULID con prefijo tipado (`prj_`, `feat_`, `usr_`) |
