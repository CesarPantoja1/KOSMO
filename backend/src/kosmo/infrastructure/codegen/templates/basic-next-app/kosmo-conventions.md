# Convenciones de Desarrollo — Proyecto Generado KOSMO

Este documento define las reglas de diseño, arquitectura y calidad para todo código generado en este proyecto.

## 1. Stack Tecnológico
- **Framework:** Next.js 16 (App Router) + React 19 + TypeScript en modo estricto (`strict: true`).
- **Base de Datos / ORM:** SQLite (`better-sqlite3`) con Drizzle ORM.
- **Testing:** Vitest con asertos explícitos y metodología AAA.
- **Estilos & UI:** Bootstrap 5 + Design System propio (`src/components/ui/`).
- **Linter:** ESLint 9 (flat config).

## 2. Convenciones de Arquitectura
1. **Server Components por defecto:** Todo componente en `src/app/` es un Server Component salvo que requiera interactividad del navegador o hooks de cliente (`'use client'`).
2. **Acceso a Datos:** Toda persistencia y consulta SQL se realiza a través de Drizzle ORM (`src/db/`). Prohibido ejecutar SQL raw no tipado.
3. **Manejo de Errores en Rutas de API:** Las respuestas de error deben retornar objetos JSON estructurados con código de estado HTTP adecuado y campo explicativo `detail`.
4. **Nombres e Idioma:** Identificadores, tipos, funciones y archivos en inglés (`camelCase` / `PascalCase`); textos visibles al usuario final en español.

## 3. Prácticas de Calidad y Testing
1. **Red-Green-Refactor:** Cada funcionalidad nueva debe acompañarse de sus pruebas en `tests/`.
2. **Cero `any`:** Prohibido el uso de `any` para eludir el sistema de tipos.
3. **Validación Determinística:** El pipeline de validación (`tsc --noEmit`, `eslint .`, `vitest run`, `next build`) debe estar completamente verde.
