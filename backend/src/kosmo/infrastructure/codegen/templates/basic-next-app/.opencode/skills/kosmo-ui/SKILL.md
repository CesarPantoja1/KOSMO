---
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
