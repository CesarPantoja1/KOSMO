# Requisitos: {{FEATURE_TITLE}}

## Descripción de la Funcionalidad

{{FEATURE_DESCRIPTION}}

<!-- Opcional cuando el alcance podría malinterpretarse o la funcionalidad toca sistemas/especificaciones adyacentes -->
## Contexto de Frontera (Opcional)
- **Dentro del alcance**: {{IN_SCOPE_BEHAVIORS}}
- **Fuera del alcance**: {{OUT_OF_SCOPE_BEHAVIORS}}
- **Expectativas adyacentes**: {{ADJACENT_SYSTEM_OR_SPEC_EXPECTATIONS}}

## Requisitos del Negocio

<!-- Los requisitos se agrupan automáticamente por categoría EARS según la naturaleza del negocio -->

### Requisitos Ubicuos

Comportamiento que aplica siempre, sin condiciones previas. Características fundamentales del producto.

<!-- EJEMPLO -->
1. **The system shall identificar de forma única cada entidad del negocio**
   - **Patrón:** ubiquitous
   - **Sistema:** El sistema
   - **Respuesta:** identifica de forma única cada entidad del negocio mediante un identificador asignado al momento de su creación
   - **Justificación:** La trazabilidad de cada entidad es esencial para auditoría y operación del negocio
   - **Criterios de aceptación:**
     1. Dado que se crea una nueva entidad, cuando el sistema la registra, entonces la entidad recibe un identificador único que no se repite
     2. Dado que existe un identificador, cuando se consulta por ese identificador, entonces se recupera exactamente una entidad

### Requisitos Basados en Eventos

Comportamiento que se activa como respuesta a un evento o acción del usuario.

<!-- EJEMPLO -->
1. **WHEN el usuario realiza una acción de negocio, the system shall ejecutar el comportamiento esperado**
   - **Patrón:** event
   - **Disparador:** WHEN el usuario realiza una acción de negocio
   - **Sistema:** El sistema
   - **Respuesta:** ejecuta el comportamiento esperado por el negocio
   - **Justificación:** El negocio requiere que esta acción dispare un proceso específico
   - **Criterios de aceptación:**
     1. Dado que el usuario está autenticado, cuando realiza la acción de negocio, entonces el sistema inicia el proceso correspondiente

### Requisitos Determinados por el Estado

Comportamiento que depende del estado de una entidad de negocio mientras dicho estado persiste.

<!-- EJEMPLO -->
1. **WHILE la entidad de negocio está en un estado específico, the system shall mantener el comportamiento asociado a dicho estado**
   - **Patrón:** state
   - **Disparador:** WHILE la entidad de negocio está en un estado específico
   - **Sistema:** El sistema
   - **Respuesta:** mantiene el comportamiento asociado a dicho estado
   - **Justificación:** El negocio define reglas diferentes según el estado de la entidad
   - **Criterios de aceptación:**
     1. Dado que la entidad está en el estado específico, cuando se intenta una acción no permitida, entonces el sistema la rechaza

### Requisitos Opcionales

Comportamiento que solo aplica cuando una característica o configuración de negocio está activa.

<!-- EJEMPLO -->
1. **WHERE la funcionalidad de negocio está habilitada, the system shall ofrecer el comportamiento adicional**
   - **Patrón:** optional
   - **Disparador:** WHERE la funcionalidad de negocio está habilitada
   - **Sistema:** El sistema
   - **Respuesta:** ofrece el comportamiento adicional configurado
   - **Justificación:** El negocio ofrece esta funcionalidad como valor agregado opcional
   - **Criterios de aceptación:**
     1. Dado que la funcionalidad está habilitada, cuando el usuario interactúa con el sistema, entonces el comportamiento adicional está disponible

### Requisitos de Respuesta ante Fallos

Comportamiento del sistema ante situaciones no deseadas del negocio.

<!-- EJEMPLO -->
1. **IF ocurre una condición no deseada del negocio, THEN the system shall responder de forma controlada**
   - **Patrón:** unwanted
   - **Disparador:** IF ocurre una condición no deseada del negocio
   - **Sistema:** El sistema
   - **Respuesta:** responde de forma controlada protegiendo la integridad del negocio
   - **Justificación:** El negocio requiere manejo controlado de situaciones excepcionales
   - **Criterios de aceptación:**
     1. Dado que ocurre la condición no deseada, cuando el sistema la detecta, entonces notifica al usuario y preserva el estado del negocio

### Requisitos Complejos

Combinaciones de múltiples condiciones de negocio que definen un comportamiento.

<!-- EJEMPLO -->
1. **WHEN se cumple la primera condición de negocio AND se cumple la segunda, the system shall ejecutar el comportamiento combinado**
   - **Patrón:** complex
   - **Disparador:** WHEN se cumple la primera condición de negocio AND se cumple la segunda
   - **Sistema:** El sistema
   - **Respuesta:** ejecuta el comportamiento combinado según las reglas de negocio
   - **Justificación:** El negocio define reglas que dependen de múltiples condiciones simultáneas
   - **Criterios de aceptación:**
     1. Dado que se cumplen ambas condiciones, cuando ocurre el evento disparador, entonces el sistema ejecuta el comportamiento definido
