# Política de Seguridad de KOSMO

En el equipo de desarrollo de **KOSMO (Knowledge Orchestration for Spec-driven MOdeling)** y la **Escuela Politécnica Nacional (EPN TIC)**, nos tomamos muy en serio la seguridad de nuestra plataforma, datos y usuarios. 

Agradecemos los esfuerzos de investigadores de seguridad y miembros de la comunidad que nos ayudan a mantener la integridad del sistema mediante la divulgación responsable de vulnerabilidades.

---

## Versiones Soportadas

Dado que KOSMO se encuentra actualmente en su ciclo de desarrollo activo hacia la versión 1.0, brindamos soporte de seguridad y parches de forma prioritaria en las siguientes ramas:

| Versión / Rama | Estado de Soporte |
|---|---|
| Rama Principal (`main`) | ✅ Soporte Activo |
| Versión 1.0.x (Release Actual) | ✅ Soporte Activo |
| Versiones Anteriores / Ramas obsoletas | ❌ Sin Soporte |

---

## Cómo Reportar una Vulnerabilidad (Divulgación Responsable)

**Por favor, NO reportes vulnerabilidades de seguridad a través de *issues* públicos de GitHub o Azure DevOps.**

Si has descubierto una vulnerabilidad de seguridad en KOSMO, sigue los siguientes pasos para una divulgación responsable:

1. **Contacto Privado:** Envía un correo electrónico detallado al equipo de arquitectura y mantenimiento del proyecto KOSMO o a la dirección institucional de EPN TIC.
2. **Información requerida:**
   * Descripción clara y detallada del problema o vulnerabilidad encontrada.
   * Pasos reproducibles o prueba de concepto (*PoC*).
   * Componente afectado (Backend FastAPI, Frontend Next.js, Nginx, Autenticación JWT, Docker/Infraestructura).
   * Evaluación potencial del impacto (ej. Escalación de privilegios, Inyección de comandos, Exposición de secretos).
3. **Confidencialidad:** Danos un tiempo razonable para investigar y solucionar la falla antes de hacer pública cualquier información.

---

## Compromiso y Tiempos de Respuesta

Nos comprometemos a responder a los reportes de seguridad con la mayor celeridad posible:

* **Acuse de recibo inicial:** Dentro de las primeras **24 a 48 horas** hábiles tras la recepción del reporte.
* **Evaluación y confirmación:** Dentro de los **5 días hábiles** posteriores al acuse de recibo.
* **Despliegue del parche de seguridad:** El tiempo de corrección dependerá de la severidad (las vulnerabilidades críticas tendrán prioridad máxima de corrección y despliegue dentro del entorno de integración continua).

---

## Buenas Prácticas de Seguridad Implementadas en KOSMO

Para garantizar la robustez del entorno, la arquitectura de KOSMO incluye por diseño las siguientes salvaguardas:

1. **Gestión de Secretos Desacoplada:**
   * Las claves asimétricas de firma de tokens (**RS256**) se montan como volúmenes de solo lectura en `/app/.secrets` y nunca se empaquetan dentro de las imágenes Docker.
2. **Contenedores y Menor Privilegio:**
   * La etapa runtime del backend se ejecuta sobre la imagen sin componentes de compilación (`python:3.13-slim-bookworm`) bajo un usuario no privilegiado denominado `kosmo`.
3. **Autenticación y Autorización:**
   * Firma de sesiones JWT con algoritmos asimétricos y expiración configurada.
4. **Infraestructura Aisla en Redes Privadas:**
   * Comunicación restringida entre contenedores mediante redes Docker aisladas (`kosmo-network`), exponiendo únicamente el proxy inverso Nginx/Cloudflared.
5. **Análisis de Vulnerabilidades:**
   * Escaneo periódico de dependencias de código (usando `uv` en Python y `bun` en Node.js) y análisis de vulnerabilidades en imágenes base de contenedores.

---

¡Gracias por ayudarnos a mantener la plataforma KOSMO segura y confiable!
