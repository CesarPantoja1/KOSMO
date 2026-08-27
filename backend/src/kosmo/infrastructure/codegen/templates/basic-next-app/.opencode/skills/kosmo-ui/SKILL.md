---
name: kosmo-ui
description: UI funcional y consistente con Bootstrap 5. Modelo mental, UX contextual y desacople. Trigger: UI, diseño, navegación, bootstrap.
---

# UI, Navegación y Diseño con Bootstrap 5 en KOSMO

Esta skill define el contrato de diseño que toda feature implementada debe cumplir.
El stack frontend se basa en **100% Bootstrap 5** y el Design System propio (`src/components/ui/`).
**PROHIBIDO el uso de Tailwind CSS.**

---

## 1. Regla de oro: toda feature entrega una pantalla funcional

Una feature NO está implementada si solo existe su lógica. Toda feature debe entregar:

1. **Ruta visible**: `src/app/<slug>/page.tsx` (Server Component que renderiza el componente principal de la feature).
2. **Slice autocontenido** en `src/features/<slug>/`:
   - `manifest.ts` — `{ slug, title, description, route, icon }` (icono de `lucide-react`).
   - `logic.ts` — lógica de negocio pura, tipada, sin I/O ni React.
   - `components/` — componentes de la UI de la feature (usando Bootstrap y `src/components/ui/`).
   - `index.ts` — exports públicos del slice.
3. **Registro de navegación**: importar el manifest en `src/lib/feature-registry.ts`.
4. **Tests** de la lógica en Vitest (`tests/` o dentro del slice).

**Desacople absoluto**: el shell (`layout`, `app-shell`, home) y las demás features NO pueden importar
nada del interior de otro slice. Eliminar una feature = borrar `src/features/<slug>/` + su import
en el registro. Nada más.

---

## 2. Mapa navegacional y UX Contextual

- **Shell adaptativo**: `AppShell` (`src/components/layout/app-shell.tsx`) maneja automáticamente la navegación según el arquetipo:
  - `dashboard` o `workflow` → Sidebar de navegación lateral persistente (`sidebar.tsx`).
  - `storefront` o `saas_tool` → Top navbar sticky (`navbar.tsx`).
- **Persistencia del contexto**: el usuario siempre sabe dónde está (link activo, `PageHeader` consistente).
- **Estados completos**: cada pantalla define estado vacío (`EmptyState`), estado de carga y estado de error con mensajes reales en español neutro.
- **Jerarquía visual**: máximo una acción primaria (`variant="primary"`) por pantalla; acciones secundarias como `outline` o `light`.

---

## 3. Catálogo del Design System (`src/components/ui/`)

Usa **EXCLUSIVAMENTE** los componentes del design system y clases estándar de Bootstrap:

| Componente | Caso de uso principal |
|---|---|
| `Button` | Acciones (`variant="primary" | "secondary" | "outline" | "outline-secondary" | "danger" | "light"`) |
| `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardBody`, `CardFooter` | Contenedores estructurados de información |
| `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell` | Tablas de datos responsivas y legibles |
| `Stat` | Métricas clave, KPIs y balances con variación |
| `Badge` | Etiquetas semánticas (`tone="neutral" | "success" | "warning" | "danger" | "primary" | "info"`) |
| `BadgeStatus` | Estados del ciclo de vida del negocio (`status="pending" | "in_progress" | "completed" | "active" | "rejected"`) |
| `Input`, `Select`, `Label`, `Textarea` | Formularios accesibles con soporte de validación (`isInvalid`) |
| `Modal` | Diálogos de confirmación o captura focalizada |
| `Tabs` | Vistas alternativas y pestañas (`variant="tabs" | "pills"`) |
| `Alert` | Mensajes de feedback inline (`variant="info" | "success" | "warning" | "danger"`) |
| `Steps` | Indicador de progreso multi-etapa |
| `EmptyState` | Mensaje cuando no hay registros |
| `PageHeader` | Encabezado estándar con título, descripción y botones de acción |

---

## 4. Bootstrap 5: Grid y Utilidades

- **Grid Responsive**: usa `container`, `container-fluid`, `row`, `col-12`, `col-md-6`, `col-lg-4`, etc.
- **Espaciado y Layout**: `d-flex`, `flex-column`, `align-items-center`, `justify-content-between`, `gap-2`, `gap-3`, `mb-3`, `p-3`.
- **Tipografía y Colores**: `text-dark`, `text-secondary`, `text-muted`, `fw-bold`, `fw-semibold`, `small`.
- **Prohibido**: No inventes estilos CSS inline `style={{...}}` para lo que Bootstrap y el Design System resuelven.

---

## 5. Anti-"AI Slop": Reglas de Calidad

- **Cero Dashboards con cards repetidas**: En arquetipos Dashboard, usa `Table` con filtros y `Stat` para KPIs.
- **Textos Reales**: Textos en español neutro específicos del negocio del usuario. Prohibido "Lorem Ipsum" y "Bienvenido a nuestra plataforma".
- **Formularios Honestos**: Labels visibles, feedback de validación claro que refleje las reglas de `logic.ts`.

---

## 6. Checklist antes de dar una feature por terminada

- [ ] Existe `src/app/<slug>/page.tsx` renderizando el componente principal.
- [ ] El slice `src/features/<slug>/` contiene manifest + logic + components.
- [ ] El manifest está registrado en `feature-registry.ts` y aparece en el shell.
- [ ] Usa componentes de `src/components/ui/` y clases de Bootstrap 5.
- [ ] Cero dependencias o clases de Tailwind CSS.
- [ ] `tsc --noEmit`, `eslint .`, `vitest run` y `next build` pasan.

