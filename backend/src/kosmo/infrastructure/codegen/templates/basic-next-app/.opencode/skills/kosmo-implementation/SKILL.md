---
name: kosmo-implementation
description: Directrices de Clean Architecture, TypeScript estricto y convenciones de capas para el workspace de KOSMO. Trigger: architecture, implement, domain, service, clean architecture.
---

# Clean Architecture & Implementación en KOSMO

Esta skill define las reglas de diseño arquitectónico y de código que el agente debe seguir obligatoriamente para estructurar el software generado.

---

## 1. Principios Fundacionales de Clean Architecture

El proyecto organiza el código en capas concéntricas con regla de dependencia unidireccional: **el código de negocio nunca depende de detalles de infraestructura o frameworks**.

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

1. **Cero `any`:** Prohibido el uso de `any` para silenciar errores del compilador. Usa `unknown`, `never`, genéricos o interfaces bien tipadas.
2. **Inmutabilidad por Defecto:** Prefiere `readonly`, `ReadonlyArray`, `const` y copias inmutables (spread operator `...`) sobre mutaciones directas de objetos o arrays.
3. **Manejo de Errores con Tipos:** Usa excepciones tipadas o tipos de resultado estructurados. Prohibido capturar errores genéricos y silenciarlos.
4. **Nomenclatura:** Código e identificadores en inglés (`PascalCase` para componentes y tipos, `camelCase` para funciones y variables); textos y etiquetas de interfaz de usuario en español.

---

## 3. Anti-patrones Prohibidos para el Agente (LLM Guardrails)

| Anti-patrón | Por qué está prohibido | Solución requerida |
|-------------|------------------------|-------------------|
| **Lógica en Componentes UI** | Rompe la testabilidad y mezcla presentación con negocio | Extraer reglas a funciones puras en `src/lib/` o `src/services/` |
| **SQL en Vistas de Cliente** | Inseguro y no compila en el cliente | Mover consultas a Server Components o Rutas de API |
| **Monolito en `page.tsx`** | Dificulta mantenimiento y testing | Dividir en subcomponentes modulares en `src/components/` |
| **Mutaciones Globales** | Provoca efectos secundarios no deterministas | Funciones puras que retornan nuevos estados |
| **Silenciar errores de compilación (`@ts-ignore`)** | Oculta bugs críticos | Corregir los tipos exactos hasta que `tsc --noEmit` pase limpio |

---

## 4. Checklist de Calidad para el Agente

Antes de dar una característica por implementada, verifica:
- [ ] La lógica pura está separada de los componentes React.
- [ ] No existen tipos `any` ni directivas `@ts-ignore`.
- [ ] Cada función exportada cuenta con tests unitarios en `tests/`.
- [ ] Las consultas de base de datos usan Drizzle ORM con tipado estricto.
- [ ] El pipeline de validación (`tsc`, `eslint`, `vitest`, `build`) pasa al 100%.
