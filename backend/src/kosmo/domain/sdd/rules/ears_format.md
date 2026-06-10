# Guía de Formato EARS — Enfoque de Negocio

## Principio Fundamental

EARS (Easy Approach to Requirements Syntax) en KOSMO documenta **QUÉ comportamiento espera el negocio del sistema**, nunca cómo se implementa técnicamente. Cada requisito debe ser comprensible y verificable por un stakeholder sin conocimientos técnicos.

## Selección del Sujeto

- Usa **"El sistema"** de forma consistente en todos los requisitos.
- "El sistema" representa el producto o solución completa desde la vista del usuario o stakeholder.
- No uses nombres de servicios, módulos técnicos, componentes de software ni roles de arquitectura.

## Estructura de un Requisito EARS

Cada requisito se compone de los siguientes elementos:

| Elemento | Descripción | Obligatorio |
|----------|-------------|:-----------:|
| `source_statement` | Declaración completa en inglés con keywords EARS | Sí |
| `pattern` | Categoría EARS (ubiquitous/event/state/optional/unwanted/complex) | Sí |
| `trigger` | Condición o evento disparador (WHEN/IF/WHILE/WHERE) | Depende del patrón |
| `system` | Sujeto del requisito ("El sistema") | Sí |
| `response` | Respuesta o comportamiento esperado del sistema | Sí |
| `acceptance_criteria` | Criterios de aceptación verificables por negocio | Sí |
| `rationale` | Justificación: por qué el negocio necesita este comportamiento | Recomendado |

## Estructura de Criterios de Aceptación

Cada criterio debe seguir el formato **Dado-Cuando-Entonces**:

| Elemento | Significado | Ejemplo |
|----------|-------------|---------|
| `scenario` | Contexto inicial y evento disparador | "Dado que el cliente tiene un pedido en estado 'pendiente', cuando confirma el pago" |
| `description` | Descripción en lenguaje natural | "El sistema registra el pago y cambia el estado del pedido a 'confirmado'" |
| `expected_result` | Resultado concreto verificable | "El pedido aparece en la lista de pedidos confirmados y el cliente recibe una notificación" |

## Patrones EARS — Perspectiva de Negocio

### 1. Requisitos Ubicuos (Ubiquitous)

Comportamiento que aplica **siempre**, sin condiciones previas. Características fundamentales del producto.

**Patrón:** `The <system> shall <response>`

**Cuándo usarlo:**
- Propiedades fundamentales del sistema
- Comportamiento que no depende de eventos, estados ni condiciones
- Restricciones globales del negocio
- Identidad y características permanentes

**Ejemplos:**
- `The system shall identificar de forma única cada pedido mediante un número de referencia`
- `The system shall conservar el historial de transacciones del cliente durante 24 meses`
- `The system shall cumplir con la normativa de protección de datos personales aplicable`
- `The system shall estar disponible para los usuarios durante el horario de operación`

**Criterios de aceptación ejemplo:**
- `scenario`: "Dado que se crea un nuevo pedido, cuando el sistema lo registra"
- `expected_result`: "Cada pedido recibe un número de referencia único que no se repite"

### 2. Requisitos Basados en Eventos (Event-driven)

Comportamiento que se activa como **respuesta a un evento o acción del usuario**.

**Patrón:** `WHEN <trigger>, the <system> shall <response>`

**Cuándo usarlo:**
- Respuesta a una acción del usuario (clic, envío de formulario, confirmación)
- Respuesta a un evento de negocio (recepción de pago, vencimiento de plazo)
- Flujos de trabajo disparados por el usuario o stakeholder

**Ejemplos:**
- `WHEN el cliente confirma un pedido, the system shall reservar el inventario solicitado`
- `WHEN un usuario envía una consulta de soporte, the system shall registrar la consulta y asignar un número de seguimiento`
- `WHEN se alcanza la fecha de vencimiento de una suscripción, the system shall notificar al cliente con 7 días de anticipación`
- `WHEN un administrador aprueba una solicitud de reembolso, the system shall iniciar el proceso de devolución`

**Criterios de aceptación ejemplo:**
- `scenario`: "Dado que el cliente tiene productos en el carrito, cuando confirma el pedido"
- `expected_result`: "El inventario de cada producto se reduce en la cantidad solicitada y el pedido pasa a estado 'confirmado'"

### 3. Requisitos Determinados por el Estado (State-driven)

Comportamiento que depende del **estado de una entidad de negocio** mientras dicho estado persiste.

**Patrón:** `WHILE <state>, the <system> shall <response>`

**Cuándo usarlo:**
- Comportamiento condicionado al estado de un pedido, cuenta, suscripción, etc.
- Restricciones que aplican durante una fase del proceso de negocio
- Comportamiento que solo es válido mientras se cumple una condición

**Ejemplos:**
- `WHILE un pedido está en estado 'en preparación', the system shall permitir al cliente cancelarlo sin costo`
- `WHILE la cuenta del usuario está suspendida, the system shall restringir el acceso a funcionalidades de compra`
- `WHILE una campaña de marketing está activa, the system shall aplicar el descuento configurado al precio final`
- `WHILE el inventario de un producto está por debajo del umbral mínimo, the system shall mostrar una alerta al administrador`

**Criterios de aceptación ejemplo:**
- `scenario`: "Dado que un pedido está en estado 'en preparación', cuando el cliente solicita cancelarlo"
- `expected_result`: "El pedido se cancela sin generar cargos y el inventario se libera"

### 4. Requisitos Opcionales (Optional features)

Comportamiento que solo aplica cuando una **característica o configuración de negocio está activa**.

**Patrón:** `WHERE <feature enabled>, the <system> shall <response>`

**Cuándo usarlo:**
- Funcionalidades premium o por suscripción
- Características configurables por el cliente o administrador
- Comportamiento condicionado a la activación de un módulo de negocio

**Ejemplos:**
- `WHERE el cliente tiene suscripción premium activa, the system shall ofrecer envío gratuito en todos los pedidos`
- `WHERE la funcionalidad de notificaciones por correo está habilitada, the system shall enviar confirmación por cada transacción`
- `WHERE el módulo de facturación electrónica está activo, the system shall generar comprobantes fiscales por cada venta`
- `WHERE el cliente ha activado la verificación en dos pasos, the system shall solicitar un código adicional al iniciar sesión`

**Criterios de aceptación ejemplo:**
- `scenario`: "Dado que el cliente tiene suscripción premium, cuando realiza un pedido"
- `expected_result`: "El costo de envío aparece como $0.00 y el cliente no paga cargos de envío"

### 5. Requisitos de Respuesta ante Fallos (Unwanted behaviors)

Comportamiento del sistema ante **situaciones no deseadas del negocio** (errores, fallos, condiciones excepcionales).

**Patrón:** `IF <condition>, THEN the <system> shall <response>`

**Cuándo usarlo:**
- Manejo de errores de negocio (pago rechazado, inventario insuficiente)
- Validaciones que impiden continuar un proceso
- Situaciones excepcionales que requieren acción correctiva
- Protección ante condiciones que violan reglas de negocio

**Ejemplos:**
- `IF el pago es rechazado por la entidad financiera, THEN the system shall notificar al cliente y conservar el pedido en estado 'pendiente de pago'`
- `IF el inventario es insuficiente para cubrir un pedido, THEN the system shall informar al cliente sobre la disponibilidad parcial y ofrecer alternativas`
- `IF un cliente intenta exceder su límite de crédito, THEN the system shall rechazar la transacción y notificar el motivo`
- `IF se detecta que un producto está fuera del horario de entrega de su zona, THEN the system shall mostrar las franjas horarias disponibles`

**Criterios de aceptación ejemplo:**
- `scenario`: "Dado que un cliente intenta pagar con una tarjeta rechazada, cuando el sistema procesa el pago"
- `expected_result`: "El cliente ve un mensaje indicando que el pago fue rechazado y el pedido permanece en estado 'pendiente de pago'"

### 6. Requisitos Complejos (Complex)

Combinaciones de múltiples condiciones de negocio que definen un comportamiento.

**Patrón:** `WHEN ... AND/OR ... , WHILE ..., IF ... THEN ...`

**Cuándo usarlo:**
- Reglas de negocio compuestas
- Flujos con múltiples condiciones simultáneas
- Comportamiento que depende de más de un factor de negocio

**Ejemplos:**
- `WHEN el cliente solicita un reembolso AND el pedido fue entregado hace menos de 30 días, the system shall procesar el reembolso automáticamente`
- `WHEN un pedido supera los $1000 AND el cliente es nuevo, WHILE la verificación de identidad está pendiente, the system shall retener el pedido hasta verificación`
- `IF el cliente no ha realizado compras en 90 días AND tiene saldo a favor, THEN the system shall notificar al cliente sobre su saldo disponible`

## Verbos Medibles para Requisitos de Negocio

Usa verbos que describan comportamiento observable y verificable:

| Verbo | Uso | Ejemplo |
|-------|-----|---------|
| Registrar | Crear o almacenar información | "El sistema deberá registrar cada transacción" |
| Notificar | Informar al usuario/stakeholder | "El sistema deberá notificar al cliente cuando su pedido esté listo" |
| Mostrar | Presentar información al usuario | "El sistema deberá mostrar el historial de pedidos" |
| Calcular | Determinar un valor según reglas | "El sistema deberá calcular el costo total del pedido" |
| Validar | Verificar que se cumple una regla | "El sistema deberá validar que el cliente tenga crédito suficiente" |
| Restringir | Impedir una acción según reglas | "El sistema deberá restringir compras a clientes suspendidos" |
| Permitir | Habilitar una acción según reglas | "El sistema deberá permitir cancelar pedidos en estado 'pendiente'" |
| Generar | Producir un documento o resultado | "El sistema deberá generar un comprobante por cada venta" |
| Asignar | Atribuir un valor o responsable | "El sistema deberá asignar un número de seguimiento a cada consulta" |
| Actualizar | Modificar información existente | "El sistema deberá actualizar el inventario tras cada venta" |

## Anti-patrones — Lo que NUNCA debe aparecer en un requisito

### Fugas de implementación (BLOCKER automático)

| ❌ Incorrecto (técnico) | ✅ Correcto (negocio) |
|--------------------------|------------------------|
| `WHEN el endpoint POST /orders recibe una solicitud, the API shall devolver status 201` | `WHEN el cliente confirma un pedido, the system shall registrar la orden y confirmar al cliente` |
| `The system shall guardar el registro en la tabla 'customers' de PostgreSQL` | `The system shall conservar la información del cliente durante toda la relación comercial` |
| `El componente React del carrito mostrará los productos` | `El sistema deberá mostrar los productos agregados al carrito de compra` |
| `WHEN el microservicio de pagos recibe un evento de Kafka, the backend shall actualizar Redis` | `WHEN se confirma un pago, the system shall actualizar el estado del pedido` |

### Ambigüedades (deben evitarse)

| ❌ Ambigüedad | ✅ Concreto |
|---------------|-------------|
| "El sistema debe ser rápido" | "El sistema deberá mostrar el resultado de la búsqueda en menos de 3 segundos" |
| "La plataforma será segura" | "El sistema deberá requerir autenticación para acceder a datos del cliente" |
| "La interfaz debe ser intuitiva" | "El sistema deberá agrupar los pedidos por estado y permitir filtrar por fecha" |
| "El sistema debe ser escalable" | "El sistema deberá permitir el registro de nuevos clientes sin degradar el servicio" |

## Checklist de Calidad por Requisito

Antes de aceptar un requisito, verifica que:

- [ ] El `source_statement` sigue correctamente el patrón EARS declarado
- [ ] NO contiene términos técnicos (APIs, bases de datos, frameworks, lenguajes, infraestructura)
- [ ] Describe UN solo comportamiento atómico de negocio
- [ ] Usa "El sistema" como sujeto de forma consistente
- [ ] Tiene al menos 1 criterio de aceptación (idealmente 2-3)
- [ ] Cada criterio de aceptación es verificable por un analista de negocio
- [ ] El lenguaje es concreto, sin ambigüedades ("rápido", "seguro", "robusto")
- [ ] Incluye `rationale` que justifica por qué el negocio necesita este comportamiento
- [ ] La relación trigger→response es lógica y directa
- [ ] Cubre un escenario de negocio relevante (happy path, error, estado, opcional)
