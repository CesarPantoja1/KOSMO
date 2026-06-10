# Puerta de Revisión de Requisitos

Antes de escribir `requirements.md`, revisa los requisitos generados y repara problemas locales hasta que pasen la revisión o se descubra una ambigüedad real de alcance.

## Pureza de Negocio (NO NEGOCIABLE)

KOSMO opera en capa de negocio. Los requisitos deben describir **comportamiento observable desde la perspectiva del usuario/stakeholder**, sin ninguna referencia a implementación técnica.

- **CERO referencias** a tecnologías, frameworks, bases de datos, protocolos, lenguajes de programación o infraestructura.
- Si un requisito menciona cualquier término técnico → **BLOCKER automático**.
- Todo requisito debe ser verificable por un analista de negocio sin conocimientos técnicos.
- Usa "El sistema" como sujeto consistente. No uses nombres de componentes, servicios o módulos.

**Términos prohibidos explícitamente:**
API, endpoint, REST, GraphQL, WebSocket, HTTP, JSON, XML, base de datos, tabla, columna, índice, SQL, NoSQL, PostgreSQL, MongoDB, Redis, servidor, contenedor, frontend, backend, componente, módulo, clase, método, controlador, middleware, framework, librería, React, Angular, Django, Spring, Node, Python, Java, microservicio, ORM, Docker, Kubernetes, CDN, caché, deploy.

## Rúbrica de Scoring de Requisitos

Cada requisito se evalúa en 6 dimensiones con la siguiente ponderación:

| Dimensión | Peso | Umbral de aprobación | Qué evalúa |
|-----------|:----:|:--------------------:|------------|
| **pureza_negocio** | 30% | >= 7 | Ausencia total de fugas de implementación |
| **correccion_ears** | 25% | >= 7 | El source_statement sigue exactamente el patrón EARS declarado |
| **verificabilidad** | 20% | >= 5 | Criterios de aceptación medibles y verificables por analista funcional |
| **completitud** | 10% | >= 5 | Todos los campos requeridos están presentes y completos |
| **no_ambiguedad** | 10% | >= 5 | Lenguaje concreto sin términos vagos o subjetivos |
| **cobertura** | 5% | >= 3 | Suficientes criterios de aceptación, trigger presente, justificación de negocio |

**Puntaje global:** promedio ponderado de las 6 dimensiones.

### Severidad del veredicto

| Puntaje global | Veredicto | Acción |
|:--------------:|-----------|--------|
| >= 7.0 | `approved` | El requisito pasa a revisión final |
| 5.0 - 6.9 | `warning` | Requiere ajustes — reenviar al generador con feedback específico |
| < 5.0 | `blocker` | Rechazado automáticamente — corregir antes de continuar |
| Fuga técnica detectada | `blocker` | Rechazo inmediato sin importar otros scores |

## Continuidad de Frontera (Boundary Continuity)

Usa terminología de frontera de forma consistente sin convertir requisitos en diseño:

- **Discovery** identifica `Candidatos de Frontera`
- **Requisitos** hacen explícitas expectativas de inclusión, exclusión y adyacencia cuando el alcance podría malinterpretarse
- **Diseño** convierte esas expectativas en `Compromisos de Frontera`
- **Tareas** usan `_Frontera:_` para restringir el trabajo ejecutable

Los requisitos deben clarificar la frontera de la funcionalidad en términos observables por el usuario u operador, no en propiedad de arquitectura o detalle de implementación.

## Revisión de Alcance y Cobertura

- El borrador debe cubrir los flujos principales del usuario, fronteras de alcance relevantes, casos de error primarios y condiciones de borde significativas visibles para el usuario u operador.
- Si la funcionalidad toca sistemas, especificaciones o flujos adyacentes, el borrador debe declarar qué espera de ellos y qué no posee, cuando esa distinción afecta el comportamiento visible para el usuario.
- Reglas de negocio, restricciones de cumplimiento, expectativas de seguridad/privacidad y restricciones operativas que moldean el comportamiento visible del usuario deben reflejarse explícitamente cuando están en alcance.
- Si falta cobertura porque el borrador está incompleto, repara el borrador y revisa de nuevo.
- Si la cobertura no puede completarse porque la descripción del proyecto o el contexto de dirección es ambiguo, contradictorio o subespecificado, detente y pide aclaración al usuario en lugar de adivinar.

## Revisión EARS y Verificabilidad

- Cada criterio de aceptación debe seguir las reglas EARS definidas en `ears_format.md`.
- Cada requisito debe ser verificable, observable y lo suficientemente específico para que diseño y validación posteriores puedan verificarlo.
- Elimina detalles de implementación que pertenecen a `design.md` en lugar de `requirements.md`.
- Los encabezados de requisito deben usar IDs numéricos únicamente; no mezclar etiquetas numéricas y alfabéticas.

## Revisión de Estructura y Calidad

- Agrupa comportamientos relacionados en áreas de requisito coherentes sin duplicar la misma obligación en múltiples secciones.
- Haz explícitas las fronteras de inclusión/exclusión cuando el alcance de la funcionalidad podría malinterpretarse.
- Mantén las declaraciones de frontera ligeras y observables: describe responsabilidad de la funcionalidad y expectativas adyacentes sin prescribir componentes, capas o propiedad interna.
- Asegura que las expectativas no funcionales permanezcan observables por el usuario u operador; mueve elecciones tecnológicas y detalles de arquitectura interna fuera de los requisitos.
- Normaliza lenguaje vago como "rápido", "robusto" o "seguro" en expectativas concretas visibles para el usuario siempre que el material fuente lo respalde.

## Verificaciones Mecánicas

Antes de aplicar juicio, verifica mecánicamente:
- **IDs numéricos presentes**: Cada encabezado de requisito tiene un ID numérico.
- **Criterios de aceptación existen**: Cada requisito tiene al menos un criterio de aceptación en formato EARS.
- **Sin lenguaje de implementación**: Busca términos específicos de tecnología que pertenecen a diseño, no a requisitos. Marca cualquier hallazgo.
- **Detección de fugas técnicas**: Ejecutar validación automática de fugas de implementación. Cualquier coincidencia es BLOCKER.

## Ciclo de Revisión

- Ejecuta verificaciones mecánicas primero, luego revisión basada en juicio.
- Si los problemas son locales al borrador, repara el borrador y vuelve a ejecutar la puerta de revisión.
- Mantén el ciclo acotado: máximo 2 pases de revisión y reparación antes de escalar una ambigüedad real al usuario.
- Escribe `requirements.md` solo después de que la puerta de revisión apruebe.
