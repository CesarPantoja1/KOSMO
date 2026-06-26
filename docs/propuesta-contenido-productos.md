# Propuesta de Contenido para los Productos de KOSMO

Este documento se organiza en dos partes. La primera parte define las secciones y campos que componen cada producto, junto con la justificación de su inclusión. La segunda parte presenta un ejemplo de flujo completo que recorre los tres productos de forma continua para evidenciar la trazabilidad entre ellos.

---

# Parte 1. Definición de secciones y campos

## 1. Producto de Descubrimiento

El producto de Descubrimiento constituye la fase inicial del pipeline de KOSMO y opera exclusivamente a nivel de negocio. Su propósito consiste en capturar, organizar y validar el entendimiento del dominio del problema y la oportunidad que el producto pretende abordar. Cada sección del documento resultante se orienta a comunicar el valor, el contexto y las reglas del negocio sin hacer referencia alguna a tecnología, infraestructura o componentes de software. El documento se compone de siete secciones obligatorias.

### 1.1. Visión del producto

**Descripción**

La Visión del producto presenta en un párrafo breve de dos a cuatro oraciones la razón de existir del producto, el público al que se dirige y el propósito central que persigue. Funciona como la declaración fundacional que alinea a todos los involucrados en torno a una misma comprensión del producto.

**Justificación**

Todo proceso de descubrimiento requiere un punto de partida que unifique expectativas. La visión cumple ese rol al sintetizar el qué, el para quién y el para qué en un solo párrafo. Sin esta declaración, las secciones posteriores carecerían de un marco de referencia compartido, lo cual generaría ambigüedad en la interpretación de actores, reglas y alcance.

### 1.2. Espacio del problema

**Descripción**

El Espacio del problema describe la situación actual que motiva la creación del producto. Identifica quiénes padecen el problema, en qué contexto se manifiesta y cuáles son las consecuencias de no resolverlo. Esta sección establece la brecha entre la realidad del usuario y la solución deseada.

**Justificación**

Definir con precisión el problema es un requisito previo para cualquier propuesta de valor sólida. Una descripción vaga conduce a soluciones desenfocadas que no atienden necesidades reales. Articular las consecuencias tangibles de la situación actual permite priorizar funcionalidades en fases posteriores y sirve como criterio de validación para determinar si el producto efectivamente resuelve lo que se propone.

### 1.3. Actores

**Descripción**

La sección de Actores enumera las personas, roles u organizaciones que interactúan con el producto o se ven afectadas por él. Para cada actor se proporciona una descripción de su rol, su interés principal y su relación con el problema descrito.

**Justificación**

Identificar a los actores de forma explícita garantiza que el producto contemple las perspectivas de todos los involucrados relevantes. Omitir un actor puede derivar en la exclusión de funcionalidades críticas o en decisiones de diseño sesgadas hacia un solo perfil. Asimismo, la lista de actores establece la base para la Propuesta de valor, donde cada actor recibe un beneficio diferenciado.

### 1.4. Propuesta de valor

**Descripción**

La Propuesta de valor articula el beneficio concreto y diferenciador que el producto ofrece a cada actor identificado previamente. Cada declaración conecta un actor con la mejora tangible que obtiene al utilizar el producto.

**Justificación**

Esta sección traduce el problema en beneficios específicos por actor, lo cual permite validar que el producto aporta algo significativo a cada perfil. Si algún actor no recibe un beneficio claro, su inclusión debería reconsiderarse. Cada beneficio declarado debe materializarse en al menos una funcionalidad futura, lo cual convierte a esta sección en insumo directo para la fase de Características.

### 1.5. Metas del producto

**Descripción**

La sección de Metas del producto establece las metas de alto nivel que el producto debe cumplir para resolver el problema identificado. De cada meta se derivan múltiples Características en la fase siguiente. Las metas no describen escenarios de interacción ni nombran actores específicos. Se requiere un mínimo de dos metas.

**Justificación**

Las metas expresan qué quiere lograr el negocio, mientras que las Características expresan qué quiere hacer el usuario. Al redactar metas verificables se establece un criterio claro de éxito para el producto que puede evaluarse al final de cada ciclo de implementación. Su nivel amplio garantiza que cada una genere varias Características, organizando la descomposición del producto en una relación de uno a muchos y evitando la duplicación entre fases.

### 1.6. Reglas de negocio

**Descripción**

Las Reglas de negocio establecen las restricciones, condiciones y políticas que gobiernan el comportamiento del producto desde la perspectiva del dominio. Cada regla es una afirmación verificable que define una condición específica que siempre debe cumplirse. Se requiere un mínimo de cuatro reglas.

**Justificación**

Las reglas delimitan lo que el producto puede y no puede hacer dentro del contexto del dominio. Sin ellas, las decisiones sobre comportamiento quedarían a interpretación libre de quien implementa, generando inconsistencias. Al expresarlas de forma verificable, se facilita su conversión en requisitos formales durante la fase de Requisitos y en criterios de aceptación.

### 1.7. Alcance

**Descripción**

La sección de Alcance delimita de forma explícita qué está incluido en el producto, qué queda excluido y qué podría incorporarse en el futuro. Se organiza en tres categorías claramente diferenciadas con un mínimo de tres exclusiones explícitas.

**Justificación**

El alcance previene la expansión descontrolada del producto y establece expectativas claras entre todos los involucrados. Las exclusiones explícitas eliminan supuestos implícitos que suelen generar conflictos en fases avanzadas. La categoría de futuro potencial permite capturar ideas valiosas sin comprometerse a implementarlas, preservando el enfoque sin perder oportunidades de evolución.

---

## 2. Producto de Características

El producto de Características opera a nivel de usuario y su propósito consiste en descomponer el Documento de Descubrimiento en un conjunto de intenciones de interacción que un usuario tendría con el futuro producto de software. En este nivel no existe todavía un sistema ni una aplicación, por lo tanto cada característica expresa lo que el usuario desea lograr, no lo que el software hace. Cada característica se compone de cuatro campos.

### 2.1. Código

**Descripción**

El código asigna un identificador único a cada característica con el formato C seguido de un número correlativo de dos dígitos, como C01, C02 o C03. Este código permite referenciar la característica de forma inequívoca a lo largo de todo el pipeline.

**Justificación**

La trazabilidad entre productos requiere un mecanismo de referencia estable y conciso. El formato correlativo de dos dígitos soporta hasta 99 características por proyecto, lo cual resulta suficiente para cualquier escenario razonable.

### 2.2. Título

**Descripción**

El título expresa en un máximo de seis palabras la intención de interacción del usuario con el futuro producto. Se redacta como una acción que el usuario desea realizar, evitando nomenclatura de software y terminología de negocio. Debe ser claro, distintivo y libre de ambigüedad respecto a las demás características del mismo proyecto.

**Justificación**

Limitar a seis palabras obliga a la precisión y previene descripciones vagas o genéricas. Redactar desde la intención de interacción garantiza que el nivel de abstracción se mantiene centrado en el usuario, estableciendo una frontera clara con el nivel de negocio del Descubrimiento y con el nivel técnico de los Requisitos.

### 2.3. Descripción

**Descripción**

La descripción presenta en un párrafo de una a dos oraciones cómo el usuario interactuaría con el producto para lograr el propósito expresado en el título. La narrativa se construye desde la perspectiva del usuario, describiendo lo que esta persona realiza y lo que obtiene como resultado, sin mencionar componentes de software, mecanismos técnicos ni conceptos de negocio abstractos.

**Justificación**

La descripción complementa el título al proporcionar el contexto necesario para comprender la interacción completa. Al redactar desde la perspectiva del usuario se asegura que la característica permanece en su nivel de abstracción correcto, lo cual facilita su posterior traducción a requisitos formales sin contaminación de supuestos técnicos. La restricción a una o dos oraciones impide que se convierta en una especificación prematura.

### 2.4. Origen

**Descripción**

El origen unifica en un solo campo la justificación de existencia de la característica y las secciones del Descubrimiento de las cuales se deriva. Explica en una a dos oraciones por qué esta característica resulta esencial para el producto y enumera las secciones específicas del Documento de Descubrimiento que la fundamentan.

**Justificación**

Cada característica debe demostrar que su existencia se sustenta en una necesidad real identificada durante el Descubrimiento. Este campo impide la inclusión de características arbitrarias o desconectadas del problema original, al mismo tiempo que hace visible la cadena de derivación para facilitar el análisis de impacto cuando el Descubrimiento se modifica.

---

## 3. Producto de Requisitos

El producto de Requisitos opera a nivel de software y su propósito consiste en traducir cada característica aprobada en un conjunto de requisitos formales verificables utilizando la notación EARS (Easy Approach to Requirements Syntax). En este nivel ya se permite nombrar componentes técnicos, referirse al sistema y especificar comportamientos esperados de forma precisa. Cada requisito se genera para una sola característica y se compone de cinco campos.

### 3.1. Código

**Descripción**

El código asigna un identificador único a cada requisito con el formato REQ seguido del número de la característica, un punto y el número correlativo del requisito dentro de esa característica, como REQ-1.1, REQ-1.2 o REQ-3.5. Esta notación vincula cada requisito con su característica de origen de forma inmediata.

**Justificación**

El formato compuesto cumple una doble función al proporcionar unicidad global y trazabilidad implícita hacia la característica. La estructura REQ-X.Y permite navegar la jerarquía de requisitos sin consultar tablas auxiliares y facilita la referencia cruzada en documentos de diseño y matrices de trazabilidad.

### 3.2. Patrón

**Descripción**

El patrón clasifica cada requisito en una de las seis categorías definidas por la metodología EARS. Cada categoría determina una estructura sintáctica diferente para el enunciado del requisito y comunica el tipo de condición que lo gobierna. Las seis categorías son Ubicuo, Basado en Eventos, Determinado por el Estado, Opcional, Respuesta ante Comportamiento no Deseado y Complejo.

La siguiente tabla presenta la sintaxis propia de cada patrón.

| Patrón | Sintaxis |
|--------|----------|
| Ubicuo | El sistema shall [comportamiento] |
| Basado en Eventos | CUANDO [evento], el sistema shall [comportamiento] |
| Determinado por el Estado | MIENTRAS [estado], el sistema shall [comportamiento] |
| Opcional | DONDE [opción], el sistema shall [comportamiento] |
| Respuesta ante Comportamiento no Deseado | SI [condición no deseada], el sistema shall [mitigación] |
| Complejo | MIENTRAS [estado] Y CUANDO [evento], el sistema shall [comportamiento] |

**Justificación**

La clasificación por patrón obliga a que cada requisito exprese con precisión bajo qué circunstancias se activa, eliminando la ambigüedad inherente al lenguaje libre. Dado que cada patrón posee una estructura sintáctica diferente, el enunciado del requisito no se descompone en campos separados sino que se presenta como una oración completa que respeta la forma de su patrón.

### 3.3. Enunciado

**Descripción**

El enunciado es la oración completa del requisito redactada en la sintaxis EARS correspondiente a su patrón. Constituye la representación íntegra y canónica del requisito. Su forma varía según la categoría asignada, ya que un requisito ubicuo carece de condición previa mientras que un requisito complejo combina un estado con un evento. Por esta razón, el enunciado se trata como una unidad indivisible que respeta la estructura propia de su patrón.

**Justificación**

La adherencia estricta a la sintaxis EARS garantiza que el requisito es analizable de forma automática y cumple con los estándares de la notación. Al ser la representación completa, funciona como la referencia autoritativa para validaciones, revisiones y aprobaciones.

### 3.4. Origen

**Descripción**

El origen unifica en un solo campo la justificación de existencia del requisito y su cadena de derivación hacia la característica y el Descubrimiento. Explica en una a dos oraciones por qué este requisito es necesario y enumera la característica de origen junto con las secciones del Descubrimiento que lo fundamentan.

**Justificación**

Este campo previene la aparición de requisitos huérfanos que no responden a una necesidad real. La trazabilidad bidireccional permite verificar la completitud del conjunto de requisitos hacia arriba y facilita el análisis de impacto hacia abajo cuando una característica o sección del Descubrimiento cambia.

### 3.5. Criterios de aceptación

**Descripción**

Los criterios de aceptación describen interacciones funcionales concretas del usuario con el producto que demuestran el cumplimiento del requisito. Cada criterio comienza con un Escenario, que es un título breve y descriptivo que identifica la situación que se va a verificar. A continuación sigue el patrón Dado, Cuando, Entonces, donde Dado establece el contexto en el que el usuario se encuentra, Cuando describe la acción de interacción concreta que el usuario realiza sobre el producto (como hacer clic en un botón, seleccionar una opción o ingresar un valor) y Entonces expresa el resultado observable que el producto presenta. Se requieren al menos dos criterios por requisito.

**Justificación**

Los criterios constituyen el puente entre la especificación y la verificación. Al describir interacciones reales del usuario con el producto se garantiza que cada criterio es comprobable mediante la utilización directa del producto. El Escenario permite identificar rápidamente qué situación cubre cada criterio sin necesidad de leer el detalle completo. La exigencia de al menos dos criterios por requisito asegura que se cubren tanto el flujo esperado como variantes relevantes de la interacción.

---

# Parte 2. Ejemplo de flujo completo

El siguiente ejemplo utiliza un producto ficticio llamado GastoJusto para ilustrar la trazabilidad entre los tres productos de KOSMO. Cada fase se deriva de la anterior, y las referencias cruzadas permiten recorrer la cadena completa desde el negocio hasta el software.

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

Las cinco características que se presentan a continuación se derivan del Documento de Descubrimiento anterior. Cada una expresa la intención de interacción del usuario con el futuro producto. 

| Código | Título | Descripción | Origen |
|--------|--------|-------------|--------|
| C01 | Registrar gastos entre participantes | Cualquier participante del grupo indica el monto de un gasto, selecciona a las personas involucradas y elige cómo repartirlo. El producto calcula de forma inmediata cuánto corresponde a cada persona y actualiza los balances de todos los involucrados. | Se deriva de la meta Gestión financiera de gastos. Sin esta característica no existiría la información base para calcular balances. Se traza a Metas del producto, Actores y Reglas de negocio. |
| C02 | Consultar balances y deudas pendientes | Cualquier participante accede a un resumen que muestra cuánto debe, a quién le debe y quién le adeuda, con el detalle de cada gasto que originó el saldo. | Se deriva de la meta Gestión financiera de gastos. Se traza a Metas del producto, Propuesta de valor y Reglas de negocio. |
| C03 | Liquidar deudas del grupo | El administrador visualiza un plan de transferencias optimizado que indica quién debe pagar a quién y cuánto, permitiendo saldar todas las deudas con la menor cantidad de movimientos posibles. | Se deriva de la meta Gestión financiera de gastos. Se traza a Metas del producto, Propuesta de valor y Reglas de negocio. |
| C04 | Crear y administrar grupos | El administrador establece un nuevo grupo, define su moneda de operación, invita participantes y gestiona la membresía a lo largo del tiempo. | Se deriva de la meta Administración de grupos y es prerrequisito para todas las demás características. Se traza a Metas del producto, Actores y Reglas de negocio. |
| C05 | Participar temporalmente en un grupo | Una persona se incorpora a un grupo existente para un evento específico, participa en los gastos correspondientes y cierra su participación una vez que su balance queda en cero. | Se deriva de la meta Administración de grupos. Se traza a Metas del producto, Propuesta de valor y Actores. |

---

## Requisitos de la característica C01

Los requisitos que se presentan a continuación traducen la característica C01 "Registrar gastos entre participantes" en especificaciones formales EARS. Se distribuyen en cinco patrones diferentes para garantizar una cobertura integral.

### Requisitos Ubicuos

**REQ-1.1**

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

### Requisitos Basados en Eventos

**REQ-1.2**

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

**REQ-1.3**

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

### Requisitos Determinados por el Estado

**REQ-1.4**

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

### Requisitos Opcionales

**REQ-1.5**

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

### Requisitos de Respuesta ante Comportamiento no Deseado

**REQ-1.6**

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
