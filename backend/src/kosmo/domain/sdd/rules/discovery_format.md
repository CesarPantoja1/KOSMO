# Guía de Formato de Descubrimiento — Enfoque de Negocio

## Principio Fundamental

El documento de Descubrimiento en KOSMO documenta la comprensión del producto desde la perspectiva del negocio y del usuario. Describe QUÉ problema resuelve, PARA QUIÉN, y CUÁL es su propuesta de valor. NUNCA menciona tecnología, infraestructura, ni implementación.

## Secciones del Documento

### 1. Visión del producto
Razón de ser del producto, propósito fundamental, impacto esperado en el negocio y en los usuarios.

**Preguntas guía:**
- ¿Qué producto o solución estamos creando?
- ¿Cuál es su propósito fundamental?
- ¿Qué cambio positivo genera en el negocio o en los usuarios?

**Ejemplo (negocio):**
"Plataforma de gestión de pedidos para restaurantes que permite a los meseros tomar órdenes desde la mesa, enviarlas directamente a cocina y permitir que los clientes paguen sin esperar la cuenta."

### 2. Espacio del problema
Problema que resuelve, contexto actual, dolores, necesidades insatisfechas.

**Preguntas guía:**
- ¿Qué problema concreto resuelve?
- ¿Quiénes sufren este problema hoy?
- ¿Cómo lo resuelven actualmente (si es que lo resuelven)?
- ¿Qué consecuencias tiene no resolverlo?

### 3. Actores
Usuarios, sistemas externos, stakeholders, con su rol y responsabilidades desde la perspectiva del negocio.

**Preguntas guía:**
- ¿Quiénes usarán el producto? (roles de negocio, no técnicos)
- ¿Qué necesita cada actor del sistema?
- ¿Qué responsabilidades tiene cada actor en el proceso de negocio?

### 4. Propuesta de valor
Valor único para cada actor, diferenciación frente a alternativas existentes.

**Preguntas guía:**
- ¿Qué valor único entrega a cada tipo de usuario?
- ¿Por qué elegirían este producto sobre las alternativas?
- ¿Qué problema resuelve que nadie más resuelve?

### 5. Casos de uso
Escenarios principales de uso, cómo los actores logran sus objetivos de negocio.

**Preguntas guía:**
- ¿Cuáles son los flujos principales que un usuario realiza?
- ¿Qué pasos sigue cada actor para lograr su objetivo?
- ¿Qué resultados espera obtener?

### 6. Capacidades principales
Funcionalidades clave que el producto debe tener para cumplir su propósito.

**Preguntas guía:**
- ¿Qué debe poder hacer el sistema para que los usuarios logren sus objetivos?
- ¿Cuáles son las capacidades sin las cuales el producto no tiene sentido?

### 7. Reglas de negocio
Reglas, políticas y restricciones del dominio de negocio que el sistema debe respetar.

**Preguntas guía:**
- ¿Qué reglas del negocio debe cumplir el sistema?
- ¿Hay restricciones legales o normativas?
- ¿Qué políticas internas afectan el comportamiento del sistema?

### 8. Atributos de calidad
Expectativas no funcionales desde la perspectiva del negocio y del usuario.

**Preguntas guía:**
- ¿Qué expectativas de rendimiento tiene el negocio? (tiempos de respuesta, capacidad)
- ¿Qué nivel de disponibilidad esperan los usuarios?
- ¿Qué requisitos de seguridad o privacidad aplican?
- ¿Cuántos usuarios concurrentes se esperan?
- NOTA: Expresa todo en términos de negocio (ej. "El sistema debe procesar un pedido en menos de 30 segundos", NO "El servidor debe tener 4 cores").

### 9. Alcance
Qué está incluido en el producto, qué está explícitamente fuera, y qué podría considerarse en el futuro.

**Preguntas guía:**
- ¿Qué funcionalidades están DENTRO del alcance de esta versión?
- ¿Qué está explícitamente FUERA?
- ¿Qué podría considerarse en versiones futuras?

## Términos Prohibidos (NON-NEGOTIABLE)

NO uses bajo ninguna circunstancia:
- Tecnologías: API, endpoint, REST, GraphQL, WebSocket, HTTP, JSON, XML
- Bases de datos: tabla, columna, SQL, NoSQL, PostgreSQL, MongoDB, Redis
- Frameworks: React, Angular, Vue, Django, Flask, Spring, Node, Python, Java
- Infraestructura: servidor, contenedor, Docker, Kubernetes, cloud, AWS, CDN
- Implementación: componente, módulo, clase, método, controlador, middleware
- Arquitectura: frontend, backend, microservicio

## Checklist de Calidad por Sección

Antes de aceptar una sección del discovery, verifica que:

- [ ] Describe el producto desde la perspectiva del usuario o negocio
- [ ] NO contiene términos técnicos o de implementación
- [ ] Responde a las preguntas guía de la sección
- [ ] Usa lenguaje claro y concreto, sin ambigüedades
- [ ] Tiene suficiente profundidad (2-4 párrafos con contenido sustancial)
- [ ] Los ejemplos son del dominio del negocio, no técnicos
