# 🏗️ Arquitectura Frontend — FSD Progresivo

## 📌 Plan de Implementación

Este documento define el marco arquitectónico del proyecto TIC, basado en la metodología **Feature-Sliced Design (FSD)** aplicada de forma progresiva.

El objetivo es garantizar que el sistema sea **escalable, mantenible y modular** desde sus primeras etapas de desarrollo.

---

## 🎯 Justificación de FSD en Proyectos TIC

Los proyectos de Tecnología de la Información y Comunicación (TIC) suelen enfrentarse a requisitos cambiantes y a un incremento constante en la complejidad. En este contexto, FSD aporta:

* **Estandarización**
  Proporciona una estructura clara de carpetas y reglas de importación, reduciendo ambigüedad en la organización del código.

* **Escalabilidad controlada**
  Permite que el proyecto crezca de forma orgánica sin derivar en un monolito difícil de mantener.

* **Separación de responsabilidades**
  Aísla la lógica de negocio, la interfaz y las acciones del usuario, facilitando pruebas y mantenimiento.

---

## 🚀 Enfoque Progresivo

La implementación se divide en dos fases principales:

---

## 🧱 Fase 1: Fundamentos (Base del Sistema)

Se prioriza la definición del dominio, la infraestructura y los datos.

### 1. **Shared**

Capa más desacoplada y transversal. No contiene lógica de negocio.

* `ui/` → Componentes atómicos (botones, inputs)
* `lib/` → Utilidades, hooks genéricos
* `api/` → Configuración de clientes HTTP
* `assets/` → Recursos globales

---

### 2. **Entities**

Representa los conceptos clave del dominio.

* **Slices**: Usuario, Proyecto, Modelo, etc.
* **Segments**:

  * `ui/` → Componentes visuales de la entidad
  * `model/` → Tipos, estado, validaciones
  * `lib/` → Transformaciones de datos
  * `api/` → Endpoints específicos

---

### 3. **App**

Configuración global de la aplicación.

* `providers/` → Contextos globales (Auth, Theme, Store)
* `styles/` → Estilos globales
* `setup/` → Configuración de frameworks/plugins

---

### 4. **Pages**

Responsable del enrutamiento y composición de vistas.

* **Slices**: Cada ruta
* **Segments**:

  * `ui/` → Layout de la página
  * `model/` → Lógica específica de la página

---

## ⚙️ Fase 2: Interactividad y Composición

Se incorporan funcionalidades y componentes complejos.

### 5. **Features**

Acciones que el usuario puede realizar.

* **Slices**: Casos de uso (ej. `edit-requirements`, `search-project`)
* **Segments**:

  * `ui/` → Formularios y acciones
  * `model/` → Estado y validaciones
  * `api/` → Requests al backend
  * `lib/` → Procesamiento de datos

---

### 6. **Widgets**

Componentes complejos que integran múltiples elementos.

* **Slices**: Bloques UI (navbar, dashboard, panel)
* **Segments**:

  * `ui/` → Composición visual
  * `model/` → Coordinación de estados

---

## 🧩 Estructura Jerárquica FSD

FSD se organiza en tres niveles:

```
Layer → Slice → Segment
```

* **Layer (Capa)** → Nivel arquitectónico (Shared, Entities, etc.)
* **Slice (Rebanada)** → Unidad funcional o de dominio
* **Segment (Segmento)** → Tipo de responsabilidad técnica

---

## 📦 Estándar de Segmentos

La mayoría de los slices siguen esta estructura:

* `ui/` → Componentes visuales
* `model/` → Estado, tipos, lógica
* `lib/` → Helpers y utilidades internas
* `api/` → Comunicación con servicios externos

---

## 📏 Reglas de Código

### 1. Naming

* **Componentes** → `PascalCase` (`UserCard.tsx`)
* **Archivos utilitarios** → `kebab-case` (`use-local-storage.ts`)
* **Variables/Funciones** → `camelCase`
* **Constantes** → `UPPER_SNAKE_CASE`

---

### 2. TypeScript

* Tipado estricto habilitado
* Evitar `any` (usar `unknown` o genéricos)
* `interface` → Objetos y props
* `type` → Uniones y tipos complejos

---

### 3. Componentes

* Funciones flecha:

  ```ts
  const Component = () => {}
  ```
* Exportaciones nombradas (excepto en `page.tsx`)
* Desestructuración de props
* Uso de **early returns**

---

### 4. Next.js (App Router)

* Usar `'use client'` solo cuando sea necesario
* Fetching en Server Components
* Colocation de archivos relacionados

---

### 5. Estilos

* Uso de **Tailwind CSS**
* Evitar inline styles
* Mantener orden lógico de clases

---

### 6. Imports

Orden recomendado:

1. React / Next
2. Librerías externas
3. Módulos internos (`@/`)
4. Hooks / utils
5. Tipos
6. Estilos

---

### 7. Manejo de Estado

* **URL** → Estados compartibles
* **Local** → `useState`
* **Global** → Zustand (solo cuando sea necesario)

---

### 8. Documentación

* Uso de **JSDoc** en funciones complejas
* Comentarios enfocados en el **por qué**, no en el qué

---

## ✅ Conclusión

El enfoque progresivo de FSD permite:

* Construir una base sólida desde el inicio
* Escalar sin comprometer la arquitectura
* Mantener bajo acoplamiento y alta cohesión

Esto asegura que el proyecto evolucione de forma sostenible a medida que crece en complejidad.


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
