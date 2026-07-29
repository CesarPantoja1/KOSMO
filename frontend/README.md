# Arquitectura Frontend — Feature-Sliced Design (FSD)

Este documento define las reglas arquitectónicas del proyecto, basadas en **Feature-Sliced Design (FSD)**.

---

## Estructura jerárquica

```
Layer → Slice → Segment
```

- **Layer** — Nivel arquitectónico (`app`, `pages`, `widgets`, `features`, `entities`, `shared`)
- **Slice** — Unidad de dominio o funcionalidad dentro de la capa
- **Segment** — Tipo de responsabilidad técnica (`ui/`, `model/`, `api/`, `lib/`)

---

## Capas y sus reglas

### `app/`

Configuración global de la aplicación. No se crean slices aquí.

- `providers/` — Contextos globales (Auth, Theme, MSW)
- `store/` — Store global de la app
- `globals.css` — Estilos globales y **paleta de colores del proyecto**

> La paleta de colores está definida en `app/globals.css` mediante tokens CSS de Tailwind v4 (`@theme`). Siempre usar estos tokens en lugar de valores hardcodeados.
>
> Tokens disponibles: `--color-base-{50|100|200|300|600|800|950}`, `--color-primary-{50|100|800}`, `--color-ai`, `--color-status-{success|warning|error|info}`, `--color-light-yellow`.

---

### `src/entities/`

Representa los tipos de datos principales del dominio. Contiene los datos, su forma y cómo se obtienen.

**Segmentos permitidos:**

- `model/` — Tipos TypeScript y store Zustand de la entidad
- `api/` — Endpoints y llamadas HTTP específicas de la entidad

**Prohibido:**

- `ui/` — Las entidades no exponen componentes visuales

---

### `src/pages/`

Cada slice corresponde a una página de la aplicación. Compone widgets y features para construir la vista final.

**Segmentos permitidos (solo si son necesarios):**

- `ui/` — Componentes y layout propios de la página
- `model/` — Lógica, hooks y estado específico de la página

> No crear `model/` ni `ui/` si la página no los necesita.

---

### `src/feature/`

Acciones que el usuario puede realizar. Los componentes de esta capa son **agnósticos a la API** — no saben de dónde vienen los datos, solo los reciben via props o store.

**Segmentos permitidos:**

- `ui/` — Componentes de acción (formularios, botones de acción, editores)
- `model/` — Estado y lógica local de la feature
- `lib/` — Utilidades internas de la feature

**Prohibido:**

- `api/` — Las features no hacen llamadas HTTP directamente

---

### `src/widgets/`

Bloques UI complejos que componen múltiples entidades y features en una unidad visual cohesiva (navbars, paneles, wizards).

- `ui/` — Composición visual del widget
- `model/` — Coordinación de estados entre slices
- `lib/` — Utilidades internas del widget
- `types/` — Tipos propios del widget

---

### `src/shared/`

Código transversal sin lógica de negocio. Puede ser importado por cualquier capa.

- `ui/` — Componentes atómicos reutilizables (Button, Loading, Toast, iconos)
- `lib/` — Utilidades genéricas (PKCE, Zod helpers)
- `api/` — Configuración del cliente HTTP y helpers de autenticación
- `store/` — Store global de autenticación
- `mocks/` — Configuración de MSW para tests y desarrollo

---

## Reglas de importación

Las capas solo pueden importar de capas inferiores:

```
pages → widgets → features → entities → shared
```

- `pages` puede importar de `widgets`, `features`, `entities`, `shared`
- `widgets` puede importar de `features`, `entities`, `shared`
- `features` puede importar de `entities`, `shared`
- `entities` puede importar de `shared`
- `shared` no importa de ninguna capa del proyecto

---

## Convenciones de código

### Naming

- **Componentes** → `PascalCase` (`UserCard.tsx`)
- **Archivos utilitarios / hooks** → `kebab-case` (`use-local-storage.ts`)
- **Variables y funciones** → `camelCase`
- **Constantes** → `UPPER_SNAKE_CASE`

### TypeScript

- Tipado estricto habilitado; evitar `any` (usar `unknown` o genéricos)
- `interface` para objetos y props
- `type` para uniones y tipos complejos

### Componentes

- Arrow functions con exportación nombrada (excepto `page.tsx`)
- Desestructuración de props y uso de early returns

```ts
export const MyComponent = ({ title }: Props) => {
  if (!title) return null
  return <h1>{title}</h1>
}
```

### Next.js (App Router)

- `'use client'` solo cuando sea estrictamente necesario
- Preferir Server Components para fetching de datos
- Los archivos de ruta (`page.tsx`, `layout.tsx`) van en `app/`; la lógica va en `src/pages/`

### Estilos

- Tailwind CSS para todos los estilos; sin inline styles
- Usar los tokens de `globals.css` para colores, espaciado y radios

### Manejo de estado

- **URL** → Estado compartible entre vistas
- **`useState`** → Estado local del componente
- **Zustand** → Estado global (último recurso; preferir estado local o de URL)

### Documentación

- JSDoc en funciones complejas
- Comentarios explican el **por qué**, no el qué


This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## PARA COMENZAR

Primero, ejecutar el servidor de desarrollo:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev (este proyecto)
```

Abrir [http://localhost:3000](http://localhost:3000) en el navegador de su preferencia.
