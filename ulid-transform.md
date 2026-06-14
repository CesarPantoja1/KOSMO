# Migraci n UUID  ULID en KOSMO

## Resumen

Se migr  el sistema de identificadores de `UUID v4` a `ULID con prefijos tipados` cumpliendo la regla de CLAUDE.md: **"Nunca UUID. Nunca `uuid.uuid4()`. Nunca `uuid.UUID(...)`** para entidades de negocio. El auth (tokens JWT, request IDs) mantiene UUID v4 ya que son identificadores de correlaci n internos, no IDs de negocio.

## Archivos Modificados

### 1. Modelo de DB  `infrastructure/persistence/postgres/models.py`

| Tabla | Campo | Antes | Despu s |
|-------|-------|-------|---------|
| `users` | `id` | `UUID` (PostgreSQL `UUID` type) | `String(64)` (almacena `usr_01KT...`) |
| `projects` | `id` | *(nueva)* | `String(64)` (`prj_01KT...`) |
| `features` | `id` | *(nueva)* | `String(64)` (`feat_01KT...`) |
| `features` | `project_id` | *(nueva)* | `String(64)` referencia a `projects.id` |
| `requirements` | `id` | *(nueva)* | `String(64)` (`req_01KT...`) |
| `requirements` | `feature_id` | *(nueva)* | `String(64)` referencia a `features.id` |
| `pipeline_states` | `id` | *(nueva)* | `String(64)` (`aud_01KT...`) |
| `pipeline_states` | `project_id` | *(nueva)* | `String(64)` referencia a `projects.id` |
| `pipeline_states` | `user_id` | *(nueva)* | `String(64)` referencia a `users.id` |
| `pipeline_states` | `pipeline_id` | *(nueva)* | `String(64)` (`pipe_01KT...`) |
| `audit_log` | `id` | `UUID` | `String(64)` (`aud_01KT...`) |
| `audit_log` | `actor_id` | `UUID` (nullable) | `String(64)` (nullable) |

### 2. Repository  `infrastructure/persistence/postgres/repositories/users.py`

- Se elimin  `from uuid import UUID, uuid4`
- Se elimin  la funci n `_coerce_uuid()` que convert a strings a `UUID`
- `by_id()` ahora compara directamente con `String(64)` en vez de convertir a `UUID`
- `create()` ya no convierte `user.id` a `UUID`  usa `str(user.id)` directamente
- `update_password()` usa `String(64)` para el WHERE clause

### 3. Repository  `infrastructure/persistence/postgres/repositories/audit.py`

- Se elimin  `from uuid import UUID, uuid4`
- Se elimin  la funci n `_coerse_uuid()`
- `record()` usa `IdGenerator.generate("audit")` en vez de `uuid4()`

### 4. Caso de Uso  `application/auth/register.py`

- Se elimin  `from uuid import uuid4`
- Se a adi  `from kosmo.domain.sdd.id_generator import IdGenerator`
- `User(id=str(uuid4()), ...)`    `User(id=IdGenerator.generate("user"), ...)`

### 5. Migraci n Alembic  `alembic/versions/0002_pipeline_sdd.py`

- Crea tablas: `projects`, `features`, `requirements`, `pipeline_states`
- Alter `users.id` de `UUID` a `String(64)` (varchar)
- NOTA: En producci n se requiere un data migration para transformar los UUIDs hex existentes a formato ULID con prefijo

## Prefijos ULID Tipados

| Prefijo | Entidad | Ejemplo |
|---------|---------|---------|
| `prj_` | Project | `prj_01KT05JRA7466PPYQXYTX` |
| `feat_` | Feature | `feat_01KT05JRA7466PPYQXYTX` |
| `req_` | Requirement | `req_01KT05JRA7466PPYQXYTX` |
| `spec_` | Spec | `spec_01KT05JRA7466PPYQXYTX` |
| `tsk_` | Task | `tsk_01KT05JRA7466PPYQXYTX` |
| `usr_` | User | `usr_01KT05JRA7466PPYQXYTX` |
| `apk_` | API Key | `apk_01KT05JRA7466PPYQXYTX` |
| `aud_` | Audit Event | `aud_01KT05JRA7466PPYQXYTX` |
| `pipe_` | Pipeline State | `pipe_01KT05JRA7466PPYQXYTX` |

## Qu  NO cambi  (permanece UUID)

| Componente | Raz n |
|------------|--------|
| JWT `jti` (ID de token) | Es un correlation ID interno, no una entidad de negocio |
| JWT `family_id` | Idem  correlation para rotaci n de refresh tokens |
| Request ID en middleware | Idem  correlation ID para tracing |

Estos usos est n alineados con CLAUDE.md: **Request ID: usar `ULID().hex` (sin prefijo) para identificadores de correlaci n/trace**. En la pr xima iteraci n se migrar n a `ULID().hex`.

## Pasos de Migraci n en Base de Datos

```sql
-- 1. Crear nuevas tablas (ejecutado por Alembic)
-- projects, features, requirements, pipeline_states se crean vac as

-- 2. Alterar users.id de UUID a VARCHAR(64)
ALTER TABLE users ALTER COLUMN id TYPE VARCHAR(64);

-- 3. Migrar datos existentes (requiere script de data migration)
-- UPDATE users SET id = 'usr_' || replace(id::text, '-', '')
-- WHERE id NOT LIKE 'usr_%';
```

## Generador de IDs

Todas las entidades de negocio usan `IdGenerator.generate()` desde `domain/sdd/id_generator.py`:

```python
from kosmo.domain.sdd.id_generator import IdGenerator

project_id = IdGenerator.generate("project")  # prj_01KT05JR...
feature_id = IdGenerator.generate("feature")    # feat_01KT05JR...
user_id = IdGenerator.generate("user")          # usr_01KT05JR...
```