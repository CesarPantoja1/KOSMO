# Guía de Contribución a KOSMO

¡Gracias por tu interés en contribuir a **KOSMO (Knowledge Orchestration for Spec-driven MOdeling)**! 

KOSMO es una plataforma asistida por IA orientada a la unificación de requisitos en lenguaje natural (estándar EARS), diagramado arquitectónico determinista y trazabilidad de software. Esta guía describe el flujo de trabajo, estándares de código y buenas prácticas acordadas por el equipo de desarrollo (EPN TIC).

---

## Tabla de Contenidos

1. [Código de Conducta](#código-de-conducta)
2. [Estrategia de Ramas (Git Flow)](#estrategia-de-ramas-git-flow)
3. [Convención Estricta de Commits](#convención-estricta-de-commits)
4. [Entorno de Desarrollo Local](#entorno-de-desarrollo-local)
5. [Estándares de Código y Arquitectura](#estándares-de-código-y-arquitectura)
   * [Backend (FastAPI & Arquitectura Hexagonal)](#backend-fastapi--arquitectura-hexagonal)
   * [Frontend (Next.js & TypeScript)](#frontend-nextjs--typescript)
6. [Flujo para Enviar un Pull Request (PR)](#flujo-para-enviar-un-pull-request-pr)
7. [Pruebas y Verificación](#pruebas-y-verificación)

---

## Código de Conducta

Al participar en este proyecto, te comprometes a mantener un entorno respetuoso, inclusivo y profesional. Por favor, consulta nuestro [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) para más detalles.

---

## Estrategia de Ramas (Git Flow)

El desarrollo en KOSMO se organiza mediante ramas basadas en características o historias de usuario (*User Stories*):

* **`main`**: Código estable y listo para producción.
* **`feature/hu-<id>-<descripcion-corta>`**: Ramas de trabajo para la implementación de nuevas historias de usuario o características (ej. `feature/hu-12-generacion-diagrama-actividad-ia`).
* **`fix/<descripcion-corta>`**: Ramas para la corrección de errores puntuales o *hotfixes*.

> **Nota:** No trabajes directamente sobre la rama `main`. Todas las modificaciones deben integrarse mediante Pull Requests revisados.

---

## Convención Estricta de Commits

En KOSMO seguimos una convención estricta de mensajes de commit para mantener un historial limpio y legible:

### Reglas de formato:
1. **Idioma:** Todos los mensajes de commit deben escribirse en **español**.
2. **Formato:** Usar el prefijo del tipo de cambio seguido de dos puntos y espacio `: `. **No incluyas paréntesis ni textos adicionales antes de la descripción.**
3. **Estructura:** `<tipo>: <descripción en minúsculas y modo imperativo/descriptivo>`

### Tipos de commit permitidos:

| Tipo | Descripción | Ejemplo |
|---|---|---|
| `feat` | Nueva funcionalidad o característica | `feat: agregar generador de diagramas de secuencia` |
| `fix` | Corrección de errores en código o configuración | `fix: corregir proxy_pass en nginx para endpoints v1` |
| `docs` | Cambios en documentación | `docs: actualizar guia de despliegue en docker` |
| `style` | Cambios de formato, espacios o linting (sin afectar lógica) | `style: formatear controladores de proyectos con ruff` |
| `refactor` | Refactorización de código existente sin cambiar comportamiento | `refactor: desacoplar servicios de agentes en capa de aplicacion` |
| `test` | Adición o modificación de pruebas unitarias/integración | `test: agregar pruebas para endpoint de salud` |
| `chore` | Tareas de mantenimiento, dependencias o tooling | `chore: actualizar dependencias en pyproject.toml` |

---

## Entorno de Desarrollo Local

### Requisitos Previos:
* [Docker](https://www.docker.com/) y [Docker Compose](https://docs.docker.com/compose/)
* [Python 3.13+](https://www.python.org/) y [`uv`](https://github.com/astral-sh/uv) (para desarrollo de backend)
* [Node.js 20+](https://nodejs.org/) y [`bun`](https://bun.sh/) (para desarrollo de frontend)

### Configuración del proyecto:

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/CesarPantoja1/KOSMO.git
   cd KOSMO
   ```

2. **Configurar variables de entorno:**
   Copia el archivo de ejemplo para crear tu entorno local:
   ```bash
   cp .env.example .env
   ```

3. **Levantar la infraestructura de servicios con Docker Compose:**
   ```bash
   docker compose up -d --build
   ```
   * Frontend: `http://localhost:3000`
   * Backend API: `http://localhost:8000`
   * Documentación Swagger: `http://localhost:8000/docs`

---

## Estándares de Código y Arquitectura

### Backend (FastAPI & Arquitectura Hexagonal)
* Ubicación: `backend/src/kosmo/`
* **Capas de Arquitectura Hexagonal:**
  * `domain/`: Entidades de negocio, agregados, objetos de valor y excepciones de dominio. No depende de ningún marco externo.
  * `application/`: Casos de uso, servicios de aplicación e interfaces de puertos.
  * `infrastructure/`: Adaptadores externos (base de datos con PostgreSQL/pgvector, MongoDB, Redis, API FastAPI, integraciones con LLM).
* **Gestión de dependencias:** Usamos `uv` para gestionar paquetes en `pyproject.toml` y `uv.lock`.

### Frontend (Next.js & TypeScript)
* Ubicación: `frontend/`
* Framework: Next.js (App Router), React, TypeScript.
* Diseño UI: Utilizar la guía de diseño del proyecto, evitando valores arbitrarios en píxeles cuando se puedan usar variables del sistema de diseño.

---

## Flujo para Enviar un Pull Request (PR)

1. Crea tu rama desde la rama base de trabajo:
   ```bash
   git checkout -b feature/hu-XX-mi-funcionalidad
   ```
2. Realiza tus cambios y haz commits siguiendo la [Convención Estricta de Commits](#convención-estricta-de-commits).
3. Asegúrate de que las pruebas pasen y el código construya sin errores.
4. Envía la rama al repositorio remoto:
   ```bash
   git push origin feature/hu-XX-mi-funcionalidad
   ```
5. Abre un **Pull Request** en GitHub / Azure DevOps describiendo:
   * El objetivo de la historia de usuario o corrección.
   * Los cambios principales realizados.
   * El plan de verificación o pruebas realizadas.
6. Asigna revisores y realiza los ajustes solicitados hasta obtener la aprobación.

---

## Pruebas y Verificación

Antes de enviar tu PR, ejecuta las pruebas en tu entorno local:

### Backend:
```bash
cd backend
uv run pytest
```

### Frontend:
```bash
cd frontend
bun run build
```

---

¡Gracias por contribuir a la evolución de KOSMO! Si tienes dudas o sugerencias, abre un *issue* o contacta al equipo de desarrollo.
