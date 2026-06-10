# Guia de Formato de Descubrimiento — Enfoque de Negocio

## Principio Fundamental

El documento de Descubrimiento en KOSMO documenta la comprension del producto desde la perspectiva del negocio y del usuario. Describe QUE problema resuelve, PARA QUIEN, y CUAL es su propuesta de valor. NUNCA menciona tecnologia, infraestructura, ni implementacion.

## Secciones del Documento

### 1. Vision del producto
Razon de ser del producto, proposito fundamental, impacto esperado en el negocio y en los usuarios.

**Preguntas guia:**
- Que producto o solucion estamos creando?
- Cual es su proposito fundamental?
- Que cambio positivo genera en el negocio o en los usuarios?

**Ejemplo (negocio):**
"Plataforma de gestion de pedidos para restaurantes que permite a los meseros tomar ordenes desde la mesa, enviarlas directamente a cocina y permitir que los clientes paguen sin esperar la cuenta."

### 2. Espacio del problema
Problema que resuelve, contexto actual, dolores, necesidades insatisfechas.

**Preguntas guia:**
- Que problema concreto resuelve?
- Quienes sufren este problema hoy?
- Como lo resuelven actualmente (si es que lo resuelven)?
- Que consecuencias tiene no resolverlo?

### 3. Actores
Usuarios, sistemas externos, stakeholders, con su rol y responsabilidades desde la perspectiva del negocio.

**Preguntas guia:**
- Quienes usaran el producto? (roles de negocio, no tecnicos)
- Que necesita cada actor del sistema?
- Que responsabilidades tiene cada actor en el proceso de negocio?

### 4. Propuesta de valor
Valor unico para cada actor, diferenciacion frente a alternativas existentes.

**Preguntas guia:**
- Que valor unico entrega a cada tipo de usuario?
- Por que elegirian este producto sobre las alternativas?
- Que problema resuelve que nadie mas resuelve?

### 5. Casos de uso
Escenarios principales de uso, como los actores logran sus objetivos de negocio.

**Preguntas guia:**
- Cuales son los flujos principales que un usuario realiza?
- Que pasos sigue cada actor para lograr su objetivo?
- Que resultados espera obtener?

### 6. Capacidades principales
Funcionalidades clave que el producto debe tener para cumplir su proposito.

**Preguntas guia:**
- Que debe poder hacer el sistema para que los usuarios logren sus objetivos?
- Cuales son las capacidades sin las cuales el producto no tiene sentido?

### 7. Reglas de negocio
Reglas, politicas y restricciones del dominio de negocio que el sistema debe respetar.

**Preguntas guia:**
- Que reglas del negocio debe cumplir el sistema?
- Hay restricciones legales o normativas?
- Que politicas internas afectan el comportamiento del sistema?

### 8. Atributos de calidad
Expectativas no funcionales desde la perspectiva del negocio y del usuario.

**Preguntas guia:**
- Que expectativas de rendimiento tiene el negocio? (tiempos de respuesta, capacidad)
- Que nivel de disponibilidad esperan los usuarios?
- Que requisitos de seguridad o privacidad aplican?
- Cuantos usuarios concurrentes se esperan?
- NOTA: Expresa todo en terminos de negocio (ej. "El sistema debe procesar un pedido en menos de 30 segundos", NO "El servidor debe tener 4 cores").

### 9. Alcance
Que esta incluido en el producto, que esta explicitamente fuera, y que podria considerarse en el futuro.

**Preguntas guia:**
- Que funcionalidades estan DENTRO del alcance de esta version?
- Que esta explicitamente FUERA?
- Que podria considerarse en versiones futuras?

## Terminos Prohibidos (NON-NEGOTIABLE)

NO uses bajo ninguna circunstancia:
- Tecnologias: API, endpoint, REST, GraphQL, WebSocket, HTTP, JSON, XML
- Bases de datos: tabla, columna, SQL, NoSQL, PostgreSQL, MongoDB, Redis
- Frameworks: React, Angular, Vue, Django, Flask, Spring, Node, Python, Java
- Infraestructura: servidor, contenedor, Docker, Kubernetes, cloud, AWS, CDN
- Implementacion: componente, modulo, clase, metodo, controlador, middleware
- Arquitectura: frontend, backend, microservicio

## Checklist de Calidad por Seccion

Antes de aceptar una seccion del discovery, verifica que:

- [ ] Describe el producto desde la perspectiva del usuario o negocio
- [ ] NO contiene terminos tecnicos o de implementacion
- [ ] Responde a las preguntas guia de la seccion
- [ ] Usa lenguaje claro y concreto, sin ambiguedades
- [ ] Tiene suficiente profundidad (2-4 parrafos con contenido sustancial)
- [ ] Los ejemplos son del dominio del negocio, no tecnicos
