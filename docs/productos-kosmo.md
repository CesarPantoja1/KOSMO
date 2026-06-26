# Productos de KOSMO

Este documento define la estructura de los tres productos de KOSMO y presenta un ejemplo de flujo completo que evidencia la trazabilidad entre ellos.

---

## 1. Descubrimiento

El producto de Descubrimiento opera exclusivamente a nivel de negocio. Su propósito consiste en capturar y validar el entendimiento del dominio del problema y la oportunidad que el producto pretende abordar, sin hacer referencia alguna a tecnología, infraestructura o componentes de software. Se compone de siete secciones.

### 1.1. Visión del producto

Párrafo breve de dos a cuatro oraciones que presenta la razón de existir del producto, el público al que se dirige y el propósito central que persigue. Funciona como la declaración fundacional que alinea a todos los involucrados en torno a una misma comprensión del producto.

### 1.2. Espacio del problema

Describe la situación actual que motiva la creación del producto. Identifica quiénes padecen el problema, en qué contexto se manifiesta y cuáles son las consecuencias de no resolverlo. Establece la brecha entre la realidad del usuario y la solución deseada.

### 1.3. Actores

Enumera las personas, roles u organizaciones que interactúan con el producto o se ven afectadas por él. Para cada actor se proporciona una descripción de su rol, su interés principal y su relación con el problema descrito.

### 1.4. Propuesta de valor

Articula el beneficio concreto y diferenciador que el producto ofrece a cada actor identificado previamente. Cada declaración conecta un actor con la mejora tangible que obtiene al utilizar el producto.

### 1.5. Metas del producto

Metas de alto nivel que el producto debe cumplir para resolver el problema identificado. Cada meta comienza con un título de máximo cinco palabras que identifica el área de negocio que abarca, seguido de una declaración verificable de lo que el negocio necesita lograr. De cada meta se derivan múltiples Características en la fase siguiente. Las metas no describen escenarios de interacción ni nombran actores específicos. Mínimo dos metas.

### 1.6. Reglas de negocio

Restricciones, condiciones y políticas que gobiernan el comportamiento del producto desde la perspectiva del dominio. Cada regla es una afirmación verificable que define una condición específica que siempre debe cumplirse. Mínimo cuatro reglas.

### 1.7. Alcance

Delimita de forma explícita qué está incluido en el producto, qué queda excluido y qué podría incorporarse en el futuro. Se organiza en tres categorías (Incluido, Excluido, Futuro potencial) con un mínimo de tres exclusiones explícitas.

---

## 2. Características

El producto de Características opera a nivel de usuario. Cada característica expresa lo que el usuario desea lograr, no lo que el software hace. En este nivel no existe todavía un sistema ni una aplicación. Se compone de cuatro campos.

### 2.1. Código

Identificador único con el formato C seguido de un número correlativo de dos dígitos (C01, C02, C03).

### 2.2. Título

Máximo seis palabras que expresan la intención de interacción del usuario con el futuro producto. Se redacta como una acción que el usuario desea realizar, evitando nomenclatura de software y terminología de negocio.

### 2.3. Descripción

Párrafo de una a dos oraciones que describe cómo el usuario interactuaría con el producto para lograr el propósito del título. Se construye desde la perspectiva del usuario, sin mencionar componentes de software, mecanismos técnicos ni conceptos de negocio abstractos.

### 2.4. Origen

Unifica la justificación de existencia de la característica y las secciones del Descubrimiento de las cuales se deriva. Explica en una a dos oraciones por qué resulta esencial y enumera las secciones del Descubrimiento que la fundamentan.

---

## 3. Requisitos

El producto de Requisitos opera a nivel de software y traduce cada característica aprobada en requisitos formales verificables utilizando la notación EARS (Easy Approach to Requirements Syntax). En este nivel ya se permite nombrar componentes técnicos y especificar comportamientos del sistema. Cada requisito se genera para una sola característica y se compone de cinco campos.

### 3.1. Código

Identificador único con el formato REQ seguido del número de la característica, un punto y el correlativo del requisito (REQ-1.1, REQ-1.2, REQ-3.5).

### 3.2. Patrón

Clasifica el requisito en una de las seis categorías EARS, cada una con su propia sintaxis.

| Patrón | Sintaxis |
|--------|----------|
| Ubicuo | El sistema shall [comportamiento] |
| Basado en Eventos | CUANDO [evento], el sistema shall [comportamiento] |
| Determinado por el Estado | MIENTRAS [estado], el sistema shall [comportamiento] |
| Opcional | DONDE [opción], el sistema shall [comportamiento] |
| Respuesta ante Comportamiento no Deseado | SI [condición no deseada], el sistema shall [mitigación] |
| Complejo | MIENTRAS [estado] Y CUANDO [evento], el sistema shall [comportamiento] |

### 3.3. Enunciado

Oración completa del requisito redactada en la sintaxis EARS correspondiente a su patrón. Se trata como una unidad indivisible ya que cada patrón posee una estructura sintáctica diferente.

### 3.4. Origen

Unifica la justificación de existencia del requisito y su cadena de derivación hacia la característica y el Descubrimiento. Explica por qué es necesario y enumera la característica de origen junto con las secciones del Descubrimiento que lo fundamentan.

### 3.5. Criterios de aceptación

Interacciones funcionales concretas del usuario con el producto que demuestran el cumplimiento del requisito. Cada criterio tiene un Escenario (título breve) seguido del patrón Dado, Cuando, Entonces, donde Cuando describe una acción de interacción concreta como hacer clic en un botón, seleccionar una opción o ingresar un valor. Mínimo dos criterios por requisito.

---

# Ejemplo de flujo completo

Producto ficticio GastoJusto que ilustra la trazabilidad Descubrimiento → Características → Requisitos.

## Descubrimiento de GastoJusto

### Visión del producto

GastoJusto es un producto diseñado para grupos de personas que comparten gastos de forma recurrente, como compañeros de vivienda, grupos de viaje o equipos de trabajo. Su propósito central consiste en eliminar la fricción y los conflictos que surgen al dividir gastos de manera informal. El producto facilita que cada participante registre, visualice y liquide sus deudas de forma transparente y equitativa.

### Espacio del problema

Los grupos de personas que comparten gastos recurren habitualmente a métodos informales como hojas de cálculo, mensajes de texto o acuerdos verbales para llevar el control de lo que cada persona debe. Estos métodos generan errores frecuentes en los cálculos, olvidos de pagos realizados y conflictos entre los participantes. La falta de un registro centralizado y confiable provoca que las deudas se acumulen sin resolverse, deteriorando las relaciones personales dentro del grupo. El problema se agrava proporcionalmente al tamaño del grupo y a la frecuencia de los gastos compartidos.

### Actores

* **Miembro del grupo** es cualquier persona que participa en los gastos compartidos, ya sea registrando gastos propios, consultando sus deudas o realizando pagos a otros miembros
* **Administrador del grupo** es la persona responsable de crear el grupo, invitar participantes y supervisar que los balances estén actualizados y correctos
* **Participante ocasional** es una persona que se incorpora al grupo temporalmente para un evento o actividad específica y necesita gestionar sus aportes de forma aislada

### Propuesta de valor

* **Para el Miembro del grupo** el producto ofrece la posibilidad de consultar en todo momento cuánto debe y a quién, eliminando la incertidumbre y las discusiones sobre montos pendientes
* **Para el Administrador del grupo** el producto proporciona una visión consolidada de todos los balances del grupo, permitiendo identificar rápidamente desequilibrios y facilitar la liquidación de deudas
* **Para el Participante ocasional** el producto permite incorporarse a un grupo existente de forma ágil, participar en los gastos relevantes y desvincularse una vez liquidadas sus cuentas

### Metas del producto

1. **Gestión financiera de gastos:** todo gasto compartido se distribuye entre los participantes con exactitud matemática, cada participante puede consultar el estado de sus deudas y acreencias en todo momento, y las deudas del grupo se pueden liquidar con la menor cantidad de transferencias posibles
2. **Administración de grupos:** un grupo se puede crear con moneda y reglas de reparto definidas, admite la incorporación y desvinculación de participantes en cualquier momento, y no permite que un miembro se desvincule mientras tenga deudas pendientes

### Reglas de negocio

1. Todo gasto registrado debe tener al menos dos participantes para que la distribución sea posible
2. El monto total distribuido entre los participantes debe ser exactamente igual al monto original del gasto sin diferencias por redondeo
3. Un participante no puede ser eliminado de un grupo mientras tenga deudas pendientes con otros miembros
4. Los métodos de reparto disponibles son partes iguales, porcentajes personalizados y montos fijos por participante
5. La moneda de un grupo se define al momento de su creación y no puede modificarse posteriormente

### Alcance

**Incluido**

* Registro y distribución de gastos compartidos entre miembros de un grupo
* Cálculo automático de balances individuales y optimización de liquidaciones
* Creación y administración de grupos con gestión de membresía

**Excluido**

* Procesamiento de pagos reales entre cuentas bancarias de los participantes
* Conversión automática entre divisas para grupos con múltiples monedas
* Funcionalidades de contabilidad empresarial o facturación fiscal

**Futuro potencial**

* Reconocimiento de tickets de compra mediante fotografía para registro automático de gastos
* Integración con servicios de pago para facilitar las transferencias entre participantes
* Soporte para múltiples divisas dentro de un mismo grupo con conversión automática

---

## Características de GastoJusto

| Código | Título | Descripción | Origen |
|--------|--------|-------------|--------|
| C01 | Registrar gastos entre participantes | Cualquier participante del grupo indica el monto de un gasto, selecciona a las personas involucradas y elige cómo repartirlo. Se calcula de forma inmediata cuánto corresponde a cada persona y actualiza los balances de todos los involucrados. | Se deriva de la meta Gestión financiera de gastos. Sin esta característica no existiría la información base para calcular balances. Se traza a Metas del producto, Actores y Reglas de negocio. |
| C02 | Consultar balances y deudas pendientes | Cualquier participante accede a un resumen que muestra cuánto debe, a quién le debe y quién le adeuda, con el detalle de cada gasto que originó el saldo. | Se deriva de la meta Gestión financiera de gastos. Se traza a Metas del producto, Propuesta de valor y Reglas de negocio. |
| C03 | Liquidar deudas del grupo | El administrador visualiza un plan de transferencias optimizado que indica quién debe pagar a quién y cuánto, permitiendo saldar todas las deudas con la menor cantidad de movimientos posibles. | Se deriva de la meta Gestión financiera de gastos. Se traza a Metas del producto, Propuesta de valor y Reglas de negocio. |
| C04 | Crear y administrar grupos | El administrador establece un nuevo grupo, define su moneda de operación, invita participantes y gestiona la membresía a lo largo del tiempo. | Se deriva de la meta Administración de grupos y es prerrequisito para todas las demás características. Se traza a Metas del producto, Actores y Reglas de negocio. |
| C05 | Participar temporalmente en un grupo | Una persona se incorpora a un grupo existente para un evento específico, participa en los gastos correspondientes y cierra su participación una vez que su balance queda en cero. | Se deriva de la meta Administración de grupos. Se traza a Metas del producto, Propuesta de valor y Actores. |

---

## Requisitos de C01

### REQ-1.1

| Campo | Contenido |
|-------|-----------|
| Patrón | Ubicuo |
| Enunciado | El sistema shall presentar todos los montos con exactamente dos decimales y la moneda configurada para el grupo |
| Origen | Garantiza consistencia visual en la presentación de valores monetarios conforme a la regla de negocio que exige exactitud en los montos distribuidos. Se deriva de C01 y Reglas de negocio. |

**Criterios de Aceptación**

**Escenario: Montos en pantalla de balance**

**Dado** que el usuario se encuentra en la pantalla principal del grupo

**Cuando** hace clic en la pestaña "Balance"

**Entonces** todos los montos aparecen formateados con dos decimales y el símbolo de la moneda del grupo

**Escenario: Montos en detalle de un gasto**

**Dado** que el usuario se encuentra en el listado de gastos del grupo

**Cuando** hace clic en un gasto registrado para ver su detalle

**Entonces** cada cuota individual aparece con dos decimales y la moneda del grupo, incluyendo el monto total del gasto

### REQ-1.2

| Campo | Contenido |
|-------|-----------|
| Patrón | Basado en Eventos |
| Enunciado | CUANDO un participante confirma el registro de un gasto con participantes seleccionados, el sistema shall calcular la cuota correspondiente a cada participante según el método de reparto seleccionado y actualizar el balance de cada participante involucrado |
| Origen | Traduce la interacción central de la característica C01 en un comportamiento verificable del sistema. La distribución debe respetar la regla de negocio que exige que el monto distribuido sea exactamente igual al monto original. Se deriva de C01, Reglas de negocio y Metas del producto. |

**Criterios de Aceptación**

**Escenario: Reparto equitativo entre tres participantes**

**Dado** que el usuario se encuentra en la pantalla de registro de gastos con tres participantes seleccionados y reparto equitativo

**Cuando** ingresa 90 como monto del gasto y hace clic en el botón "Registrar"

**Entonces** el balance de cada participante seleccionado refleja una deuda de 30 unidades y la suma de las cuotas es exactamente 90

**Escenario: Reparto equitativo con monto no divisible**

**Dado** que el usuario se encuentra en la pantalla de registro de gastos con tres participantes seleccionados y reparto equitativo

**Cuando** ingresa 100 como monto del gasto y hace clic en el botón "Registrar"

**Entonces** las cuotas asignadas suman exactamente 100 unidades sin diferencia por redondeo y el balance de cada participante se actualiza de forma coherente

### REQ-1.3

| Campo | Contenido |
|-------|-----------|
| Patrón | Basado en Eventos |
| Enunciado | CUANDO un participante selecciona el método de reparto por porcentajes personalizados, el sistema shall validar que la suma de los porcentajes asignados sea exactamente 100 antes de permitir el registro |
| Origen | Previene errores de distribución al aplicar la regla de negocio que exige que el monto total distribuido sea igual al monto original. Se deriva de C01 y Reglas de negocio. |

**Criterios de Aceptación**

**Escenario: Porcentajes que no suman 100**

**Dado** que el usuario se encuentra en la pantalla de registro de gastos con reparto por porcentajes y ha asignado 40%, 30% y 20% a tres participantes

**Cuando** hace clic en el botón "Registrar"

**Entonces** el producto muestra un mensaje indicando que los porcentajes suman 90% y no 100%, impidiendo el registro hasta que se corrija

**Escenario: Porcentajes que suman 100**

**Dado** que el usuario se encuentra en la pantalla de registro de gastos con reparto por porcentajes y ha asignado 50%, 30% y 20% a tres participantes

**Cuando** hace clic en el botón "Registrar"

**Entonces** el gasto queda registrado correctamente y el balance de cada participante se actualiza según el porcentaje asignado

### REQ-1.4

| Campo | Contenido |
|-------|-----------|
| Patrón | Determinado por el Estado |
| Enunciado | MIENTRAS el grupo tiene un único participante activo, el sistema shall impedir el registro de nuevos gastos e informar que se requiere al menos un participante adicional |
| Origen | Aplica la regla de negocio que exige al menos dos participantes para que la distribución sea posible. Se deriva de C01, Reglas de negocio y Actores. |

**Criterios de Aceptación**

**Escenario: Intento de registro sin participantes suficientes**

**Dado** que el usuario pertenece a un grupo donde es el único miembro activo

**Cuando** hace clic en la opción "Nuevo gasto"

**Entonces** el producto muestra un aviso indicando que no es posible registrar gastos sin al menos otro participante en el grupo

**Escenario: Registro habilitado al incorporar un segundo miembro**

**Dado** que el usuario pertenece a un grupo donde acaba de incorporarse un segundo miembro

**Cuando** hace clic en la opción "Nuevo gasto"

**Entonces** el producto abre la pantalla de registro de gastos con normalidad, permitiendo seleccionar al nuevo participante

### REQ-1.5

| Campo | Contenido |
|-------|-----------|
| Patrón | Opcional |
| Enunciado | DONDE el participante elige el método de reparto por montos fijos, el sistema shall permitir asignar un monto específico a cada participante y validar que la suma de los montos individuales sea igual al monto total del gasto |
| Origen | Soporta la variante de reparto por montos fijos descrita en las reglas de negocio como uno de los tres métodos disponibles. Se deriva de C01 y Reglas de negocio. |

**Criterios de Aceptación**

**Escenario: Montos fijos que suman el total**

**Dado** que el usuario se encuentra en la pantalla de registro de un gasto de 100 unidades y selecciona "Montos fijos" como método de reparto

**Cuando** asigna 50 al primer participante, 30 al segundo y 20 al tercero, y hace clic en el botón "Registrar"

**Entonces** el gasto queda registrado con las cuotas individuales indicadas y el balance de cada participante se actualiza según el monto asignado

**Escenario: Montos fijos que no suman el total**

**Dado** que el usuario se encuentra en la pantalla de registro de un gasto de 100 unidades con "Montos fijos" seleccionado

**Cuando** asigna 50 al primer participante y 30 al segundo sin asignar al tercero, y hace clic en el botón "Registrar"

**Entonces** el producto muestra un mensaje indicando que los montos asignados suman 80 y no coinciden con el total de 100, impidiendo el registro

### REQ-1.6

| Campo | Contenido |
|-------|-----------|
| Patrón | Respuesta ante Comportamiento no Deseado |
| Enunciado | SI la conexión del usuario se interrumpe durante el registro de un gasto, el sistema shall preservar los datos ingresados en el formulario y permitir completar el registro cuando la conexión se restablezca |
| Origen | Protege la experiencia del usuario ante interrupciones involuntarias, evitando la pérdida de datos durante la interacción principal de la característica C01. Se deriva de C01 y Metas del producto. |

**Criterios de Aceptación**

**Escenario: Recuperación de datos tras desconexión**

**Dado** que el usuario ha ingresado un monto y seleccionado participantes en el formulario de registro de gastos y pierde la conexión

**Cuando** la conexión se restablece y el usuario hace clic en la notificación de reconexión para regresar al formulario

**Entonces** el formulario conserva el monto ingresado y los participantes seleccionados previamente, permitiendo continuar con el registro sin repetir los pasos

**Escenario: Registro exitoso tras reconexión**

**Dado** que el usuario recuperó el formulario con los datos preservados después de una desconexión

**Cuando** verifica que los datos son correctos y hace clic en el botón "Registrar"

**Entonces** el gasto se registra con normalidad y los balances de los participantes se actualizan correctamente
