from __future__ import annotations

import contextlib
import dataclasses
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from kosmo.contracts.codegen import (
    CodeWorkspace,
    WorkspaceManagerPort,
    WorkspaceRepository,
    WorkspaceStatus,
)
from kosmo.contracts.sdd.ids import ProjectId, WorkspaceId
from kosmo.contracts.sdd.repositories import ProjectRepository

_IGNORED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        ".next",
        "dist",
        "build",
        "__pycache__",
        ".turbo",
        ".pytest_cache",
        ".coverage",
    }
)


def _generate_agents_md(project_name: str) -> str:
    """Genera el contenido de AGENTS.md para el workspace de implementación."""
    return f"""# {project_name} — Implementación generada por KOSMO

## Contexto
Este proyecto fue generado y es mantenido por KOSMO (Spec-Driven Development).
Cada Feature corresponde a un conjunto de Requirements EARS y un Activity Diagram.
El desarrollo es **test-first**: nunca se da una tarea por terminada sin validaciones verdes.

## Stack
- Next.js 16 (App Router) + React 19 + TypeScript estricto
- Drizzle ORM + SQLite (better-sqlite3)
- Vitest para tests
- Tailwind CSS + shadcn/ui
- ESLint (flat config)

## Comandos
```bash
npm install              # instalar dependencias
npx tsc --noEmit         # typecheck
npx eslint .             # lint
npx vitest run           # tests (suite completa)
npx next build           # compilación de producción
```

## Pipeline de validación (NON-NEGOTIABLE)
Toda tarea termina ÚNICAMENTE cuando este pipeline está completamente en verde.
1. `npx tsc --noEmit` — cero errores de tipos.
2. `npx eslint .` — cero errores de lint.
3. `npx vitest run` — todos los tests pasan.
4. `npx next build` — la compilación de producción es exitosa.

**Regla de cierre:** ejecuta las 4 validaciones tras cada cambio. Si alguna falla,
corrige los errores y vuelve a ejecutar **desde el principio** del pipeline. No declares
la tarea completada con validaciones en rojo, no dejes tests rotos "para después" y no
entregues código que no compila. Si un test falla por una razón legítima (spec cambió),
actualiza el test junto con la implementación y vuelve a validar.

## TDD (obligatorio)
Antes de escribir cualquier test, carga la skill `.opencode/skills/tdd/SKILL.md`.
Sigue estrictamente **Red-Green-Refactor**: test que falla → implementación mínima → refactor.
Toda funcionalidad nueva debe tener al menos happy path + error path cubiertos.

## Estructura
```text
src/
  app/           ← Next.js App Router (pages, layouts, API routes)
  components/    ← Componentes React reutilizables
  db/            ← Schema Drizzle, migraciones, queries
  lib/           ← Utilidades, tipos compartidos
  styles/        ← Estilos globales
tests/           ← Tests Vitest
```

## Convenciones (NON-NEGOTIABLE)
1. TypeScript estricto (`strict: true`). Cero `any` sin justificación.
2. Server Components por defecto; `'use client'` solo cuando necesario.
3. Drizzle ORM para toda persistencia. No SQL raw.
4. Cada archivo tiene un propósito único.
5. Nombres en inglés para código; UI en español.
6. Errores de API estructurados (status + `detail`), nunca strings sueltos.

## MCP Tools disponibles
- `get_requirements(feature_id)`: Obtener requirements EARS de una feature.
- `get_activity_diagram(feature_id)`: Obtener diagrama de actividad.
- `get_traceability(feature_id)`: Obtener archivos ya trazados a una feature.
- `get_related_features(feature_id)`: Features relacionadas para evitar duplicación.
- **token-savior**: para navegar el código generado usa sus tools (`find_symbol`,
  `get_edit_context`, `search_codebase`, `get_change_impact`) ANTES que grep/lectura de archivos.
- **context7**: para firmas exactas de Next.js, React, Drizzle, Tailwind o Vitest,
  consulta context7 en lugar de adivinar APIs de memoria.

## Anti-patrones prohibidos
- Lógica de negocio dentro de server components de rutas.
- `any` para silenciar errores de tipos.
- SQL raw fuera de Drizzle.
- Instalar dependencias sin justificación.
- Dejar tests rotos o saltarse validaciones para "avanzar".

## Reglas de modificación
- No instalar dependencias sin justificación.
- No modificar archivos de configuración raíz sin aprobación.
- Cada feature nueva debe tener tests.
- Respetar archivos existentes de otras features.
"""


def _generate_tdd_skill_md() -> str:
    """Genera la skill TDD adaptada a Vitest/TypeScript para el workspace de implementación."""
    return """---
name: tdd
description: TDD for Vitest + TypeScript: Red-Green-Refactor, AAA, it.each, builders. Trigger: test, tests, TDD.
---

# TDD Skill — Test-Driven Development (Vitest + TypeScript)

No es una guía académica: es el contrato ejecutable que todo test debe cumplir.

---

## 1. Principio fundacional: Red-Green-Refactor

El orden es innegociable. Nunca escribas implementación antes del test.

```
RED      — escribe el test mínimo que falla (aún no existe la implementación)
GREEN    — escribe la implementación mínima que hace pasar el test
REFACTOR — mejora el código sin cambiar comportamiento (test sigue verde)
```

Con IA generativa: tú (el agente) escribes el test. La implementación se genera para
hacerlo pasar. Esto ancla la generación a expectativas concretas y previene alucinaciones.

---

## 2. Estructura AAA (Arrange, Act, Assert)

Todo test sin excepción sigue AAA, delimitado con comentarios `// Arrange`, `// Act`, `// Assert`.

```typescript
import { describe, expect, it } from "vitest";

describe("expenseCalculator.split", () => {
  it("distributes the amount evenly across participants", () => {
    // Arrange
    const calculator = new ExpenseCalculator();

    // Act
    const result = calculator.split(90, 3);

    // Assert
    expect(result).toEqual([30, 30, 30]);
  });

  it("throws when there are no participants", () => {
    // Arrange
    const calculator = new ExpenseCalculator();

    // Act & Assert
    expect(() => calculator.split(90, 0)).toThrow("participants must be greater than zero");
  });
});
```

---

## 3. Naming de tests

Formato: `describe("<subjecto>.<acción>", () => { it("<escenario>") })`.

| Tipo | Patrón | Ejemplo |
|------|--------|---------|
| Happy path | `it("returns <resultado> when <condición>")` | `it("returns the total when items exist")` |
| Error | `it("throws when <condición>")` | `it("throws when the feature is not found")` |
| Edge case | `it("handles <caso borde>")` | `it("handles zero cents without rounding drift")` |

---

## 4. Checklist de calidad (cada test responde SÍ)

1. **¿Prueba lógica o es relleno?** — Fallaría si la lógica se rompe. Si solo sube cobertura, elimínalo.
2. **¿Cubre happy path + error path + un edge case?** — Toda unidad pública tiene mínimo 3 tests.
3. **¿Los asserts son concretos?** — Prohibido `expect(result).toBeTruthy()` como único assert.
4. **¿Usa AAA?** — Las tres secciones están delimitadas y visibles.
5. **¿El nombre describe el escenario?** — Con leerlo sabes qué falló sin abrir el test.
6. **¿Sin mock innecesario?** — Solo se mockean puertos externos (red, DB, clock); la lógica pura se prueba real.

---

## 5. `it.each` (no clones)

Cuando pruebas la misma lógica con distintas entradas, usa `it.each` en vez de copiar el test.

```typescript
it.each([
  [90, 3, [30, 30, 30]],
  [100, 3, [33.34, 33.33, 33.33]], // redondeo
  [0, 2, [0, 0]],
])("split(%i, %i) => %j", (amount, participants, expected) => {
  const calculator = new ExpenseCalculator();
  expect(calculator.split(amount, participants)).toEqual(expected);
});
```

---

## 6. Test Data Builders

Construye los datos con helpers con defaults sensibles; el test solo sobrescribe lo relevante.

```typescript
// tests/factories.ts
export function anExpense(overrides: Partial<Expense> = {}): Expense {
  return { id: "exp_01", amount: 100, currency: "EUR", ...overrides };
}
```

```typescript
const expense = anExpense({ amount: 0 }); // sobrescribe solo lo relevante
```

---

## 7. Test smells prohibidos

| Smell | Síntoma | Corrección |
|-------|---------|------------|
| **Assertion Roulette** | Muchos asserts sin mensaje | Un assert por comportamiento; mensaje en asserts críticos |
| **Mystery Guest** | Depende de estado externo (DB real, red, reloj) | Todo en memoria; usa fake timers si hay fechas |
| **Erratic Test** | A veces pasa, a veces falla | Elimina dependencias de tiempo/red/orden |
| **Conditional Test Logic** | `if`/`for` dentro del test | Test lineal; si necesitas variar, usa `it.each` |
| **Slow Test** | > 200ms en unitarios | Revisa I/O real accidental |
| **Coverage-Driven Test** | Solo existe para tocar una línea | Añade asserts concretos o elimínalo |

---

## 8. Cobertura como side effect

- Cobertura alta es consecuencia de buen testing, no objetivo.
- Nunca escribas un test solo para subir el porcentaje.
- Nunca uses comentarios de exclusión para silenciar código no testeado.

---

## 9. Flujo TDD completo para una feature nueva

1. Lee los requirements de la feature (`get_requirements`) y el AGENTS.md.
2. Escribe el test del happy path (RED — no compila, falta la implementación).
3. Escribe el test del error path (RED).
4. Escribe el test del edge case (RED).
5. Implementa lo mínimo para pasar los 3 tests (GREEN).
6. Refactoriza sin romper verde (REFACTOR).
7. Ejecuta `npx vitest run && npx tsc --noEmit && npx eslint . && npx next build`.
8. Si encontraste un bug que ningún test detecta, escribe el test primero (RED) y luego corrígelo.
"""


def _generate_opencode_json(
    project_id: ProjectId,
    workspace_dir: str,
    mcp_url: str = "http://127.0.0.1:8000/mcp",
) -> str:
    """Genera la configuración de opencode.json para el workspace de implementación."""
    config = {
        "$schema": "https://opencode.ai/config.json",
        "instructions": ["AGENTS.md"],
        "plugin": ["@dietrichgebert/ponytail"],
        "mcp": {
            "kosmo-context": {
                "type": "remote",
                "url": mcp_url,
                "environment": {
                    "KOSMO_PROJECT_ID": str(project_id),
                },
            },
            "token-savior": {
                "type": "local",
                "command": ["uvx", "--from", "token-savior-recall", "token-savior"],
                "environment": {
                    "WORKSPACE_ROOTS": workspace_dir,
                    "TOKEN_SAVIOR_CLIENT": "opencode",
                    "TOKEN_SAVIOR_PROFILE": "optimized",
                },
            },
            "context7": {
                "type": "remote",
                "url": "https://mcp.context7.com/mcp",
            },
        },
        "permission": {
            "read": {"*": "allow"},
            "edit": {
                "src/**": "allow",
                "tests/**": "allow",
                "drizzle/**": "allow",
                "*": "deny",
            },
            "bash": {
                "npm install": "allow",
                "npm run build": "allow",
                "npx tsc --noEmit": "allow",
                "npx vitest run": "allow",
                "npx eslint .": "allow",
                "npx drizzle-kit push": "allow",
                "*": "deny",
            },
        },
    }
    return json.dumps(config, indent=2) + "\n"


class WorkspaceLockedError(RuntimeError):
    """Lanzada cuando se intenta acceder o bloquear un workspace que ya está bloqueado."""


class LocalWorkspaceManager(WorkspaceManagerPort):
    """Adaptador de infraestructura para la gestión de workspaces locales."""

    def __init__(
        self,
        workspaces_root: Path | str,
        workspace_repo: WorkspaceRepository | None = None,
        template_dir: Path | str | None = None,
        git_init: bool = True,
        mcp_url: str = "http://127.0.0.1:8000/mcp",
        project_repo: ProjectRepository | None = None,
    ) -> None:
        self._workspaces_root = Path(workspaces_root)
        self._workspace_repo = workspace_repo
        self._template_dir = Path(template_dir) if template_dir else None
        self._git_init = git_init
        self._mcp_url = mcp_url
        self._project_repo = project_repo
        self._in_memory_locks: set[str] = set()

    @staticmethod
    def _extract_manifest(workspace_path: Path) -> tuple[str, ...]:
        """Extrae el listado de archivos relativos excluyendo directorios ignorados."""
        if not workspace_path.exists():
            return ()

        files: list[str] = []
        for root, dirs, filenames in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in _IGNORED_DIRS]
            rel_root = Path(root).relative_to(workspace_path)
            for fname in filenames:
                if fname in {".DS_Store", "thumbs.db"}:
                    continue
                rel_path = (rel_root / fname).as_posix()
                if rel_path.startswith("./"):
                    rel_path = rel_path[2:]
                files.append(rel_path)

        return tuple(sorted(files))

    async def ensure_workspace(self, project_id: ProjectId) -> CodeWorkspace:
        """Crea el directorio del workspace si no existe (idempotente) y retorna la entidad."""
        target_dir = (self._workspaces_root / str(project_id)).resolve()
        created_new = False

        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            created_new = True

            if self._template_dir and self._template_dir.exists():
                shutil.copytree(self._template_dir, target_dir, dirs_exist_ok=True)

            if self._git_init:
                with contextlib.suppress(Exception):
                    subprocess.run(
                        ["git", "init"],
                        cwd=target_dir,
                        capture_output=True,
                        check=False,
                    )

        # Generar AGENTS.md y opencode.json si no existen
        agents_file = target_dir / "AGENTS.md"
        if not agents_file.exists():
            project_name = str(project_id)
            if self._project_repo:
                with contextlib.suppress(Exception):
                    proj = await self._project_repo.by_id(project_id)
                    if proj and proj.name:
                        project_name = proj.name
            agents_file.write_text(_generate_agents_md(project_name), encoding="utf-8")

        opencode_file = target_dir / "opencode.json"
        if not opencode_file.exists():
            opencode_file.write_text(
                _generate_opencode_json(project_id, str(target_dir), self._mcp_url),
                encoding="utf-8",
            )

        # Generar la skill TDD si no existe
        tdd_skill_file = target_dir / ".opencode" / "skills" / "tdd" / "SKILL.md"
        if not tdd_skill_file.exists():
            tdd_skill_file.parent.mkdir(parents=True, exist_ok=True)
            tdd_skill_file.write_text(_generate_tdd_skill_md(), encoding="utf-8")

        manifest = self._extract_manifest(target_dir)
        now = datetime.now(UTC)

        if self._workspace_repo:
            existing = await self._workspace_repo.by_project_id(project_id)
            if existing is not None and not created_new:
                return dataclasses.replace(existing, manifest_files=manifest)

            ws = CodeWorkspace(
                id=WorkspaceId(f"ws_{project_id}"),
                project_id=project_id,
                status=WorkspaceStatus.READY,
                workspace_dir=str(target_dir),
                manifest_files=manifest,
                current_branch="main",
                is_locked=str(project_id) in self._in_memory_locks,
                created_at=now,
                updated_at=now,
            )
            await self._workspace_repo.save(ws)
            return ws

        return CodeWorkspace(
            id=WorkspaceId(f"ws_{project_id}"),
            project_id=project_id,
            status=WorkspaceStatus.READY,
            workspace_dir=str(target_dir),
            manifest_files=manifest,
            current_branch="main",
            is_locked=str(project_id) in self._in_memory_locks,
            created_at=now,
            updated_at=now,
        )

    async def get_workspace(self, project_id: ProjectId) -> CodeWorkspace | None:
        """Obtiene la información del workspace si existe."""
        if self._workspace_repo:
            ws = await self._workspace_repo.by_project_id(project_id)
            if ws is not None:
                if ws.workspace_dir and Path(ws.workspace_dir).exists():
                    manifest = self._extract_manifest(Path(ws.workspace_dir))
                    return dataclasses.replace(ws, manifest_files=manifest)
                return ws

        target_dir = (self._workspaces_root / str(project_id)).resolve()
        if target_dir.exists():
            manifest = self._extract_manifest(target_dir)
            now = datetime.now(UTC)
            return CodeWorkspace(
                id=WorkspaceId(f"ws_{project_id}"),
                project_id=project_id,
                status=WorkspaceStatus.READY,
                workspace_dir=str(target_dir),
                manifest_files=manifest,
                current_branch="main",
                is_locked=str(project_id) in self._in_memory_locks,
                created_at=now,
                updated_at=now,
            )

        return None

    async def get_manifest(self, workspace: CodeWorkspace) -> tuple[str, ...]:
        """Retorna el manifiesto de archivos actual del workspace."""
        if not workspace.workspace_dir:
            return ()
        return self._extract_manifest(Path(workspace.workspace_dir))

    async def is_locked(self, project_id: ProjectId) -> bool:
        """Verifica si el workspace está bloqueado."""
        if self._workspace_repo:
            ws = await self._workspace_repo.by_project_id(project_id)
            if ws is not None and ws.is_locked:
                return True
        return str(project_id) in self._in_memory_locks

    async def acquire_lock(self, project_id: ProjectId) -> None:
        """Adquiere el bloqueo para un proyecto o lanza WorkspaceLockedError."""
        if await self.is_locked(project_id):
            raise WorkspaceLockedError(f"Workspace for project '{project_id}' is currently locked by another process.")
        self._in_memory_locks.add(str(project_id))
        if self._workspace_repo:
            await self._workspace_repo.update_lock(project_id, is_locked=True)

    async def release_lock(self, project_id: ProjectId) -> None:
        """Libera el bloqueo para un proyecto."""
        self._in_memory_locks.discard(str(project_id))
        if self._workspace_repo:
            await self._workspace_repo.release_lock(project_id)
