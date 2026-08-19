from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import json
import os
import shutil
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
from kosmo.infrastructure.git import (
    git_add,
    git_commit,
    git_init,
    git_rollback,
)

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

DEFAULT_TEMPLATE_DIR: Path = Path(__file__).parent / "templates" / "basic-next-app"


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

## Skills disponibles (Cargar antes de codificar)
- `.opencode/skills/kosmo-implementation/SKILL.md`: Clean Architecture y TypeScript.
- `.opencode/skills/kosmo-testing/SKILL.md` (o `tdd`): TDD Vitest, patrón AAA y cobertura obligatoria.
- `.opencode/skills/kosmo-drizzle/SKILL.md`: Drizzle ORM sobre SQLite, tipado de esquemas y queries.
- `.opencode/skills/kosmo-nextjs/SKILL.md`: Next.js 16 App Router con Server Components y APIs.
- `.opencode/skills/kosmo-ui/SKILL.md`: UI funcional, mapa navegacional y diseño consistente.

## UI, Navegación y Diseño (NON-NEGOTIABLE)
Toda feature termina con una pantalla funcional que el usuario puede abrir y usar.

1. **Ruta y slice**: `src/app/<slug>/page.tsx` + `src/features/<slug>/` con `manifest.ts`,
   `logic.ts` y `components/`. Registrar el manifest en `src/lib/feature-registry.ts`
   (la navegación del shell se deriva del registro).
2. **Desacople**: los slices no se importan entre sí; borrar una feature = eliminar su
   carpeta y su entrada en el registro. El shell no depende de ninguna feature.
3. **Modelo mental**: nav persistente con la feature activa, home con la visión del proyecto
   y tarjetas de acceso, estados vacío/error/loading claros, español neutro.
4. **Adaptación al tipo de web**: detecta la naturaleza del negocio desde la visión del
   descubrimiento (storefront, dashboard, contenido o app de negocio) y adapta el shell.
5. **Diseño consistente**: solo componentes de `src/components/ui/` y tokens del tema;
   nada de estilos sueltos, degradados genéricos, emojis o lorem ipsum.

## TDD (obligatorio)
Antes de escribir cualquier test, carga la skill `.opencode/skills/tdd/SKILL.md` (o `kosmo-testing`).
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


def _generate_implementation_skill_md() -> str:
    """Genera la skill kosmo-implementation para el workspace de implementación."""
    return """---
name: kosmo-implementation
description: Directrices de Clean Architecture y TypeScript para KOSMO. Trigger: architecture, implement, clean.
---

# Clean Architecture & Implementación en KOSMO

Esta skill define las reglas de diseño arquitectónico y de código que el agente debe seguir obligatoriamente.

---

## 1. Principios Fundacionales de Clean Architecture

El proyecto organiza el código en capas concéntricas con regla de dependencia unidireccional:
**el código de negocio nunca depende de detalles de infraestructura o frameworks**.

```
┌────────────────────────────────────────────────────────┐
│  Presentación & UI (src/app/, src/components/)        │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Lógica de Negocio / Dominio (src/lib/, services)│  │
│  │  ┌────────────────────────────────────────────┐  │  │
│  │  │  Acceso a Datos & ORM (src/db/)            │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

1. **Dominio / Lógica Pura (`src/lib/`, `src/services/`)**:
   - Funciones puras, cálculo de reglas de negocio, validaciones y transformaciones de datos.
   - Sin dependencias de Next.js, React ni hooks de cliente.
   - Diseñado para ser probado de forma 100% aislada con Vitest en memoria.

2. **Acceso a Datos / Infraestructura (`src/db/`)**:
   - Definición de esquemas Drizzle ORM (`src/db/schema.ts`) e inicialización (`src/db/index.ts`).
   - Consultas SQL tipadas encapsuladas en funciones auxiliares o repositorios.
   - Nunca expone SQL crudo a las capas superiores.

3. **Presentación & Rutas (`src/app/`, `src/components/`)**:
   - Server Components por defecto para obtener datos directamente.
   - Client Components (`'use client'`) únicamente en hojas interactivas.
   - Componentes modulares con responsabilidad única en `src/components/`.

---

## 2. Convenciones de TypeScript Estricto

1. **Cero `any`:** Prohibido el uso de `any`. Usa `unknown`, `never`, genéricos o interfaces tipadas.
2. **Inmutabilidad:** Prefiere `readonly`, `const` y spread `...` sobre mutaciones directas.
3. **Manejo de Errores con Tipos:** Usa excepciones tipadas o tipos de resultado estructurados.
4. **Nomenclatura:** Código e identificadores en inglés; textos y etiquetas de UI en español.

---

## 3. Anti-patrones Prohibidos para el Agente (LLM Guardrails)

| Anti-patrón | Por qué está prohibido | Solución requerida |
|-------------|------------------------|-------------------|
| **Lógica en UI** | Rompe la testabilidad y mezcla presentación con negocio | Extraer a funciones puras en `src/lib/` |
| **SQL en Cliente** | Inseguro y no compila en el cliente | Mover consultas a Server Components / APIs |
| **Monolito en `page.tsx`** | Dificulta mantenimiento y testing | Dividir en subcomponentes en `src/components/` |
| **Mutaciones Globales** | Provoca efectos secundarios no deterministas | Funciones puras que retornan nuevos estados |
| **Silenciar tipos (`@ts-ignore`)** | Oculta bugs críticos | Corregir tipos hasta que `tsc --noEmit` pase |

---

## 4. Checklist de Calidad para el Agente

Antes de dar una característica por implementada, verifica:
- [ ] La lógica pura está separada de los componentes React.
- [ ] No existen tipos `any` ni directivas `@ts-ignore`.
- [ ] Cada función exportada cuenta con tests unitarios en `tests/`.
- [ ] Las consultas de base de datos usan Drizzle ORM con tipado estricto.
- [ ] El pipeline de validación (`tsc`, `eslint`, `vitest`, `build`) pasa al 100%.
"""


def _generate_testing_skill_md() -> str:
    """Genera la skill kosmo-testing (TDD con Vitest) para el workspace de implementación."""
    return """---
name: kosmo-testing
description: Metodología TDD con Vitest, patrón AAA y cobertura obligatoria. Trigger: test, tests, vitest, TDD.
---

# Testing & TDD con Vitest en KOSMO

Esta skill define el contrato ejecutable de pruebas unitarias y de integración que todo código generado debe cumplir.

---

## 1. Principio Fundacional: Red-Green-Refactor

El orden es innegociable. Nunca generes código de implementación sin su prueba correspondiente:

```
1. RED      — Escribe el test que falla (comportamiento esperado).
2. GREEN    — Escribe la implementación mínima para hacer pasar el test.
3. REFACTOR — Limpia y optimiza manteniendo el test en verde.
```

---

## 2. Estructura AAA Obligatoria (Arrange, Act, Assert)
 
Todo test unitario debe estar delimitado con comentarios `// Arrange`, `// Act`, `// Assert`:

```typescript
import { describe, expect, it } from "vitest";
import { calculateDiscount } from "@/lib/discount";

describe("calculateDiscount", () => {
  it("applies 10 percent discount for premium members", () => {
    // Arrange
    const amount = 100;
    const isPremium = true;

    // Act
    const result = calculateDiscount(amount, isPremium);

    // Assert
    expect(result).toBe(90);
  });

  it("throws ValidationError when amount is negative", () => {
    // Arrange
    const negativeAmount = -50;

    // Act & Assert
    expect(() => calculateDiscount(negativeAmount, false)).toThrow("Amount cannot be negative");
  });
});
```

---

## 3. Regla Innegociable de Cobertura de Casos

Para cada función, método o ruta pública, es **obligatorio** escribir como mínimo:
1. **Happy Path (Camino Feliz)**: Caso estándar con entradas válidas donde todo funciona correctamente.
2. **Error Path (Camino de Error)**: Entradas inválidas, valores fuera de rango o excepciones esperadas.
3. **Edge Case (Caso Borde)**: Valores cero, arrays vacíos, strings vacíos o límites numéricos.

---

## 4. Pruebas Parametrizadas con `it.each`

Cuando pruebes la misma lógica con diferentes combinaciones de datos, usa `it.each` para evitar duplicación:

```typescript
it.each([
  [100, true, 90],
  [100, false, 100],
  [0, true, 0],
])("calculateDiscount(%i, %s) => %i", (amount, isPremium, expected) => {
  // Arrange & Act
  const result = calculateDiscount(amount, isPremium);

  // Assert
  expect(result).toBe(expected);
});
```

---

## 5. Test Data Builders / Factories

Crea helpers de datos en `tests/factories.ts` para mantener los tests concisos y legibles:

```typescript
export function aUser(overrides: Partial<User> = {}): User {
  return {
    id: "usr_01",
    name: "Juan Pérez",
    email: "juan@example.com",
    role: "member",
    createdAt: new Date("2026-01-01"),
    ...overrides,
  };
}
```

---

## 6. Anti-patrones de Testing Prohibidos

| Anti-patrón | Síntoma | Corrección |
|-------------|---------|------------|
| **Assertion Roulette** | Múltiples asertos sin claridad | Un aserto por comportamiento |
| **Test de Relleno** | `expect(true).toBe(true)` de relleno | Probar comportamiento real y asertos calculados |
| **Mystery Guest** | Dependencia de red o DB real | Todo en memoria o con SQLite local aislado |
| **Sin Caso de Error** | Solo probar entradas correctas | Escribir tests explícitos para errores |
"""


def _generate_tdd_skill_md() -> str:
    """Mantiene compatibilidad con alias tdd."""
    return _generate_testing_skill_md()


def _generate_drizzle_skill_md() -> str:
    """Genera la skill kosmo-drizzle para modelado y consultas con Drizzle ORM sobre SQLite."""
    return """---
name: kosmo-drizzle
description: Persistencia con Drizzle ORM sobre SQLite, tipado estricto y queries seguras. Trigger: drizzle, db, sqlite.
---

# Drizzle ORM & Persistencia SQLite en KOSMO

Esta skill define directrices para modelar esquemas y consultas tipadas con Drizzle ORM y SQLite (`better-sqlite3`).

---

## 1. Definición de Esquemas Tipados (`src/db/schema.ts`)

Todos los esquemas de base de datos se declaran en `src/db/schema.ts` usando `drizzle-orm/sqlite-core`:

```typescript
import { sqliteTable, text, integer, real } from "drizzle-orm/sqlite-core";

export const expenses = sqliteTable("expenses", {
  id: text("id").primaryKey(),
  description: text("description").notNull(),
  amount: real("amount").notNull(),
  category: text("category").notNull().default("general"),
  userId: text("user_id").notNull(),
  createdAt: integer("created_at", { mode: "timestamp" })
    .notNull()
    .$defaultFn(() => new Date()),
});

// Tipos inferidos automáticos para inserción y lectura
export type Expense = typeof expenses.$inferSelect;
export type NewExpense = typeof expenses.$inferInsert;
```

---

## 2. Consultas Tipadas con el Query Builder

Toda operación de lectura o escritura debe usar la instancia `db` tipada de `src/db/index.ts`.

### Inserción
```typescript
import { db } from "@/db";
import { expenses, type NewExpense, type Expense } from "@/db/schema";

export async function createExpense(data: NewExpense): Promise<Expense> {
  const [created] = await db.insert(expenses).values(data).returning();
  return created;
}
```

### Consultas con Filtros (`eq`, `and`, `gte`, etc.)
```typescript
import { eq, desc } from "drizzle-orm";
import { db } from "@/db";
import { expenses, type Expense } from "@/db/schema";

export async function getExpensesByUser(userId: string): Promise<Expense[]> {
  return db
    .select()
    .from(expenses)
    .where(eq(expenses.userId, userId))
    .orderBy(desc(expenses.createdAt));
}
```

### Actualización y Eliminación
```typescript
export async function updateExpenseAmount(id: string, newAmount: number): Promise<void> {
  await db
    .update(expenses)
    .set({ amount: newAmount })
    .where(eq(expenses.id, id));
}

export async function deleteExpense(id: string): Promise<void> {
  await db.delete(expenses).where(eq(expenses.id, id));
}
```

---

## 3. Reglas Innegociables de Persistencia

1. **Cero SQL Crudo (Raw SQL):** Prohibido el uso de `db.run(sql"...")` o consultas de texto concatenadas.
2. **Tipos Exportados:** Siempre exporta los tipos inferidos `$inferSelect` y `$inferInsert` de la tabla.
3. **Claves Primarias y Fechas:** Usa identificadores unívocos y marcas de tiempo estándar.
4. **Relaciones Explícitas:** Usa `references(() => otherTable.id)` en claves foráneas.

---

## 4. Anti-patrones de Base de Datos

| Anti-patrón | Riesgo | Solución |
|-------------|--------|----------|
| **Tipos desincronizados** | Errores esquema-código | Usar `typeof table.$inferSelect` y `$inferInsert` |
| **SQL sin tipar** | Inyecciones SQL y runtime bugs | Usar operadores `eq`, `like`, `and` de Drizzle |
| **Conexiones duplicadas** | Bloqueos y memory leaks | Importar el singleton `db` desde `@/db` |
"""


def _generate_nextjs_skill_md() -> str:
    """Genera la skill kosmo-nextjs para App Router, React 19 y Server Components."""
    return """---
name: kosmo-nextjs
description: Convenciones de Next.js 16 App Router, React 19 y Server Components. Trigger: nextjs, react, api route.
---

# Next.js 16 App Router & React 19 en KOSMO

Esta skill define directrices para páginas, layouts, componentes interactivos y rutas de API en Next.js 16.

---

## 1. Server Components por Defecto

En Next.js 16 App Router, todos los componentes en `src/app/` son **Server Components** por defecto.

```tsx
// src/app/expenses/page.tsx (Server Component)
import { getExpensesByUser } from "@/db/queries/expenses";
import { ExpenseList } from "@/components/ExpenseList";

export default async function ExpensesPage() {
  // Obtención directa de datos en el servidor
  const expenses = await getExpensesByUser("usr_01");

  return (
    <main className="container mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Registro de Gastos</h1>
      <ExpenseList initialExpenses={expenses} />
    </main>
  );
}
```

---

## 2. Uso Restrictivo de `'use client'`

Solo se agrega `'use client'` en componentes de hoja pequeños en `src/components/` que requieran:
- Manejo de estado de cliente (`useState`, `useReducer`).
- Efectos y ciclo de vida del navegador (`useEffect`).
- Eventos de interacción del DOM (`onClick`, `onChange`, `onSubmit`).

```tsx
// src/components/ExpenseFilter.tsx (Client Component)
"use client";

import { useState } from "react";

interface ExpenseFilterProps {
  onFilterChange: (category: string) => void;
}

export function ExpenseFilter({ onFilterChange }: ExpenseFilterProps) {
  const [selected, setSelected] = useState("all");

  const handleChange = (cat: string) => {
    setSelected(cat);
    onFilterChange(cat);
  };

  return (
    <div className="flex gap-2">
      <button
        type="button"
        onClick={() => handleChange("all")}
        className={selected === "all" ? "bg-primary text-white px-3 py-1 rounded" : "px-3 py-1"}
      >
        Todos
      </button>
    </div>
  );
}
```

---

## 3. Rutas de API Estructuradas (`src/app/api/.../route.ts`)

Las rutas de API deben retornar `NextResponse.json` con códigos HTTP estándar y formato estructurado:

```typescript
// src/app/api/expenses/route.ts
import { NextResponse } from "next/server";
import { getExpensesByUser, createExpense } from "@/db/queries/expenses";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const userId = searchParams.get("userId");

  if (!userId) {
    return NextResponse.json(
      { error: "Bad Request", detail: "El parámetro userId es obligatorio." },
      { status: 400 }
    );
  }

  const items = await getExpensesByUser(userId);
  return NextResponse.json({ data: items }, { status: 200 });
}
```

---

## 4. Estilos y Utilidades Tailwind CSS

1. Usa clases utilitarias de Tailwind CSS v4.
2. Para composición condicional de clases, usa `cn()` desde `@/lib/utils`:
   ```tsx
   import { cn } from "@/lib/utils";

   export function Badge({ variant, className, children }: BadgeProps) {
     return (
       <span
         className={cn(
           "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
           variant === "success" && "bg-green-100 text-green-800",
           variant === "error" && "bg-red-100 text-red-800",
           className
         )}
       >
         {children}
       </span>
     );
   }
   ```

---

## 5. Anti-patrones de Next.js Prohibidos

| Anti-patrón | Consecuencia | Corrección |
|-------------|--------------|------------|
| **`'use client'` en páginas** | Deshabilita Server-Side Rendering | Extraer componentes interactivos |
| **`fetch()` a APIs propias en Server** | Overhead de red HTTP | Llamar directamente al servicio o DB |
| **Errores con strings sueltos** | Dificulta parseo en cliente | Retornar JSON `{ error, detail }` estructurado |
"""


def _generate_ui_skill_md() -> str:
    """Genera la skill kosmo-ui: UI funcional, navegación y diseño consistente."""
    return """---
name: kosmo-ui
description: UI funcional y consistente. Modelo mental, mapa navegacional y desacople. Trigger: UI, diseño, navegación.
---

# UI, Navegación y Diseño en KOSMO

Esta skill define el contrato de diseño que toda feature implementada debe cumplir.
La aplicación no es código muerto: es una web funcional que un ciudadano usa desde el primer clic.

---

## 1. Regla de oro: toda feature entrega una pantalla funcional

Una feature NO está implementada si solo existe su lógica. Toda feature debe entregar:

1. **Ruta visible**: `src/app/<slug>/page.tsx` (Server Component que renderiza el componente principal de la feature).
2. **Slice autocontenido** en `src/features/<slug>/`:
   - `manifest.ts` — `{ slug, title, description, route, icon }` (icono de `lucide-react`).
   - `logic.ts` — lógica de negocio pura, tipada, sin I/O ni React.
   - `components/` — componentes de la UI de la feature.
   - `index.ts` — exports públicos del slice.
3. **Registro de navegación**: importar el manifest en `src/lib/feature-registry.ts`.
4. **Tests** de la lógica (`tests/` o dentro del slice).

**Desacople absoluto**: el shell (`layout`, navbar, home) y las demás features NO pueden importar
nada del interior de otro slice. Eliminar una feature = borrar `src/features/<slug>/` + su import
en el registro. Nada más.

---

## 2. Mapa navegacional y modelo mental del usuario

- La **navegación principal** se deriva del registro de features (navbar). Cada feature nueva
  aparece sola en el menú: no hay que tocar el shell.
- La **home** presenta la visión del proyecto y tarjetas hacia cada feature. Mantén ese patrón.
- **Persistencia del contexto**: el usuario siempre sabe dónde está (link activo en navbar,
  títulos de página consistentes).
- **Estados completos**: cada pantalla define estado vacío, estado de carga y estado de error,
  con mensajes claros en español neutro.
- **Jerarquía visual**: una acción primaria por pantalla; las secundarias como outline/ghost.

## 3. Arquetipos de web (la UI se adapta a la naturaleza del negocio)

Lee el contexto del proyecto (nombre, descripción y visión del descubrimiento) y determina el
arquetipo ANTES de diseñar:

| Arquetipo | Señales | Patrón de shell |
|---|---|---|
| **Storefront** | venta, inventario, precios | Top-nav + home con propuesta de valor |
| **Dashboard** | métricas, CRUDs, reportes | Sidebar de navegación + contenido |
| **Contenido** | blog, docs, institucional | Top-nav simple + secciones |
| **SaaS / negocio** | flujos, formularios, cuentas | Top-nav + rutas por feature |

El template trae un shell neutro (top-nav). Adáptalo al arquetipo sin romper el registro:
para dashboard, convierte la nav en sidebar (misma lista del registro).

## 4. No parecer hecho con IA

- **Solo design system**: componentes de `src/components/ui/` (Button, Card, Input, Label,
  Badge, Textarea, EmptyState, PageHeader) y tokens del tema. Prohibido estilos sueltos,
  degradados llamativos, sombras excesivas, emojis o colores aleatorios.
- **Contenido real**: textos en español neutro específicos del negocio. Prohibido lorem ipsum
  y textos genéricos tipo "bienvenido a nuestra plataforma".
- **Formularios honestos**: labels visibles, validación que muestra los mensajes exactos de
  `logic.ts`, feedback de éxito y error tras cada acción.
- **Consistencia**: mismas medidas de espaciado, radios y pesos tipográficos en toda la app.
- **Iconos**: usa `lucide-react` para acciones y estados; sin iconos decorativos sin propósito.

## 5. TDD aplicado a la UI

- La lógica (`logic.ts`) se escribe primero con tests (Red-Green-Refactor) y sin dependencias de React.
- Los componentes son delgados: renderizan estado y llaman a la lógica pura.
- No se testean componentes visuales a menos que la lógica interactiva lo justifique.

## 6. Checklist antes de dar una feature por terminada

- [ ] Existe `src/app/<slug>/page.tsx` renderizando el componente principal.
- [ ] El slice `src/features/<slug>/` contiene manifest + logic + components.
- [ ] El manifest está registrado en `feature-registry.ts` y aparece en la navbar.
- [ ] La pantalla tiene estados vacío/error y muestra mensajes de validación reales.
- [ ] Solo usa componentes de `src/components/ui/` y tokens del tema.
- [ ] Textos en español neutro, específicos del negocio.
- [ ] `tsc --noEmit`, `eslint`, `vitest` y `next build` pasan.
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
            "edit": {"*": "allow"},
            "bash": {"*": "allow"},
        },
        # Flujo headless: el agente no debe bloquearse pidiendo aclaraciones al usuario
        "tools": {
            "question": False,
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
        self._template_dir = Path(template_dir) if template_dir is not None else DEFAULT_TEMPLATE_DIR
        self._git_init = git_init
        self._mcp_url = mcp_url
        self._project_repo = project_repo
        self._in_memory_locks: set[str] = set()
        # ponytail: guard global del proceso; la carrera multi-worker se cierra con el
        # CAS (UPDATE condicional) de update_lock en el repositorio SQL.
        self._lock_guard = asyncio.Lock()

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
                    git_init(target_dir)

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

        # Generar las skills en .opencode/skills si no existen
        skills_dir = target_dir / ".opencode" / "skills"
        skills_map = {
            "kosmo-implementation": _generate_implementation_skill_md(),
            "kosmo-testing": _generate_testing_skill_md(),
            "kosmo-drizzle": _generate_drizzle_skill_md(),
            "kosmo-nextjs": _generate_nextjs_skill_md(),
            "kosmo-ui": _generate_ui_skill_md(),
            "tdd": _generate_tdd_skill_md(),
        }
        for skill_name, skill_content in skills_map.items():
            skill_file = skills_dir / skill_name / "SKILL.md"
            if not skill_file.exists():
                skill_file.parent.mkdir(parents=True, exist_ok=True)
                skill_file.write_text(skill_content, encoding="utf-8")

        if self._git_init and created_new:
            with contextlib.suppress(Exception):
                git_add(target_dir)
                git_commit(target_dir, "chore: initialize workspace template and configurations")

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
        async with self._lock_guard:
            if str(project_id) in self._in_memory_locks:
                raise WorkspaceLockedError(
                    f"Workspace for project '{project_id}' is currently locked by another process."
                )
            if self._workspace_repo:
                updated = await self._workspace_repo.update_lock(project_id, is_locked=True)
                if updated is None:
                    # El CAS/INSERT de la DB decidió que otro proceso tiene el lock
                    raise WorkspaceLockedError(
                        f"Workspace for project '{project_id}' is currently locked by another process."
                    )
            self._in_memory_locks.add(str(project_id))

    async def release_lock(self, project_id: ProjectId) -> None:
        """Libera el bloqueo para un proyecto."""
        async with self._lock_guard:
            self._in_memory_locks.discard(str(project_id))
            if self._workspace_repo:
                await self._workspace_repo.release_lock(project_id)

    async def rollback_workspace(self, project_id: ProjectId) -> None:
        """Revierte el workspace al último commit exitoso y limpia archivos no rastreados."""
        target_dir = (self._workspaces_root / str(project_id)).resolve()
        if not target_dir.exists():
            return

        git_rollback(target_dir)

        manifest = self._extract_manifest(target_dir)
        if self._workspace_repo:
            ws = await self._workspace_repo.by_project_id(project_id)
            if ws is not None:
                updated = dataclasses.replace(ws, manifest_files=manifest, updated_at=datetime.now(UTC))
                await self._workspace_repo.save(updated)

    async def commit_workspace(self, project_id: ProjectId, message: str) -> bool:
        """Consolida los cambios del workspace en un commit de git y actualiza el manifiesto."""
        target_dir = (self._workspaces_root / str(project_id)).resolve()
        if not target_dir.exists():
            return False

        git_add(target_dir)
        committed = git_commit(target_dir, message)

        manifest = self._extract_manifest(target_dir)
        if self._workspace_repo:
            ws = await self._workspace_repo.by_project_id(project_id)
            if ws is not None:
                updated = dataclasses.replace(ws, manifest_files=manifest, updated_at=datetime.now(UTC))
                await self._workspace_repo.save(updated)

        return committed

    async def publish_preview(self, project_id: ProjectId) -> None:
        """Escribe el puntero del workspace a previsualizar (leído por el servicio preview)."""
        target_dir = (self._workspaces_root / str(project_id)).resolve()
        (self._workspaces_root / ".preview").write_text(str(target_dir), encoding="utf-8")
