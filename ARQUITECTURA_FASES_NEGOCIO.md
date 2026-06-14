# KOSMO — Propuesta Técnica: Arquitectura Escalable para Fases de Negocio

> **Alcance**: Fases 1–3 (Descubrimiento, Características, Requisitos EARS).
> **Principio**: 100% negocio, 0% tecnología.
> **Estrategia**: Un agente ReAct con 3 modos de comportamiento hoy, extensible a orquestación multiagente mañana. Agnóstico al framework de orquestación.

---

## Tabla de Contenidos

1. [Visión General](#1-visión-general)
2. [Naturaleza del Agente: ReAct, no Prompt Chaining](#2-naturaleza-del-agente-react-no-prompt-chaining)
3. [Arquitectura: KOSMOAgent con PhaseModes](#3-arquitectura-kosmoagent-con-phasemodes)
4. [Memoria Centralizada y Estado](#4-memoria-centralizada-y-estado)
5. [Gestión de Contexto e Inyección de Herramientas](#5-gestión-de-contexto-e-nyección-de-herramientas)
6. [Flujo de Backend: Endpoints y Lógica](#6-flujo-de-backend-endpoints-y-lógica)
7. [Adaptación del Framework cc-sdd](#7-adaptación-del-framework-cc-sdd)
8. [System Prompts por PhaseMode](#8-system-prompts-por-phasemode)
9. [Diagramas Conceptuales](#9-diagramas-conceptuales)
10. [Estructura de Directorios y Contratos](#10-estructura-de-directorios-y-contratos)
11. [Roadmap de Migración a Multiagente](#11-roadmap-de-migración-a-multiagente)
12. [Orden de Implementación](#12-orden-de-implementación)

---

## 1. Visión General

### 1.1 Diagnóstico del Estado Actual

| Aspecto | Estado Actual | Problema |
|---------|--------------|----------|
| **Orquestación** | `kosmo_graph.py` con 17 nodos LangGraph | Complejidad excesiva para 3 fases de negocio; acoplado a LangGraph |
| **Estado** | `KOSMOState` monolítico (~40 campos) | Arrastra contexto no relevante entre fases; race conditions con reducers |
| **Agentes** | Supervisor + 4 generadores + 3 críticos + merger/evaluator | Overkill; la lógica de negocio está entrelazada con la orquestación |
| **Fases faltantes** | `CARACTERISTICAS` no tiene lógica; `MODELO` e `IMPLEMENTACION` devuelven `human_input_pending` | Solo `DESCUBRIMIENTO` y `REQUISITOS` funcionan end-to-end |
| **Composición** | Wire manual en routers; `composition.py` solo tiene Auth | No hay wiring de agentes ni pipeline |

### 1.2 Principios de Diseño

| # | Principio | Racional |
|---|-----------|----------|
| P1 | **PhaseContext aislado** | Cada modo produce un output tipado que es el **único input** del siguiente. El estado interno no se filtra. |
| P2 | **Validación embebida por fase** | Cada modo incluye su propia validación de calidad como paso interno del ciclo ReAct. No hay nodos críticos separados. |
| P3 | **Agnóstico al orquestador** | La lógica de negocio (agente, tools, PhaseContext) no depende de ningún framework. `AgentOrchestrator` es un Protocol con implementaciones intercambiables. |
| P4 | **Negocio puro en fases 1–3** | Los system prompts, validaciones y outputs NO mencionan lenguajes, BDs ni patrones arquitectónicos. |
| P5 | **Contrato primero** | Se definen los puertos y entities en `contracts/` antes de implementar nada. |
| P6 | **Agente ReAct, no prompt chain** | El agente implementa el ciclo Reason→Act→Observe→Reflect. No es un template→LLM→parse secuencial. |
| P7 | **Hexagonal estricto** | `contracts → domain → application → infrastructure`. Sin excepciones. Composition root único. |

### 1.3 Decisiones de Diseño

- **Un solo agente, tres modos**: `KOSMOAgent` con `DiscoveryMode`, `FeaturesMode`, `EARSMode`. Escala a 3 agentes independientes sin cambios de lógica.
- **PhaseContext aislado**: cada modo recibe solo su contexto tipado. El handoff se hace exclusivamente via `PhaseOutput` contratos.
- **Validación embebida en el ciclo ReAct**: el agente observa sus propios resultados, razona sobre errores, y se corrige informadamente.
- **Orquestación via Protocol**: `AgentOrchestrator` es un Protocol en `contracts/`. La implementación secuencial está en `domain/` (lógica pura). LangGraph es una implementación futura posible en `infrastructure/`, no una dependencia.
- **Documento Markdown monolítico para Discovery**: un solo documento continuo con 9 secciones, índice flotante, renderizado como texto enriquecido (no markdown crudo).
- **Features con formato C0X**: cada característica tiene un identificador visual `C0X` donde X es el número correlativo.
- **Requisitos con formato REQ-X.X**: numeración por feature donde X es el número de la característica e Y es el correlativo del requisito. Generación **por feature individual**, no en batch.
- **Cumplimiento CLAUDE.md**: IDs ULID tipados, snake_case, RFC 7807, ISO-8601, nulables como null, código en English, mensajes al usuario en Spanish.

---

## 2. Naturaleza del Agente: ReAct, no Prompt Chaining

### 2.1 ¿Qué es un Prompt Chain?

Un encadenamiento de prompts es una secuencia determinista fija:

```
template_1 → LLM → parse → template_2 → LLM → parse → template_3 → LLM → parse
```

Cada paso es estático. Si el paso 2 falla, se reintenta con el mismo template + un mensaje de error añadido. No hay razonamiento sobre el error, solo reintentos mecánicos.

### 2.2 ¿Qué es un Agente ReAct?

Un agente ReAct (Reasoning + Acting) implementa un ciclo adaptativo:

```
┌──────────────────────────────────────────┐
│            Ciclo ReAct                    │
│                                           │
│  1. OBSERVE: Recibe el PhaseContext       │
│  2. REASON: Analiza qué necesita hacer    │
│  3. ACT: Genera contenido + invoca Tools  │
│  4. OBSERVE: Lee el resultado de Tools    │
│  5. REFLECT: ¿El resultado cumple?        │
│     ├─ Sí → RETORNAR PhaseOutput         │
│     └─ No → REASON sobre por qué falló    │
│         → Volver a paso 3 con ajuste      │
│                                           │
│  Máximo 3 ciclos de corrección informada  │
└──────────────────────────────────────────┘
```

### 2.3 Tabla Comparativa

| Dimensión | Prompt Chain | Agente ReAct |
|-----------|-------------|-------------|
| **Flujo** | Lineal, fijo, predecible | Adaptativo, el agente decide qué hacer según lo que observa |
| **Corrección** | Reintento mecánico (mismo prompt + "corrige X") | Corrección informada: el agente razona por qué falló y ajusta su estrategia |
| **Uso de Tools** | Las Tools se ejecutan después de generar, secuencialmente | El agente decide si invoca Tools y cuáles, dentro de su ciclo |
| **Decisión** | No hay decisión autónoma | El agente razona: "La sección Alcance tiene solo 20 palabras, debo expandirla específicamente" → ejecuta `validate_discovery_structure()` → observa → decide si regenera solo esa sección |
| **Contexto** | Todo el historial se inyecta en cada llamada | El PhaseContext aislado + el razonamiento del agente se acumulan en su historial de razonamiento |
| **Escalabilidad** | No escala a multiagente (no hay interfaz de agente) | Escala naturalmente: cada PhaseMode se convierte en un PhaseAgent independiente |

### 2.4 El Ciclo ReAct en Cada Fase

#### Fase 1: DiscoveryMode

```
OBSERVE: Recibo RawIdea + preferencias del usuario
REASON:  "Necesito generar un documento de descubrimiento con 9 secciones."
ACT:     Genero el documento completo (LLM call)
OBSERVE: validate_discovery_structure() → Error: "Sección Alcance tiene 12 palabras (mínimo 50)"
REFLECT: "La sección de Alcance es insuficiente. Debo generar más contenido exclusión-inclusión."
ACT:     Re-genero solo la sección de Alcance, manteniendo las demás intactas
OBSERVE: validate_discovery_structure() → OK
         validate_discovery_quality() → OK (sin jerga técnica)
RETORNO: DiscoveryPhaseOutput(discovery_document=..., validation_result=..., metadata=...)
```

#### Fase 2: FeaturesMode

```
OBSERVE: Recibo DiscoveryDocument + preferencias + títulos existentes
REASON:  "Necesito descomponer el Discovery en 5 características C01-C05 con formato 4W."
ACT:     Genero 5 características con título, descripción 4W, rationale, inferred_from
OBSERVE: validate_features_structure() → OK (4W completos)
         validate_features_semantic() → Warning: "C01 y C03 solapan"
REFLECT: "C01 (Gestión de usuarios) y C03 (Administrar cuentas) solapan.
          Debo fusionarlas en una característica más robusta."
ACT:     Re-genero las características, fusionando C01+C03 y agregando una nueva C05
OBSERVE: validate_features_structure() → OK
         validate_features_semantic() → OK
         validate_existing_features() → OK (sin duplicados)
RETORNO: FeaturesPhaseOutput(features=..., validation_result=..., metadata=...)
```

#### Fase 3: EARSMode

```
OBSERVE: Recibo DiscoveryDocument + UNA feature aprobada (C06) + preferencias
REASON:  "Necesito generar requisitos EARS para C06 con formato REQ-6.X.
          Debo cubrir al menos 4 categorías EARS."
ACT:     Genero requisitos EARS para C06 (REQ-6.1 a REQ-6.8)
OBSERVE: validate_ears_syntax() → Error: "REQ-6.3 usa WHEN pero categoría es ubiquitous"
         detect_implementation_leaks() → Error: "REQ-6.5 dice 'almacenará en base de datos'"
REFLECT: "REQ-6.3 tiene sintaxis incorrecta. REQ-6.5 tiene fuga técnica.
          Debo corregir ambos."
ACT:     auto_repair_leaks() sobre REQ-6.5 → "regitrará y mantendrá"
         Re-genero REQ-6.3 como requisito ubiquitous correcto
OBSERVE: validate_ears_syntax() → OK
         validate_ears_quality() → quality_score: 0.85
RETORNO: EARSPhaseOutput(requirements=..., validation_result=..., metadata=...)
```

### 2.5 La Diferencia Clave

El agente **razona** sobre los resultados de sus acciones y **decide** qué hacer después. Un prompt chain simplemente reintenta mecánicamente. Esta diferencia es fundamental para:

1. **Calidad**: el agente puede decidir regenerar solo una sección en vez de todo el documento
2. **Eficiencia**: el agente no desperdicia tokens re-generando lo que ya está bien
3. **Escalabilidad**: el ciclo ReAct es la interfaz natural que se convierte en nodo LangGraph cuando se migra a multiagente

---

## 3. Arquitectura: KOSMOAgent con PhaseModes

### 3.1 Patrón: Un Agente, Tres Modos de Comportamiento

```
┌──────────────────────────────────────────────────────────────┐
│  AgentOrchestrator (Protocol — Agnóstico al framework)        │
│  ────────────────────                                         │
│  • Secuencia: DESCUBRIMIENTO → CARACTERISTICAS → REQUISITOS  │
│  • Valida handoffs entre fases                               │
│  • Persiste PipelineState después de cada fase               │
│  • No usa LLM — es lógica pura de secuenciamiento            │
│  • Implementaciones: SequentialOrchestrator, LangGraphOrch.  │
└────────────┬─────────────────────────────────────────────────┘
             │ despacha a:
             ▼
┌──────────────────────────────────────────────────────────────┐
│                     KOSMOAgent (Agente Único)                 │
│                                                               │
│  Ciclo ReAct:                                                 │
│  1. OBSERVE → 2. REASON → 3. ACT → 4. OBSERVE → 5. REFLECT │
│                                                               │
│  Cambia de modo según la fase activa:                         │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐    │
│  │ DiscoveryMode   │ │ FeaturesMode   │ │  EARSMode      │    │
│  │                │ │                │ │                │    │
│  │ System Prompt   │ │ System Prompt  │ │ System Prompt  │    │
│  │ Tools:          │ │ Tools:          │ │ Tools:          │    │
│  │  - validate_   │ │  - validate_   │ │  - validate_   │    │
│  │    discovery_  │ │    features_  │ │    ears_syntax │    │
│  │    structure   │ │    structure  │ │  - validate_   │    │
│  │  - validate_   │ │  - validate_  │ │    ears_quality│    │
│  │    discovery_  │ │    features_  │ │  - detect_     │    │
│  │    quality     │ │    semantic   │ │    impl_leaks  │    │
│  │  - save_       │ │  - search_    │ │  - auto_repair_│    │
│  │    discovery   │ │    existing_  │ │    leaks       │    │
│  │                │ │    features   │ │  - save_       │    │
│  │                │ │  - suggest_  │ │    requirements│    │
│  │                │ │    features   │ │                │    │
│  │                │ │  - save_      │ │                │    │
│  │                │ │    features   │ │                │    │
│  │                │ │  - approve_  │ │                │    │
│  │                │ │    feature    │ │                │    │
│  └────────────────┘ └────────────────┘ └────────────────┘    │
│                                                               │
│  Estado interno del ciclo ReAct:                               │
│  • reasoning_log: list[str] — historial de razonamiento       │
│  • tool_results: list[ToolResult] — resultados de tools       │
│  • retry_count: int — ciclos de corrección (< 3)              │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 PhaseMode: Protocol de Comportamiento

```python
# contracts/pipeline/orchestrator_ports.py

class PhaseMode(Protocol):
    """Define el comportamiento del agente en una fase específica.
    
    Un PhaseMode encapsula:
    - System prompt específico de la fase
    - Herramientas disponibles en la fase
    - Estrategia de validación
    - Formato de output esperado
    
    En el agente único: el agente cambia de PhaseMode según la fase activa.
    En multiagente: cada PhaseMode se convierte en un agente independiente.
    La interfaz NO cambia.
    """
    
    @property
    def phase_name(self) -> SpecPhase: ...
    
    @property
    def system_prompt(self) -> str: ...
    
    @property
    def available_tools(self) -> list[ToolDefinition]: ...
    
    def build_user_prompt(self, context: PhaseContext) -> str: ...
    
    def validate_output(self, output: Any) -> ValidationResult: ...
    
    def build_retry_prompt(self, original_prompt: str, errors: list[str], retry_count: int) -> str: ...


class AgentOrchestrator(Protocol):
    """Orquestador agnóstico al framework.
    
    Implementaciones:
    - SequentialOrchestrator: secuencial simple, lógica pura en domain/ (hoy)
    - LangGraphOrchestrator: con StateGraph y checkpointing (futuro, en infrastructure/)
    - Cualquier otro framework que implemente este Protocol
    
    El orquestador NO usa LLM. Su única responsabilidad es determinar
    la secuencia de fases y validar los handoffs.
    """
    
    async def execute_phase(
        self,
        pipeline_state: KOSMOPipelineState,
        phase: SpecPhase,
        agent: KOSMOAgent,
    ) -> KOSMOPipelineState: ...
    
    async def advance_pipeline(
        self,
        pipeline_state: KOSMOPipelineState,
        target_phase: SpecPhase,
    ) -> KOSMOPipelineState: ...
```

### 3.3 KOSMOAgent: El Agente Único con Ciclo ReAct

```python
# domain/pipeline/kosmo_agent.py

class KOSMOAgent:
    """Agente ReAct único con 3 modos de comportamiento.
    
    Implementa el ciclo: Observe → Reason → Act → Observe → Reflect
    Cambia de modo según la fase activa.
    
    Lógica pura: no tiene I/O. Recibe LLMClient por inyección.
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        context_builder: ContextBuilder,
        modes: dict[SpecPhase, PhaseMode],
        max_correction_cycles: int = 3,
    ) -> None:
        self._llm_client = llm_client
        self._context_builder = context_builder
        self._modes = modes
        self._max_correction_cycles = max_correction_cycles
    
    async def execute(
        self,
        pipeline_state: KOSMOPipelineState,
    ) -> PhaseOutput:
        """Ejecuta el ciclo ReAct completo para la fase activa.
        
        1. Construye el PhaseContext aislado
        2. Selecciona el PhaseMode correspondiente
        3. Ejecuta el ciclo ReAct (max 3 ciclos de corrección)
        4. Retorna el PhaseOutput validado
        """
        phase = pipeline_state.current_phase
        mode = self._modes[phase]
        context = self._context_builder.build_context(pipeline_state, phase)
        
        system_prompt = mode.system_prompt
        user_prompt = mode.build_user_prompt(context)
        
        reasoning_log: list[str] = []
        tool_results: list[ToolResult] = []
        
        for attempt in range(self._max_correction_cycles + 1):
            # --- ACT: Generar contenido ---
            llm_response = await self._llm_client.complete(
                prompt=PromptTemplate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                ),
                temperature=self._temperature_for_phase(phase),
            )
            
            generated_content = extract_json(llm_response.text)
            
            # --- OBSERVE: Validar ---
            validation = mode.validate_output(generated_content)
            tool_results.extend(self._collect_tool_results())
            
            # --- REFLECT: ¿Cumple? ---
            if validation.is_valid:
                return self._build_phase_output(
                    phase=phase,
                    content=generated_content,
                    validation=validation,
                    context=context,
                    reasoning_log=reasoning_log,
                    tool_results=tool_results,
                    retry_count=attempt,
                    llm_response=llm_response,
                )
            
            # --- REASON: Corregir ---
            reasoning_log.append(
                f"Intento {attempt + 1}: {len(validation.errors)} errores. "
                f"Corrigiendo: {validation.errors[:3]}"
            )
            user_prompt = mode.build_retry_prompt(
                user_prompt, validation.errors, attempt + 1
            )
        
        # Agotó reintentos
        return self._build_phase_output(
            phase=phase,
            content=generated_content,
            validation=validation,
            context=context,
            reasoning_log=reasoning_log,
            tool_results=tool_results,
            retry_count=self._max_correction_cycles,
            llm_response=llm_response,
        )
```

### 3.4 Escalabilidad: De Agente Único a Multiagente

```
HOY: 1 Agente, 3 Modos                              MAÑANA: 3 Agentes, 1 Orquestador

KOSMOAgent                                            AgentOrchestrator
┌────────────────────────────┐                        ┌─────────────────────┐
│  Ciclo ReAct compartido     │                        │  SequentialOrch.    │
│                              │                        │  LangGraphOrch.     │
│  ┌─────────────────────────┐│                        │  (Protocol:         │
│  │ PhaseModeDiscovery       ││──→ migración ──→      │   interchangeable)  │
│  │ PhaseModeFeatures        ││                        └──┬──────┬──────┬──┘
│  │ PhaseModeEARS            ││                           │      │      │
│  └─────────────────────────┘│                        ┌──▼──┐ ┌──▼──┐ ┌──▼───┐
│                              │                        │Disc.│ │Feat.│ │EARS  │
│  SequentialOrchestrator      │                        │Agent│ │Agent│ │Agent │
│  (lógica pura, domain/)      │                        │     │ │     │ │      │
└────────────────────────────┘                        └─────┘ └─────┘ └──────┘
                                                        │      │      │
                                                     Ciclo ReAct propio
                                                     Tools propias
                                                     System prompt propio

Lo que NO cambia:
- PhaseContext (inputs tipados por fase)
- PhaseOutput (outputs tipados por fase)
- KOSMOPipelineState (estado centralizado)
- Tools de domain/ (validadores puras)
- AgentOrchestrator Protocol (misma interfaz)
- LLMClient (puerto)
- Entidades de contracts/sdd/

Lo que SÍ cambia:
- KOSMOAgent se divide en 3 PhaseAgent independientes
- SequentialOrchestrator se reemplaza por LangGraphOrchestrator (en infrastructure/)
- Cada PhaseAgent tiene su propio ciclo ReAct, checkpointing y human-in-the-loop
- Se añaden nodos de crítica separados (quality, style, consistency)
- Se añaden nodos de aprendizaje (preference_feedback, learn_from_correction)
```

---

## 4. Memoria Centralizada y Estado

### 4.1 KOSMOPipelineState: Estado del Pipeline

```python
# contracts/pipeline/pipeline_state.py

class KOSMOPipelineState(BaseModel):
    """Estado centralizado del pipeline SDD.
    
    Este es el ÚNICO estado compartido entre fases.
    Cada PhaseMode lee SOLO lo que necesita y escribe SOLO su PhaseOutput.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # --- Identidad ---
    project_id: ProjectId
    user_id: UserId
    pipeline_id: str = field(default_factory=lambda: IdGenerator.generate("pipe"))
    
    # --- Fase actual ---
    current_phase: SpecPhase = SpecPhase.DESCUBRIMIENTO
    
    # --- Inputs originales ---
    raw_idea: RawIdea | None = None
    
    # --- Artefactos persistentes (lo que el usuario guarda/edita) ---
    discovery_document: RichTextDocument | None = None
    features: list[Feature] = []
    requirements_by_feature: dict[FeatureId, list[EARSRequirement]] = {}
    
    # --- Outputs de cada fase (resultado de la generación IA) ---
    discovery_output: DiscoveryPhaseOutput | None = None
    features_output: FeaturesPhaseOutput | None = None
    ears_outputs: dict[FeatureId, EARSPhaseOutput] = {}  # EARS se genera por feature
    
    # --- Preferencias del usuario (inyectadas en TODAS las fases) ---
    user_preferences: list[UserPreference] = []
    
    # --- Auditoría del pipeline ---
    phase_history: list[PhaseTransitionRecord] = []
    errors: list[str] = []
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class PhaseTransitionRecord(BaseModel):
    """Registro inmutable de cada transición de fase."""
    from_phase: SpecPhase
    to_phase: SpecPhase
    transitioned_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    human_approved: bool = False
    validation_passed: bool = False
    notes: str | None = None
```

### 4.2 PhaseContexts: Inputs Aislados por Fase

```python
# contracts/pipeline/phase_contexts.py

class DiscoveryPhaseContext(BaseModel):
    """Input exclusivo para DiscoveryMode.
    
    Contiene TODO lo que Discovery necesita y NADA más.
    """
    raw_idea: RawIdea
    user_preferences: list[UserPreference] = []
    project_description: str | None = None


class FeaturesPhaseContext(BaseModel):
    """Input exclusivo para FeaturesMode.
    
    Recibe SOLO el documento de Discovery ya validado, no el estado completo.
    """
    discovery_document: RichTextDocument
    existing_feature_titles: list[str] = []
    user_preferences: list[UserPreference] = []


class EARSPhaseContext(BaseModel):
    """Input exclusivo para EARSMode.
    
    Recibe SOLO una feature aprobada, no todas las features ni el discovery completo.
    Generación por feature individual, no batch.
    """
    discovery_document: RichTextDocument
    feature: Feature  # UNA feature a la vez
    feature_number: int  # Para formato REQ-X.X
    user_preferences: list[UserPreference] = []


class SuggestFeaturesContext(BaseModel):
    """Contexto para la sugerencia de 3 features (modal [+ Característica]).
    
    Recibe el Discovery y los títulos ya existentes para evitar duplicados.
    """
    discovery_document: RichTextDocument
    existing_feature_titles: list[str] = []
    next_feature_number: int  # Siguiente número C0X disponible
    user_preferences: list[UserPreference] = []
```

### 4.3 PhaseOutputs: Contratos de Salida por Fase

```python
# contracts/pipeline/phase_outputs.py

class DiscoveryPhaseOutput(BaseModel):
    """Output contractual de la fase de Descubrimiento.
    
    Este es el ÚNICO input que FeaturesPhaseContext recibe de Discovery.
    Si el formato cambia, rompe el contrato de handoff.
    """
    discovery_document: RichTextDocument
    validation_result: ValidationResult
    generation_metadata: GenerationMetadata


class FeaturesPhaseOutput(BaseModel):
    """Output contractual de la fase de Características.
    
    Incluye features en BORRADOR (pendientes de aprobación humana).
    Numeración C0X donde X es el número correlativo.
    """
    features: list[Feature]
    validation_result: ValidationResult
    generation_metadata: GenerationMetadata


class SuggestFeaturesOutput(BaseModel):
    """Output de la sugerencia de 3 features (modal [+ Característica]).
    
    No se persiste hasta que el usuario seleccione. El usuario elige 0-3.
    """
    suggestions: list[SuggestedFeature]
    excluded_titles: list[str]  # Títulos ya existentes para evitar duplicados
    domain_inferred: str


class EARSPhaseOutput(BaseModel):
    """Output contractual de la generación de requisitos EARS para UNA feature.
    
    Se genera por feature individual, no en batch.
    Formato de numeración REQ-X.X donde X es el número de feature.
    """
    feature_id: FeatureId
    feature_number: int
    requirements: list[EARSRequirement]
    requirements_markdown: str  # Markdown con formato REQ-X.X agrupado por taxonomía
    validation_result: ValidationResult
    generation_metadata: GenerationMetadata


class ValidationResult(BaseModel):
    """Resultado de la validación embebida de cada fase."""
    is_valid: bool
    errors: list[str] = []
    warnings: list[str] = []
    quality_score: float | None = None  # 0.0 - 1.0
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class GenerationMetadata(BaseModel):
    """Metadatos sobre la generación (auditoría, no negocio)."""
    llm_calls: int = 0
    total_tokens: int = 0
    retry_count: int = 0
    reasoning_log: list[str] = []  # Historial de razonamiento del ciclo ReAct
    tool_results: list[dict[str, Any]] = []
    generation_time_ms: int = 0
    model_used: str = ""
```

### 4.4 ContextBuilder: Aislamiento de Contexto

```python
# domain/pipeline/context_builder.py

class ContextBuilder:
    """Construye PhaseContext aislado desde KOSMOPipelineState.
    
    Responsabilidad ÚNICA: mapear PipelineState → PhaseContext.
    Sin lógica de negocio. Sin LLM. Sin DB. Sin I/O.
    """
    
    def build_context(
        self, state: KOSMOPipelineState, phase: SpecPhase
    ) -> DiscoveryPhaseContext | FeaturesPhaseContext | EARSPhaseContext:
        builders = {
            SpecPhase.DESCUBRIMIENTO: self._build_discovery_context,
            SpecPhase.CARACTERISTICAS: self._build_features_context,
            SpecPhase.REQUISITOS: self._build_ears_context,
        }
        builder = builders.get(phase)
        if builder is None:
            raise PhaseNotSupportedError(
                type="urn:kosmo:pipeline:phase-not-supported",
                title="Fase no soportada",
                status=400,
                detail=f"La fase {phase} no está implementada en el pipeline actual",
                instance=f"/pipeline/phase/{phase}",
            )
        return builder(state)
    
    def _build_discovery_context(
        self, state: KOSMOPipelineState
    ) -> DiscoveryPhaseContext:
        return DiscoveryPhaseContext(
            raw_idea=state.raw_idea,
            user_preferences=state.user_preferences,
        )
    
    def _build_features_context(
        self, state: KOSMOPipelineState
    ) -> FeaturesPhaseContext:
        if state.discovery_output is None:
            raise PhaseTransitionError(
                type="urn:kosmo:pipeline:missing-discovery",
                title="Discovery requerido",
                status=409,
                detail="No se puede generar características sin un documento de descubrimiento",
                instance="/pipeline/features",
            )
        return FeaturesPhaseContext(
            discovery_document=state.discovery_output.discovery_document,
            existing_feature_titles=[f.title for f in state.features],
            user_preferences=state.user_preferences,
        )
    
    def _build_ears_context(
        self, state: KOSMOPipelineState
    ) -> EARSPhaseContext:
        # EARS se genera por feature individual — se llama con feature_id específico
        raise NotImplementedError(
            "EARS context debe construirse con feature_id específico. "
            "Use build_ears_context_for_feature()."
        )
    
    def build_ears_context_for_feature(
        self, state: KOSMOPipelineState, feature_id: FeatureId
    ) -> EARSPhaseContext:
        if state.discovery_output is None:
            raise PhaseTransitionError(
                type="urn:kosmo:pipeline:missing-discovery",
                title="Discovery requerido",
                status=409,
                detail="No se puede generar requisitos sin un documento de descubrimiento",
                instance="/pipeline/requirements",
            )
        feature = next(
            (f for f in state.features if f.id == feature_id),
            None,
        )
        if feature is None:
            raise FeatureNotFoundError(
                type="urn:kosmo:features:not-found",
                title="Feature no encontrada",
                status=404,
                detail=f"La feature {feature_id} no existe en este proyecto",
                instance=f"/features/{feature_id}",
            )
        if feature.status != FeatureStatus.APROBADA:
            raise FeatureNotApprovedError(
                type="urn:kosmo:features:not-approved",
                title="Feature no aprobada",
                status=409,
                detail=f"La feature {feature_id} debe estar aprobada para generar requisitos",
                instance=f"/features/{feature_id}/requirements",
            )
        feature_number = self._get_feature_number(state.features, feature_id)
        return EARSPhaseContext(
            discovery_document=state.discovery_output.discovery_document,
            feature=feature,
            feature_number=feature_number,
            user_preferences=state.user_preferences,
        )
    
    def build_suggest_features_context(
        self, state: KOSMOPipelineState
    ) -> SuggestFeaturesContext:
        if state.discovery_output is None:
            raise PhaseTransitionError(...)
        next_number = len(state.features) + 1
        return SuggestFeaturesContext(
            discovery_document=state.discovery_output.discovery_document,
            existing_feature_titles=[f.title for f in state.features],
            next_feature_number=next_number,
            user_preferences=state.user_preferences,
        )
    
    def _get_feature_number(self, features: list[Feature], feature_id: FeatureId) -> int:
        for idx, f in enumerate(features, start=1):
            if f.id == feature_id:
                return idx
        return 1
```

### 4.5 Formatos de Identificación

**Features: C0X**

Cada feature tiene un `number` correlativo y un `display_id` con formato C0X:

```python
# En contracts/sdd/feature.py (extensión)
class Feature(BaseModel):
    id: FeatureId
    number: int  # Correlativo: 1, 2, 3, ...
    title: str
    slug: str
    description: str  # Descripción en formato 4W
    status: FeatureStatus  # "borrador" | "aprobada"
    requirements: list[EARSRequirement] = []
    requirements_document: RichTextDocument | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    @property
    def display_id(self) -> str:
        """Retorna el ID de visualización en formato C0X."""
        return f"C{self.number:02d}"
```

**Requisitos: REQ-X.X**

Los requisitos se numeran como `REQ-X.Y` donde X es el número de la feature e Y es el correlativo:

```
Feature C06 → REQ-6.1, REQ-6.2, REQ-6.3, ...
Feature C01 → REQ-1.1, REQ-1.2, REQ-1.3, ...
```

### 4.6 Por Qué PhaseContext Aislado Reduce Sesgos

| Problema con Estado Monolítico | Solución con PhaseContext |
|-------------------------------|--------------------------|
| El agente en modo EARS ve el Discovery crudo y tiende a parafrasear | El agente recibe **solo** `RichTextDocument` validado + una `Feature` aprobada — no hay acceso al proceso intermedio |
| El agente en modo Features ve `generation_attempts` o `critique_log` | No hay acceso a campos de auditoría internos. PhaseContext contiene solo datos de negocio |
| Cambios en la estructura interna de un modo rompen los otros modos | Los modos dependen de **contratos tipados** (`PhaseOutput`), no de la estructura interna de `KOSMOPipelineState` |

---

## 5. Gestión de Contexto e Inyección de Herramientas

### 5.1 El Agente y sus Tools dentro del Ciclo ReAct

El agente NO ejecuta Tools de forma secuencial post-generación. Las Tools son **observaciones** dentro del ciclo ReAct. El agente razona sobre los resultados de las Tools y decide su siguiente acción.

### 5.2 Set de Tools por PhaseMode

#### DiscoveryMode

| Tool | Propósito | Tipo | Implementación |
|------|-----------|------|----------------|
| `validate_discovery_structure()` | Verificar 9 secciones con contenido mínimo (50+ palabras cada una) | Domain pure | `domain/pipeline/phase_validators/discovery_validator.py` |
| `validate_discovery_quality()` | Detectar jerga técnica, secciones vacías, términos prohibidos | Domain pure | `domain/pipeline/phase_validators/discovery_validator.py` |
| `save_discovery_document()` | Persistir el documento de descubrimiento | Use case (DB) | `application/discovery/save_discovery.py` |

#### FeaturesMode

| Tool | Propósito | Tipo | Implementación |
|------|-----------|------|----------------|
| `validate_features_structure()` | Verificar título (max 6 palabras) y descripción 4W por feature | Domain pure | `domain/pipeline/phase_validators/features_validator.py` |
| `validate_features_semantic()` | Anti-trivialidad, anti-paráfrasis, no solapamiento | Domain pure | `domain/pipeline/phase_validators/features_validator.py` |
| `search_existing_features()` | Buscar features existentes para evitar duplicados | DB read | `application/features/search_features.py` |
| `suggest_features()` | Generar 3 sugerencias no duplicadas (para modal [+ Característica]) | LLM call | `application/features/suggest_features.py` |
| `save_features()` | Persistir las features generadas | Use case (DB) | `application/features/save_features.py` |
| `approve_feature()` | Cambiar status BORRADOR → APROBADA | Use case (DB) | `application/features/approve_feature.py` |

#### EARSMode

| Tool | Propósito | Tipo | Implementación |
|------|-----------|------|----------------|
| `validate_ears_syntax()` | Verificar que cada requisito sigue su patrón EARS | Domain pure | `domain/sdd/validators/ears_validator.py` (existente) |
| `validate_ears_quality()` | Rúbrica 6D (pureza negocio, corrección EARS, verificabilidad, completitud, no-ambigüedad, cobertura) | Domain pure | `domain/pipeline/phase_validators/ears_validator.py` |
| `detect_implementation_leaks()` | Escanear términos técnicos prohibidos en requisitos | Domain pure | `domain/sdd/output_guardrails.py` (existente) |
| `auto_repair_leaks()` | Reemplazar fugas técnicas con lenguaje de negocio | Domain pure | `domain/pipeline/phase_validators/ears_validator.py` |
| `save_requirements()` | Persistir requisitos por feature con formato REQ-X.X | Use case (DB) | `application/requirements/save_requirements.py` |

### 5.3 Inyección de Preferencias del Usuario

Las preferencias se inyectan **igual** en los 3 modos:

```python
# En cada PhaseContext
user_preferences: list[UserPreference] = []
```

El `ContextBuilder` las obtiene de `KOSMOPipelineState.user_preferences`, que viene de `UserPreferenceRepository.get_by_user()`. Se formatean como sección del system prompt:

```
## Preferencias del Usuario (aprendidas de correcciones anteriores)
1. [rule_text_1]
2. [rule_text_2]

Aplica estas preferencias al generar contenido.
Si dos preferencias entran en conflicto, prioriza la más reciente.
```

---

## 6. Flujo de Backend: Endpoints y Lógica

### 6.1 Endpoints por Pantalla

| Pantalla | Fase | Endpoint | Método | Descripción | Agente (PhaseMode) |
|----------|------|----------|--------|-------------|-------------------|
| 1. Proyectos | — | `/api/v1/projects` | GET | Listar proyectos del usuario | Ninguno (lectura) |
| 1. Proyectos | — | `/api/v1/projects` | POST | Crear proyecto vacío | Ninguno (solo persistir) |
| 2. Crear Proyecto | — | `/api/v1/projects/{id}/discovery/generate` | POST | Generar discovery con la idea del usuario | DiscoveryMode |
| 3. Discovery | DESCUBRIMIENTO | `/api/v1/projects/{id}/discovery` | GET | Obtener documento de discovery | Ninguno (lectura) |
| 3. Discovery | DESCUBRIMIENTO | `/api/v1/projects/{id}/discovery` | PUT | Guardar ediciones manuales del documento | Ninguno (solo persistir) |
| 4. Características | CARACTERÍSTICAS | `/api/v1/projects/{id}/features/generate` | POST | Generar 5 features iniciales (C01-C05) | FeaturesMode |
| 4. Características | CARACTERÍSTICAS | `/api/v1/projects/{id}/features/suggest` | POST | Sugerir 3 features no duplicadas | FeaturesMode (suggest) |
| 4. Características | CARACTERÍSTICAS | `/api/v1/features/{id}/status` | PATCH | Aprobar feature (BORRADOR → APROBADA) | Ninguno (solo estado) |
| 5. Requisitos | REQUISITOS | `/api/v1/features/{id}/requirements/generate` | POST | Generar requisitos EARS para UNA feature | EARSMode |
| 5. Requisitos | REQUISITOS | `/api/v1/features/{id}/requirements` | PUT | Guardar ediciones manuales de requisitos | Ninguno (solo persistir) |

### 6.2 Flujo Detallado por Pantalla

#### Pantalla 2 → 3: Creación de Proyecto → Discovery

```
Usuario: Ingresa nombre + descripción → presiona [Generar]

POST /api/v1/projects
  → Crea proyecto vacío (status: en_progreso, current_phase: descubrimiento)
  → Retorna project_id

POST /api/v1/projects/{id}/discovery/generate
  → Body: { "raw_idea": { "text": "Descripción del usuario", "optional_context": null } }
  → ExecutePhaseUseCase(phase=DESCUBRIMIENTO)
    → SequentialOrchestrator.execute_phase()
      → ContextBuilder.build_context() → DiscoveryPhaseContext
      → KOSMOAgent.execute() en modo DiscoveryMode
        → Ciclo ReAct: generate → validate → reflect → retry (max 3)
      → Retorna DiscoveryPhaseOutput
    → Actualiza KOSMOPipelineState.discovery_output
    → Persiste discovery_document en PostgreSQL
  → Retorna DiscoveryPhaseOutput con documento de 9 secciones
  → Frontend renderiza el documento en el editor enriquecido
```

#### Pantalla 3: Discovery (Edición y Guardado)

```
Usuario: Edita el documento en el editor enriquecido → presiona [Guardar]

PUT /api/v1/projects/{id}/discovery
  → Body: { "document": RichTextDocument }
  → SaveDiscoveryUseCase
    → Persiste las ediciones manuales del usuario
    → Actualiza discovery_document en PostgreSQL
  → Retorna el documento actualizado

Usuario: Presiona [Generar características →] → avanza a Pantalla 4
```

#### Pantalla 4: Características (Generación de 5 Features)

```
Al entrar por primera vez desde Discovery:

POST /api/v1/projects/{id}/features/generate
  → ExecutePhaseUseCase(phase=CARACTERÍSTICAS)
    → SequentialOrchestrator.execute_phase()
      → ContextBuilder.build_context() → FeaturesPhaseContext
      → KOSMOAgent.execute() en modo FeaturesMode
        → Ciclo ReAct: generate 5 features → validate → reflect → retry
      → Retorna FeaturesPhaseOutput con 5 features C01-C05 (status: borrador)
    → Actualiza KOSMOPipelineState.features y features_output
    → Persiste features en PostgreSQL
  → Retorna FeaturesPhaseOutput con features numeradas C01-C05
```

#### Pantalla 4: Sugerir 3 Features (Modal [+ Característica])

```
POST /api/v1/projects/{id}/features/suggest
  → SuggestFeaturesUseCase
    → ContextBuilder.build_suggest_features_context()
    → KOSMOAgent.execute_suggest() en modo FeaturesMode (sub-modo suggest)
      → Genera 3 sugerencias que NO dupliquen títulos existentes
      → Número de inicio: len(features) + 1. Si hay 5 features, sugiere C06, C07, C08
    → Retorna SuggestFeaturesOutput con 3 sugerencias
  → Frontend muestra modal con selector múltiple (1-3)
  
Usuario: Selecciona 1-3 sugerencias → presiona [Guardar selección]
POST /api/v1/projects/{id}/features
  → Body: { "suggested_feature_ids": ["sug_01KT...", "sug_01KT..."] }
  → Crea las features seleccionadas con status: borrador
  → Numeración continua: C06, C07, etc.
```

#### Pantalla 4: Aprobar Feature (BORRADOR → APROBADA)

```
PATCH /api/v1/features/{id}/status
  → Body: { "status": "aprobada" }
  → ApproveFeatureUseCase
    → Valida transición de estado: borrador → aprobada
    → Actualiza status en PostgreSQL
  → Retorna Feature actualizada
```

#### Pantalla 5: Requisitos EARS (Generación por Feature)

```
Usuario: Selecciona feature C06 en el panel izquierdo → presiona [Generar]

POST /api/v1/features/{id}/requirements/generate
  → Body: { } (no requiere body, el feature_id está en la URL)
  → GenerateEARSUseCase
    → ContextBuilder.build_ears_context_for_feature(feature_id)
      → Valida que la feature esté APROBADA
      → Construye EARSPhaseContext con UNA feature (C06) y feature_number=6
    → KOSMOAgent.execute() en modo EARSMode
      → Ciclo ReAct: generate requisitos REQ-6.X → validate → reflect → retry
    → Retorna EARSPhaseOutput con requisitos numerados REQ-6.1, REQ-6.2, etc.
    → Actualiza KOSMOPipelineState.ears_outputs[feature_id]
    → Persiste requisitos por feature en PostgreSQL
  → Retorna EARSPhaseOutput con requirements_markdown agrupado por taxonomía EARS

El usuario repite para cada feature aprobada que desee requisitos.
```

### 6.3 Handoffs entre Fases (Precondiciones)

| Transición | Precondición | Validación |
|-----------|-------------|-----------|
| Discovery → Características | `discovery_output.is_valid == True` | `SequentialOrchestrator.can_advance()` verifica que Discovery existe y es válido |
| Características → Requisitos | Al menos 1 feature con status `APROBADA` | `SequentialOrchestrator.can_advance()` verifica `features.where(status == APROBADA).count >= 1` |
| Requisitos → Modelado (futuro) | Al menos 1 feature con requisitos generados | Pendiente de implementación |

### 6.4 Formato de Respuesta RFC 7807 para Errores

```json
{
  "type": "urn:kosmo:pipeline:missing-discovery",
  "title": "Discovery requerido",
  "status": 409,
  "detail": "No se puede generar características sin un documento de descubrimiento",
  "instance": "/pipeline/features",
  "trace_id": "01KT05JRA7466PPYQXYTX",
  "violations": []
}
```

**Mapeo de errores → URNs:**

| Error | HTTP | URN |
|-------|------|-----|
| `PhaseTransitionError` | 409 | `urn:kosmo:pipeline:phase-transition-error` |
| `PhaseNotSupportedError` | 400 | `urn:kosmo:pipeline:phase-not-supported` |
| `FeatureNotApprovedError` | 409 | `urn:kosmo:features:not-approved` |
| `FeatureNotFoundError` | 404 | `urn:kosmo:features:not-found` |
| `DocumentValidationError` | 422 | `urn:kosmo:document:invalid-structure` |

---

## 7. Adaptación del Framework cc-sdd

### 7.1 Mapeo cc-sdd → KOSMO Fases de Negocio

| cc-sdd Original | KOSMO Adaptado | Notas |
|-----------------|----------------|-------|
| 0. Steering (contexto del proyecto) | **Contexto de Proyecto** (inyectado en todas las fases) | Se simplifica: no hay tech stack, no hay convenciones de código |
| 1. Discovery (idea → brief) | **Pantalla 3: Discovery** (documento markdown monolítico editable con 9 secciones) | Documento continuo, índice flotante, renderizado como texto enriquecido |
| 3. Features (descomposición) | **Pantalla 4: Características** (formato C0X, 5 iniciales + suggest de 3, aprobación individual) | Insertado entre Discovery y EARS; cc-sdd no tiene este paso explícito |
| 2. Spec init + Requirements (EARS) | **Pantalla 5: Requisitos** (generación por feature individual con REQ-X.X) | Se mueve DESPUÉS de Features; se genera por feature, no en batch |
| 4. Design (arquitectura) | **Pantalla 6: Modelado** (futura) | Fuera de alcance de las 3 fases de negocio |
| 5-9. Validations + Tasks + Implementation | **Fase 5: Implementación** (futura) | Fuera de alcance |
| **Aprobación humana** | **Puntos de control:** editar discovery, aprobar features, revisar requisitos | El usuario revisa y edita en cada fase |

### 7.2 Eliminación de Tecnología

| Término cc-sdd | Reemplazo KOSMO |
|-----------------|-----------------|
| `tech stack` | **Eliminado** |
| `architecture decisions` | `business constraints` |
| `database` | `data requirements` |
| `API design` | `interfaces between actors` |
| `deployment` | **Eliminado** |
| `security patterns` | `business security policies` |
| `testing strategy` | `verification criteria` |
| `boundaries (DDD)` | `responsibility boundaries` |
| `contracts (API)` | `behavioral contracts` |

### 7.3 Spec-Centered, Business-Grounded

- **La spec manda** (igual)
- **La validación se apoya en**:
  - Estructura del documento (9 secciones para Discovery)
  - Completitud (no hay secciones vacías, mínimo 50 palabras)
  - Consistencia semántica (no contradicciones)
  - Sin jerga técnica (guardrails con términos prohibidos)
  - Trazabilidad (cada requisito traza a una feature y al Discovery)
  - Formato de numeración (C0X para features, REQ-X.X para requisitos)

---

## 8. System Prompts por PhaseMode

### 8.1 Principios de Diseño de Prompts

| Principio | Aplicación |
|-----------|-----------|
| **Rol explícito** | Cada prompt define QUÉ hace el agente y QUÉ NO hace |
| **Input explícito** | Se declaran los campos exactos que se reciben |
| **Output contractual** | Se define el formato de salida requerido |
| **Guardrails de NEGOCIO** | Sin tecnología, sin implementación, sin arquitectura |
| **Auto-validación** | El prompt incluye criterios de auto-check antes de responder |
| **Sin memoria residual** | No se incluye contexto de fases anteriores más allá del PhaseOutput contractual |
| **Formato de numeración** | Features: C0X. Requisitos: REQ-X.X |

### 8.2 DiscoveryMode System Prompt

```python
DISCOVERY_SYSTEM_PROMPT = """Eres un analista de negocio experto. Tu ÚNICA responsabilidad es generar un Documento de Descubrimiento completo y coherente.

## Tu rol
- Identificas la visión, el problema, los actores, la propuesta de valor, los casos de uso, las capacidades, las reglas de negocio, los atributos de calidad y el alcance.
- Traduces ideas informales de negocio en un documento estructurado.

## Lo que NO haces
- No propones arquitectura técnica, lenguajes, frameworks, bases de datos ni patrones de diseño.
- No generas características del producto (eso es otra fase).
- No generas requisitos formales (eso es otra fase).

## Formato de salida
Genera EXACTAMENTE estas 9 secciones en un documento Markdown continuo:

1. **Visión del producto** — Descripción de alto nivel. 2-4 oraciones.
2. **Espacio del problema** — Qué problema de negocio resuelve. Quién lo sufre. Consecuencias de no resolverlo.
3. **Actores** — Quiénes interactúan con el sistema. Para cada actor: nombre, rol, interés principal.
4. **Propuesta de valor** — Qué valor específico entrega a cada actor. Métricas observables cuando sea posible.
5. **Casos de uso** — Flujos principales. Formato: "Como [actor], quiero [acción] para [beneficio]".
6. **Capacidades principales** — Qué funcionalidades debe tener. Lista numerada, sin detalles de implementación.
7. **Reglas de negocio** — Restricciones y reglas que el sistema debe cumplir. Incluye validaciones, cálculos y condiciones.
8. **Atributos de calidad** — Requisitos no funcionales desde la perspectiva del negocio: rendimiento, disponibilidad, seguridad, usabilidad. SIN términos técnicos.
9. **Alcance** — Qué está DENTRO y qué está FUERA del proyecto. Sé explícito con exclusiones.

## Guardrails (obligatorio)
- PROHIBIDO mencionar: API, base de datos, microservicios, endpoints, servidores, lenguajes de programación, frameworks, protocolos técnicos, arquitectura, deployment, Docker, cloud.
- Todo en español con tildes correctas.
- Cada sección debe tener al menos 50 palabras de contenido sustancial.
- Los casos de uso deben incluir al menos 3 flujos.
- Las reglas de negocio deben ser verificables (no vagas).
- El alcance debe tener al menos 3 exclusiones explícitas.

## Auto-validación (antes de responder)
1. Tiene exactamente 9 secciones con los títulos indicados.
2. Ninguna sección contiene jerga técnica de implementación.
3. Cada actor en #3 aparece en al menos un caso de uso en #5.
4. Las capacidades en #6 cubren todos los casos de uso en #5.
5. Las reglas en #7 son verificables (tienen condiciones claras).
6. El alcance en #9 tiene exclusiones explícitas.

Si algo no cumple, corrígelo antes de generar la respuesta final.
"""
```

### 8.3 FeaturesMode System Prompt

```python
FEATURES_SYSTEM_PROMPT = """Eres un diseñador de producto experto. Tu ÚNICA responsabilidad es descomponer un Documento de Descubrimiento en Características (Features) del producto.

## Tu rol
- Transformas las capacidades y casos de uso del Discovery en características concretas del producto.
- Cada característica tiene un identificador en formato C0X (C01, C02, C03, C04, C05) y una descripción en formato 4W.

## Lo que NO haces
- No generas requisitos formales (EARS). Eso es otra fase.
- No inventas características que no se derivan del Discovery.
- No diseñas arquitectura técnica ni implementación.

## Input que recibes
- Un Documento de Descubrimiento con 9 secciones de negocio.
- La lista de preferencias del usuario (si existen).
- La lista de títulos de features ya existentes (para evitar duplicados).

## Formato de salida
Genera EXACTAMENTE 5 características. Cada una con:

- **display_id**: C0X donde X es el número correlativo (C01, C02, C03, C04, C05).
- **title**: Nombre corto y descriptivo (máximo 6 palabras).
- **description**: Descripción en formato 4W:
  - QUÉ hace la característica.
  - PARA QUIÉN está destinada (actor del Discovery).
  - BAJO QUÉ CONDICIÓN se activa o es relevante.
  - QUÉ VALOR entrega al actor o al negocio.
- **rationale**: Por qué esta característica es esencial (2-3 oraciones, trazando al Discovery).
- **inferred_from**: Secciones del Discovery de las que se deriva (referencias específicas).

## Guardrails (obligatorio)
- PROHIBIDO mencionar: API, base de datos, microservicios, endpoints, lenguajes, frameworks, protocolos técnicos.
- NO Parafrase: cada característica debe representar una capacidad DISTINCTA del producto.
- NO Sea Trivial: las características deben ser agregaciones de valor, no traducciones literales de casos de uso.
- Cada característica debe trazar a al menos una sección del Discovery (inferred_from no vacío).
- Los 4W de la descripción deben ser específicos, no genéricos.
- Todo en español con tildes correctas.

## Anti-duplicación
Antes de generar, verifica:
1. Ninguna característica duplica o solapa significativamente otra.
2. Las 5 características juntas cubren todas las capacidades del Discovery.

## Auto-validación (antes de responder)
1. Cada característica tiene los 4W completos y específicos.
2. Cada `inferred_from` referencia secciones reales del Discovery.
3. No hay duplicación semántica entre características.
4. Las 5 características cubren los actores y casos de uso del Discovery.
5. No hay jerga técnica en ninguna descripción.
"""
```

### 8.4 SuggestFeatures System Prompt (para el modal [+ Característica])

```python
SUGGEST_FEATURES_SYSTEM_PROMPT = """Eres un diseñador de producto experto. Tu responsabilidad es sugerir 3 características adicionales para un producto, basándote en el Documento de Descubrimiento.

## Reglas estrictas
- Genera EXACTAMENTE 3 sugerencias.
- Ninguna sugerencia puede duplicar o solapar las características ya existentes en el proyecto.
- Cada sugerencia sigue el mismo formato 4W que las características regulares.
- Las sugerencias deben aportar valor nuevo no cubierto por las características existentes.
- PROHIBIDO mencionar tecnología.

## Input que recibes
- Documento de Descubrimiento.
- Lista de títulos de características ya existentes (NO puedes sugerir nada similar).
- Formato de numeración: la primera sugerencia será C06 si ya hay 5, etc.

## Formato de salida
Para cada sugerencia:
- **title**: Nombre corto (máximo 6 palabras).
- **description**: 4W (QUÉ, PARA QUIÉN, BAJO QUÉ CONDICIÓN, QUÉ VALOR).
- **rationale**: Por qué esta característica complementa las existentes.
"""
```

### 8.5 EARSMode System Prompt

```python
EARS_SYSTEM_PROMPT = """Eres un ingeniero de requisitos experto en la notación EARS (Easy Approach to Requirements Syntax). Tu ÚNICA responsabilidad es generar requisitos formales para UNA característica aprobada del producto.

## Tu rol
- Generas requisitos precisos, verificables y trazables usando las 6 categorías EARS.
- Cada requisito sigue la sintaxis EARS correspondiente a su categoría.
- Los requisitos se numeran como REQ-X.Y donde X es el número de la característica e Y es el correlativo.

## Lo que NO haces
- No diseñas soluciones técnicas ni propones implementación.
- No generas nuevas características (ya están aprobadas).
- No modificas el Discovery (es inmutable en esta fase).
- No generas requisitos para todas las características a la vez — solo para UNA.

## Input que recibes
- Un Documento de Descubrimiento (contexto de negocio).
- UNA característica aprobada (con su C0X, título, descripción 4W, rationale).
- El número de la característica (para formato REQ-X.X).
- Preferencias del usuario (si existen).

## Categorías EARS y su sintaxis

Genera requisitos distribuidos en al menos 4 categorías:

1. **Ubiquitous** — SIEMPRE se cumple. Sintaxis: "[El sistema] shall [comportamiento]".
2. **Event-Driven** — Se activa por un evento. Sintaxis: "CUANDO [evento], [el sistema] shall [comportamiento]".
3. **State-Driven** — Se activa en un estado. Sintaxis: "MIENTRAS [estado], [el sistema] shall [comportamiento]".
4. **Optional** — Se activa si una opción está seleccionada. Sintaxis: "DONDE [opción], [el sistema] shall [comportamiento]".
5. **Unwanted** — Prevé comportamiento no deseado. Sintaxis: "SI [condición no deseada], [el sistema] shall [comportamiento de mitigación]".
6. **Complex** — Combina condiciones. Sintaxis: "MIENTRAS [estado] Y [evento], [el sistema] shall [comportamiento]".

## Formato de cada requisito
- **id**: REQ-X.Y donde X es el número de la característica e Y es el correlativo (REQ-1.1, REQ-1.2, REQ-6.1, etc.).
- **pattern**: Una de las 6 categorías EARS.
- **trigger**: La condición, evento o estado que activa el requisito.
- **system**: El nombre del sistema o subsistema.
- **response**: El comportamiento esperado.
- **source_statement**: La oración completa en sintaxis EARS.
- **rationale**: Por qué este requisito es necesario (trazando al Discovery).
- **traceability**: Referencia a la feature y sección del Discovery.
- **acceptance_criteria**: Al menos 1 criterio verificable (formato: Dado-Cuando-Entonces).

## Formato de salida (Markdown)
Los requisitos se agrupan verticalmente por categoría EARS:

### Requisitos Ubicuos
- REQ-X.1: [source_statement]. **Criterio**: Dado [contexto], Cuando [acción], Entonces [resultado esperado].

### Requisitos Basados en Eventos
- REQ-X.2: [source_statement]. **Criterio**: ...

(etc., agrupando por categoría)

## Guardrails (obligatorio)
- PROHIBIDO: términos de implementación (API, database, endpoint, server, HTTP, SQL, microservicio, cache, deploy).
- PROHIBIDO: requisitos ambiguos ("el sistema funcionará bien", "será rápido").
- OBLIGATORIO: cada requisito debe ser verificable con al menos 1 criterio de aceptación.
- OBLIGATORIO: al menos 4 categorías EARS diferentes por feature.
- OBLIGATORIO: al menos 3 requisitos y máximo 15 por feature.
- Todo en español con tildes correctas.

## Detección de fugas técnicas
Antes de generar, revisa:
- Ningún requisito menciona cómo implementar algo.
- Ningún requisito dice "el sistema guardará en base de datos" → usar "el sistema registrará y mantendrá".
- Ningún requisito describe arquitectura interna.

Si detectas una fuga, reemplázala con lenguaje de negocio:
- "almacenará en la base de datos" → "registrará y mantendrá"
- "enviará una petición HTTP" → "comunicará a"
- "validará con el servidor" → "verificará"

## Auto-validación (antes de responder)
1. Cada requisito sigue exactamente la sintaxis EARS de su categoría.
2. Cada requisito tiene al menos 1 criterio de aceptación verificable.
3. No hay requisitos duplicados ni contradictorios.
4. No hay fuga de términos técnicos.
5. Los requisitos cubren los 4W de la característica.
6. La numeración es REQ-X.Y consistente.
7. Al menos 4 categorías EARS están representadas.
"""
```

---

## 9. Diagramas Conceptuales

### 9.1 Arquitectura General con KOSMOAgent

```
                          ┌─────────────────────┐
                          │  API / Router Layer  │
                          │  (FastAPI endpoints) │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  ExecutePhaseUseCase │
                          │  (Orquestador)       │
                          └──────────┬──────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                 │
           ┌───────▼───────┐ ┌──────▼──────┐ ┌───────▼───────┐
           │  Agent         │ │  Context    │ │  Agent        │
           │  Orchestrator  │ │  Builder     │ │  Orchestrator │
           │  (Protocol)    │ │ (Pure func) │ │  Validator    │
           │                │ │             │ │  (handoffs)   │
           │  SequentialOrch│ │  Build       │ │  Validate     │
           │  estrator      │ │  PhaseCtx   │ │  transitions  │
           │  (domain/)     │ │  from state │ │               │
           └───────┬───────┘ └──────┬──────┘ └───────┬──────┘
                   │                │                 │
                   │        ┌───────▼───────┐         │
                   │        │  KOSMOPipeline │         │
                   │        │  State         │         │
                   │        │  (Estado       │         │
                   │        │   centralizado) │         │
                   │        └───────┬───────┘         │
                   │                │                 │
     ┌─────────────┼────────────────┼─────────────────┘
     │             │                 │
     │    ┌────────▼────────┐       │
     │    │  KOSMOAgent      │       │
     │    │  (ReAct cycle)   │       │
     │    │                  │       │
     │    │  PhaseMode ──────┤       │
     │    │  ├─ Discovery   │       │
     │    │  ├─ Features     │       │
     │    │  └─ EARS         │       │
     │    │                  │       │
     │    │  Tools per mode: │       │
     │    │  validate_*()    │       │
     │    │  search_*()      │       │
     │    │  suggest_*()     │       │
     │    │  save_*()         │       │
     │    └────────┬────────┘       │
     │             │                │
     │    ┌────────▼────────┐       │
     │    │  LLM Client      │       │
     │    │  (via Port)      │       │
     │    └─────────────────┘       │
     │                              │
     └──────────────────────────────┘
```

### 9.2 Ciclo ReAct del Agente

```
┌───────────────────────────────────────────────────────┐
│                  KOSMOAgent (ReAct)                    │
│                                                        │
│  ┌─────────────────────────────────────────────────┐ │
│  │ 1. OBSERVE: Recibe PhaseContext                  │ │
│  │    - Lee datos de entrada                        │ │
│  │    - Carga preferencias del usuario              │ │
│  └───────────────────┬─────────────────────────────┘ │
│                      │                                 │
│  ┌───────────────────▼─────────────────────────────┐ │
│  │ 2. REASON: Construye prompt + razonamiento       │ │
│  │    - Selecciona PhaseMode                        │ │
│  │    - Genera system_prompt + user_prompt          │ │
│  │    - Decide estrategia de generación             │ │
│  └───────────────────┬─────────────────────────────┘ │
│                      │                                 │
│  ┌───────────────────▼─────────────────────────────┐ │
│  │ 3. ACT: Genera contenido (LLM call)             │ │
│  │    - Llama al LLM con el prompt construido       │ │
│  │    - Parsea la respuesta estructurada             │ │
│  └───────────────────┬─────────────────────────────┘ │
│                      │                                 │
│  ┌───────────────────▼─────────────────────────────┐ │
│  │ 4. OBSERVE: Invoca Tools de validación            │ │
│  │    - validate_*() según PhaseMode                │ │
│  │    - detect_*() si aplica                       │ │
│  │    - Recopila errores y warnings                 │ │
│  └───────────────────┬─────────────────────────────┘ │
│                      │                                 │
│  ┌───────────────────▼─────────────────────────────┐ │
│  │ 5. REFLECT: ¿El resultado cumple?                │ │
│  │    ├─ Sí → RETORNAR PhaseOutput                  │ │
│  │    └─ No → REASON sobre errores específicos       │ │
│  │         → Construir retry_prompt                  │ │
│  │         → Volver a paso 3 (max 3 ciclos)        │ │
│  └─────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────┘
```

### 9.3 Flujo de Endpoints por Pantalla

```
PANTALLA 2 → 3: Creación → Discovery
══════════════════════════════════════
POST /api/v1/projects
  → Crea proyecto vacío
POST /api/v1/projects/{id}/discovery/generate
  → KOSMOAgent(DiscoveryMode) → DiscoveryPhaseOutput
  → Frontend renderiza documento en editor enriquecido

PANTALLA 3: Discovery (edición)
═══════════════════════════════════
PUT /api/v1/projects/{id}/discovery
  → Persiste ediciones manuales del usuario

PANTALLA 4: Características (5 features)
══════════════════════════════════════════
POST /api/v1/projects/{id}/features/generate
  → KOSMOAgent(FeaturesMode) → FeaturesPhaseOutput (C01-C05, borrador)

POST /api/v1/projects/{id}/features/suggest
  → KOSMOAgent(FeaturesMode, sub-modo suggest) → SuggestFeaturesOutput (3 sugerencias)
  → Frontend muestra modal con selector múltiple

POST /api/v1/projects/{id}/features (guardar seleccionadas del modal)
  → Crea features seleccionadas con number continuo (C06, C07, etc.)

PATCH /api/v1/features/{id}/status
  → feature.status: borrador → aprobada

PANTALLA 5: Requisitos (por feature individual)
════════════════════════════════════════════════
POST /api/v1/features/{id}/requirements/generate
  → KOSMOAgent(EARSMode) → EARSPhaseOutput (REQ-X.X por feature)
  → Frontend muestra requisitos agrupados por taxonomía EARS

PUT /api/v1/features/{id}/requirements
  → Persiste ediciones manuales de requisitos
```

### 9.4 Escalabilidad: de Agente Único a Multiagente

```
HOY: 1 Agente, 3 Modos                              MAÑANA: 3 Agentes, 1 Orquestador

KOSMOAgent                                            AgentOrchestrator
┌────────────────────────────┐                        ┌─────────────────────┐
│  Ciclo ReAct compartido     │                        │  SequentialOrch.    │
│                              │                        │  LangGraphOrch.    │
│  ┌─────────────────────────┐│                        │  (Protocol:         │
│  │ PhaseModeDiscovery       ││──→ migración ──→      │   interchangeable)  │
│  │ PhaseModeFeatures        ││                        └──┬──────┬──────┬──┘
│  │ PhaseModeEARS            ││                           │      │      │
│  └─────────────────────────┘│                        ┌──▼──┐ ┌──▼──┐ ┌──▼───┐
│                              │                        │Disc.│ │Feat.│ │EARS  │
│  SequentialOrchestrator      │                        │Agent│ │Agent│ │Agent │
│  (lógica pura, domain/)      │                        │     │ │     │ │      │
└────────────────────────────┘                        └─────┘ └─────┘ └──────┘
                                                        │      │      │
                                                     Ciclo ReAct propio
                                                     Tools propias
                                                     System prompt propio

Lo que NO cambia:
- PhaseContext (inputs tipados por fase)
- PhaseOutput (outputs tipados por fase)
- KOSMOPipelineState (estado centralizado)
- Tools de domain/ (validadores puras)
- AgentOrchestrator Protocol (misma interfaz)
- LLMClient (puerto)
- Entidades de contracts/sdd/

Lo que SÍ cambia:
- KOSMOAgent se divide en 3 PhaseAgent independientes
- SequentialOrchestrator se reemplaza por LangGraphOrchestrator (en infrastructure/)
- Cada PhaseAgent tiene su propio ciclo ReAct, checkpointing y human-in-the-loop
- Se añaden nodos de crítica separados (quality, style, consistency)
- Se añaden nodos de aprendizaje (preference_feedback, learn_from_correction)
```

---

## 10. Estructura de Directorios y Contratos

### 10.1 Estructura de Directorios

```
contracts/
  pipeline/                              # NEW: Pipeline contracts
    phase_contexts.py                    # DiscoveryPhaseContext, FeaturesPhaseContext,
                                         #   EARSPhaseContext, SuggestFeaturesContext
    phase_outputs.py                     # DiscoveryPhaseOutput, FeaturesPhaseOutput,
                                         #   EARSPhaseOutput, SuggestFeaturesOutput,
                                         #   ValidationResult, GenerationMetadata
    pipeline_state.py                    # KOSMOPipelineState, PhaseTransitionRecord
    orchestrator_ports.py                # AgentOrchestrator Protocol, PhaseMode Protocol,
                                         #   ToolDefinition, ToolResult
    phase_errors.py                      # PhaseTransitionError, PhaseNotSupportedError
  sdd/                                   # EXISTING (reutilizar)
    discovery.py                         # RawIdea, DiscoveryDocument
    feature.py                           # Feature, FeatureStatus (extendido con number + display_id)
    ears.py                              # EARSRequirement, EARSPattern
    ...                                  # Resto de entidades existentes

domain/
  pipeline/                              # NEW: Lógica pura del pipeline
    kosmo_agent.py                       # KOSMOAgent con ciclo ReAct (lógica pura, sin I/O)
    context_builder.py                   # ContextBuilder — extrae PhaseContext desde PipelineState
    sequential_orchestrator.py           # SequentialOrchestrator — lógica pura de secuenciamiento
    phase_modes/                          # NEW: Comportamientos por fase
      discovery_mode.py                   # DiscoveryMode: system_prompt, tools, validate, retry
      features_mode.py                   # FeaturesMode: system_prompt, tools, validate, retry
      ears_mode.py                       # EARSMode: system_prompt, tools, validate, retry
    phase_validators/                     # NEW: Validadores cross-fase
      discovery_validator.py              # validate_discovery_structure(), validate_discovery_quality()
      features_validator.py              # validate_features_structure(), validate_features_semantic()
      ears_validator.py                  # validate_ears_syntax(), validate_ears_quality(),
                                         #   detect_implementation_leaks(), auto_repair_leaks()
  sdd/                                   # EXISTING (reutilizar)
    ...                                  # Validadores, convertidores, helpers, templates

application/
  pipeline/                              # NEW: Casos de uso del pipeline
    execute_phase.py                     # ExecutePhaseUseCase
    advance_pipeline.py                  # AdvancePipelineUseCase
    get_pipeline_status.py               # GetPipelineStatusUseCase
  discovery/                             # NEW: Casos de uso de Discovery
    generate_discovery.py               # GenerateDiscoveryUseCase
    save_discovery.py                   # SaveDiscoveryUseCase
  features/                             # NEW: Casos de uso de Features
    generate_features.py                # GenerateFeaturesUseCase (5 features C01-C05)
    suggest_features.py                 # SuggestFeaturesUseCase (3 sugerencias del modal)
    approve_feature.py                  # ApproveFeatureUseCase (BORRADOR → APROBADA)
    save_features.py                    # SaveFeaturesUseCase (persistir features del modal)
  requirements/                          # NEW: Casos de uso de EARS
    generate_ears.py                    # GenerateEARSUseCase (por feature individual)
    save_requirements.py               # SaveRequirementsUseCase

infrastructure/
  pipeline/                              # NEW: Adaptadores del pipeline (implementaciones concretas)
    langgraph_orchestrator.py           # LangGraphOrchestrator (futuro, cuando se migre a multiagente)
    # NOTA: SequentialOrchestrator está en domain/ porque es lógica pura
                                          # sin I/O, sin dependencia de framework externo
  api/
    routers/                             # EXISTING (extender)
      discovery.py                       # Endpoints de discovery (existing, adaptar)
      features.py                        # Endpoints de features (existing, adaptar)
      requirements.py                    # Endpoints de requirements (existing, adaptar)
```

### 10.2 Nuevos Contratos a Crear

| Nuevo Contrato | Archivo | Propósito |
|---------------|---------|-----------|
| `KOSMOPipelineState` | `contracts/pipeline/pipeline_state.py` | Estado centralizado del pipeline |
| `DiscoveryPhaseContext` | `contracts/pipeline/phase_contexts.py` | Input aislado para Discovery |
| `FeaturesPhaseContext` | `contracts/pipeline/phase_contexts.py` | Input aislado para Features |
| `EARSPhaseContext` | `contracts/pipeline/phase_contexts.py` | Input aislado para EARS (por feature) |
| `SuggestFeaturesContext` | `contracts/pipeline/phase_contexts.py` | Contexto para modal de 3 sugerencias |
| `DiscoveryPhaseOutput` | `contracts/pipeline/phase_outputs.py` | Output contractual de Discovery |
| `FeaturesPhaseOutput` | `contracts/pipeline/phase_outputs.py` | Output contractual de Features |
| `EARSPhaseOutput` | `contracts/pipeline/phase_outputs.py` | Output contractual de EARS (por feature) |
| `SuggestFeaturesOutput` | `contracts/pipeline/phase_outputs.py` | Output de 3 sugerencias (modal) |
| `ValidationResult` | `contracts/pipeline/phase_outputs.py` | Resultado de validación embebida |
| `GenerationMetadata` | `contracts/pipeline/phase_outputs.py` | Metadatos de generación + reasoning log |
| `PhaseTransitionRecord` | `contracts/pipeline/pipeline_state.py` | Registro de transición de fase |
| `AgentOrchestrator` | `contracts/pipeline/orchestrator_ports.py` | Protocol para orquestador (agnóstico) |
| `PhaseMode` | `contracts/pipeline/orchestrator_ports.py` | Protocol para modo de comportamiento |
| `PhaseTransitionError` | `contracts/pipeline/phase_errors.py` | Error de handoff (RFC 7807) |
| `PhaseNotSupportedError` | `contracts/pipeline/phase_errors.py` | Fase no soportada (RFC 7807) |

### 10.3 Extensiones a Entidades Existentes

| Entidad | Cambio | Justificación |
|---------|--------|---------------|
| `Feature` | Agregar `number: int` y `display_id: str` property (formato C0X) | Soportar numeración C01, C02, etc. |
| `EARSRequirement` | Soporte para numeración REQ-X.X con `feature_number: int` y `requirement_number: int` | Soportar REQ-6.1, REQ-6.2, etc. |
| `SpecPhase` | Ya tiene `DESCUBRIMIENTO`, `CARACTERISTICAS`, `REQUISITOS` | Se usan directamente |

### 10.4 Cumplimiento de Reglas de Estilo (CLAUDE.md)

| Regla | Aplicación en el Plan |
|-------|----------------------|
| **Hexagonal** | `contracts/pipeline/` tiene Protocols y entities. `domain/pipeline/` tiene lógica pura. `application/pipeline/` tiene use cases. `infrastructure/pipeline/` tiene adaptadores concretos. |
| **Composition root** | Todo el wiring (agent, orchestrator, repos) en `infrastructure/api/composition.py`. |
| **Domain is pure** | `KOSMOAgent`, `SequentialOrchestrator`, `ContextBuilder`, `PhaseMode`, validadores — todo en `domain/` sin I/O, sin clock, sin randomness. |
| **Naming** | `context_builder`, `kosmo_agent`, `sequential_orchestrator`, `discovery_mode` — English, snake_case, sin `data`, `info`, `manager`, `helper`, `utils`. |
| **IDs** | Pipeline: `IdGenerator.generate("pipe")` → `pipe_01KT...`. Feature: `feat_01KT...`. Requirement: nuevo prefijo `req_01KT...`. |
| **Fechas** | `datetime.now(UTC)` con sufijo `Z` en serialización. |
| **Nulables** | `null`, nunca `""` ni `0`. |
| **Errores RFC 7807** | `PhaseTransitionError` → `type="urn:kosmo:pipeline:phase-transition-error"`. `FeatureNotApprovedError` → `type="urn:kosmo:features:not-approved"`. |
| **Code in English** | Identifiers, archivos, módulos: English. |
| **Messages in Spanish** | System prompts, mensajes al usuario, detalles de error: Spanish. |
| **No comments** | Código sin comentarios por defecto. Solo cuando el por qué no es obvio. |

---

## 11. Roadmap de Migración a Multiagente

### 11.1 Fase Actual: Agente Único con PhaseModes

| Componente | Implementación | Archivo |
|------------|---------------|---------|
| `KOSMOAgent` | Agente ReAct con 3 PhaseModes (ciclo Reason→Act→Observe→Reflect) | `domain/pipeline/kosmo_agent.py` |
| `SequentialOrchestrator` | Lógica pura de secuenciamiento (sin I/O, sin framework) | `domain/pipeline/sequential_orchestrator.py` |
| `ContextBuilder` | Función pura que construye PhaseContext desde PipelineState | `domain/pipeline/context_builder.py` |
| `DiscoveryMode` | System prompt, tools, validación, retry para Discovery | `domain/pipeline/phase_modes/discovery_mode.py` |
| `FeaturesMode` | System prompt, tools, validación, retry para Features | `domain/pipeline/phase_modes/features_mode.py` |
| `EARSMode` | System prompt, tools, validación, retry para EARS | `domain/pipeline/phase_modes/ears_mode.py` |
| `ExecutePhaseUseCase` | Orquesta Orchestrator → Agent → Validator | `application/pipeline/execute_phase.py` |
| `AdvancePipelineUseCase` | Valida handoff y avanza fase | `application/pipeline/advance_pipeline.py` |
| `KOSMOPipelineState` | Estado centralizado con PhaseOutputs | `contracts/pipeline/pipeline_state.py` |

### 11.2 Fase de Transición: Preparación para Multiagente

1. **Registrar Tools en ToolRegistry**: Las validaciones embebidas se registran como Tools en `InMemoryToolRegistry` pero se siguen llamando desde el agente.
2. **Refactorizar PhaseModes a Protocol**: Los modos se convierten en implementaciones completas del `PhaseMode` Protocol.
3. **Implementar Checkpointing**: `KOSMOPipelineState` se persiste como checkpoint entre cada fase.
4. **Extraer reasoning_log y tool_results**: Los logs internos del ciclo ReAct se almacenan en `GenerationMetadata` para auditoría y aprendizaje.

### 11.3 Fase Multiagente: Orquestación con LangGraph u otro framework

1. **`KOSMOAgent` → 3 `PhaseAgent` independientes**: Cada `PhaseMode` se convierte en un agente con su propio ciclo ReAct, memoria, y capacidad de tool-calling autónomo.
2. **`SequentialOrchestrator` → `LangGraphOrchestrator`**: Se reemplaza la implementación secuencial por un StateGraph con nodos y edges. El Protocol `AgentOrchestrator` no cambia — solo se añade una nueva implementación en `infrastructure/pipeline/langgraph_orchestrator.py`.
3. **Validación → Nodos de crítica separados**: La validación embebida se extrae como nodos de crítico (quality, style, consistency) con fan-out paralelo.
4. **Aprendizaje**: Se integran nodos `preference_feedback` y `learn_from_correction`.
5. **Human-in-the-loop**: Se usa `Command(resume=...)` de LangGraph para puntos de aprobación.

### 11.4 Contratos que NO Cambian en la Migración

| Contrato | Monolito | Multiagente | Cambia? |
|----------|----------|-------------|---------|
| `PhaseMode.system_prompt` | String | String | NO |
| `PhaseMode.validate_output()` | Función pura | Función pura | NO |
| `PhaseContext` (input por fase) | Dict Pydantic | Dict Pydantic | NO |
| `PhaseOutput` (output por fase) | Dict Pydantic | Dict Pydantic | NO |
| `KOSMOPipelineState` | Modelo con PhaseOutputs | Modelo + reducers LangGraph | Mínimo |
| Validadores (`domain/sdd/validators/`) | Funciones puras | Funciones puras | NO |
| Entidades de `contracts/sdd/` | Pydantic models | Pydantic models | NO |
| Repositorios (puertos) | Protocols | Protocols | NO |
| `LLMClient` (puerto) | Protocol con `complete()` | Protocol con `complete()` + `stream()` | Mínimo |
| `AgentOrchestrator` (Protocol) | SequentialOrchestrator | LangGraphOrchestrator | NO (Protocol) |
| `PhaseMode` (Protocol) | KOSMOAgent con modos | PhaseAgent independiente | NO (Protocol) |
| Endpoints REST | Mismos endpoints | Mismos endpoints | NO |

---

---

## 12. Orden de Implementación

La implementación sigue el flujo hexagonal: **contratos → dominio → aplicación → infraestructura**. Cada fase se construye sobre la anterior. No se avanza a una fase hasta que su predecesora compila y los tests pasan.

### Fase 0 — Preparación del Terreno

**Objetivo**: Tener el codebase limpio y compilable antes de empezar.

| Paso | Acción | Archivos | Verificación |
|------|--------|----------|-------------|
| 0.1 | Eliminar stubs vacíos (MongoDB, sandbox, git, outbox, MCP) si molestan | `infrastructure/mcp/`, `mongodb/`, `sandbox/`, `git/`, `outbox/` | `pyright` sin errores en `src/kosmo` |
| 0.2 | Verificar que `contracts/sdd/`, `domain/sdd/`, `domain/agents/` compilan | Todo `src/kosmo/` existente | `uv run pyright` |
| 0.3 | Correr tests existentes para establecer baseline | `tests/` | `uv run pytest tests/unit/` todo verde |
| 0.4 | Crear directorios vacíos del nuevo pipeline | `contracts/pipeline/`, `domain/pipeline/phase_modes/`, `domain/pipeline/phase_validators/`, `application/pipeline/`, `application/discovery/`, `application/features/`, `application/requirements/`, `infrastructure/pipeline/` | Directorios creados con `__init__.py` |

---

### Fase 1 — Contratos (`contracts/`)

**Objetivo**: Todos los tipos, entities, Protocols y errores definidos. Sin implementación. Sin dependencias externas.

**Dependencias**: Ninguna. Esto es el kernel.

#### 1.1 Errores del Pipeline

| Archivo | Contenido |
|---------|-----------|
| `contracts/pipeline/__init__.py` | Vacío |
| `contracts/pipeline/phase_errors.py` | `PhaseTransitionError(SpecError)`, `PhaseNotSupportedError(SpecError)` |

**Campos de cada error** (RFC 7807):
```python
class PhaseTransitionError(SpecError):
    type: str = "urn:kosmo:pipeline:phase-transition-error"
    title: str = "Transición de fase inválida"
    status: int = 409
    detail: str
    instance: str
    trace_id: str = field(default_factory=lambda: ULID().hex)
    violations: list[Violation] = []

class PhaseNotSupportedError(SpecError):
    type: str = "urn:kosmo:pipeline:phase-not-supported"
    title: str = "Fase no soportada"
    status: int = 400
    detail: str
    instance: str
    trace_id: str = field(default_factory=lambda: ULID().hex)
    violations: list[Violation] = []
```

**Verificación**: `uv run pyright` — solo `contracts/pipeline/` compila. `uv run pytest tests/unit/ -k "error"` — si hay tests de errores existentes, siguen pasando.

#### 1.2 PhaseContexts (Inputs Aislados)

| Archivo | Contenido |
|---------|-----------|
| `contracts/pipeline/phase_contexts.py` | `DiscoveryPhaseContext`, `FeaturesPhaseContext`, `EARSPhaseContext`, `SuggestFeaturesContext` |

Cada uno es un `BaseModel` con:
- Solo los campos descritos en la sección 4.2
- `model_config = ConfigDict(arbitrary_types_allowed=True)`
- Dependencia de tipos de `contracts/sdd/`: `RawIdea`, `RichTextDocument`, `Feature`, `UserPreference`

**Verificación**: `uv run pyright` — `contracts/pipeline/` compila.

#### 1.3 PhaseOutputs (Contratos de Salida)

| Archivo | Contenido |
|---------|-----------|
| `contracts/pipeline/phase_outputs.py` | `ValidationResult`, `GenerationMetadata`, `DiscoveryPhaseOutput`, `FeaturesPhaseOutput`, `SuggestFeaturesOutput`, `EARSPhaseOutput` |

**Verificación**: `uv run pyright` — `contracts/pipeline/` compila completo.

#### 1.4 PipelineState (Estado Centralizado)

| Archivo | Contenido |
|---------|-----------|
| `contracts/pipeline/pipeline_state.py` | `KOSMOPipelineState`, `PhaseTransitionRecord` |

**Verificación**: `uv run pyright` — todo `contracts/pipeline/` compila.

#### 1.5 Orchestrator Ports (Protocols)

| Archivo | Contenido |
|---------|-----------|
| `contracts/pipeline/orchestrator_ports.py` | `PhaseMode(Protocol)`, `AgentOrchestrator(Protocol)`, `ToolDefinition`, `ToolResult` |

**Verificación**: `uv run pyright` — todo `contracts/pipeline/` compila. `uv run lint-imports` — no hay violaciones de capa (contracts no depende de nadie).

---

### Fase 2 — Dominio (`domain/`)

**Objetivo**: Toda la lógica pura implementada. Sin I/O, sin DB, sin HTTP. Solo algoritmos.

**Dependencias**: `contracts/pipeline/`, `contracts/sdd/`, `contracts/llm/ports.py` (`LLMClient` Protocol).

#### 2.1 ContextBuilder

| Archivo | Contenido |
|---------|-----------|
| `domain/pipeline/__init__.py` | Vacío |
| `domain/pipeline/context_builder.py` | `ContextBuilder` con métodos: `build_context()`, `_build_discovery_context()`, `_build_features_context()`, `_build_ears_context()`, `build_ears_context_for_feature()`, `build_suggest_features_context()`, `_get_feature_number()` |

**Lógica interna**:
- `build_context()` despacha según `SpecPhase`
- `_build_features_context()` lanza `PhaseTransitionError` si `discovery_output is None`
- `build_ears_context_for_feature()` lanza `FeatureNotFoundError` o `FeatureNotApprovedError` si no se cumplen condiciones

**Tests**:
- `test_build_discovery_context` — construye contexto con RawIdea
- `test_build_features_context_fails_without_discovery` — lanza PhaseTransitionError
- `test_build_ears_context_fails_for_unapproved_feature` — lanza FeatureNotApprovedError
- `test_build_ears_context_for_feature` — construye contexto con feature aprobada

**Verificación**: `uv run pytest tests/unit/test_context_builder.py` — 4+ tests verdes.

#### 2.2 Validadores de Fase

| Archivo | Contenido |
|---------|-----------|
| `domain/pipeline/phase_validators/__init__.py` | Vacío |
| `domain/pipeline/phase_validators/discovery_validator.py` | `validate_discovery_structure(doc: RichTextDocument) -> ValidationResult`, `validate_discovery_quality(doc: RichTextDocument) -> ValidationResult` |
| `domain/pipeline/phase_validators/features_validator.py` | `validate_features_structure(features: list[Feature]) -> ValidationResult`, `validate_features_semantic(features: list[Feature], discovery: RichTextDocument) -> ValidationResult` |
| `domain/pipeline/phase_validators/ears_validator.py` | `validate_ears_syntax(requirements: list[EARSRequirement]) -> ValidationResult`, `validate_ears_quality(requirements: list[EARSRequirement]) -> ValidationResult`, `detect_implementation_leaks(requirements: list[EARSRequirement]) -> ValidationResult`, `auto_repair_leaks(requirements: list[EARSRequirement]) -> list[EARSRequirement]` |

**Nota**: `ears_validator.py` reutiliza/extiende `domain/sdd/validators/ears_validator.py` y `domain/sdd/output_guardrails.py` existentes.

**Tests**:
- `test_validate_discovery_structure_valid` — documento con 9 secciones pasa
- `test_validate_discovery_structure_missing_section` — falta sección, retorna errores
- `test_validate_discovery_quality_no_tech_jargon` — sin jerga técnica pasa
- `test_validate_discovery_quality_detects_api` — detecta "API", retorna error
- `test_validate_features_structure_4w` — 4W completos pasa
- `test_validate_features_semantic_no_overlap` — sin solapamiento pasa
- `test_validate_features_semantic_detects_overlap` — features con títulos similares falla
- `test_validate_ears_syntax_correct` — sintaxis EARS correcta pasa
- `test_validate_ears_syntax_wrong_pattern` — ubiquitous con WHEN falla
- `test_detect_implementation_leaks` — detecta "base de datos"
- `test_auto_repair_leaks` — reemplaza "base de datos" por "registrará"

**Verificación**: `uv run pytest tests/unit/test_phase_validators.py` — 11+ tests verdes.

#### 2.3 SequentialOrchestrator

| Archivo | Contenido |
|---------|-----------|
| `domain/pipeline/sequential_orchestrator.py` | `SequentialOrchestrator` que implementa `AgentOrchestrator` Protocol |

**Lógica interna**:
- `PHASE_ORDER = [DESCUBRIMIENTO, CARACTERISTICAS, REQUISITOS]`
- `can_advance(state, target)` — valida precondiciones
- `execute_phase(state, phase, agent)` — ejecuta agente y actualiza state
- `advance_pipeline(state, target)` — valida + avanza fase + crea `PhaseTransitionRecord`

**Tests**:
- `test_can_advance_from_discovery_to_features` — sí puede si discovery_output existe
- `test_cannot_advance_to_features_without_discovery` — lanza error
- `test_cannot_advance_to_requirements_without_approved_features` — lanza error
- `test_execute_phase_updates_state` — el state se actualiza con PhaseOutput
- `test_advance_pipeline_creates_transition_record` — se registra PhaseTransitionRecord

**Verificación**: `uv run pytest tests/unit/test_sequential_orchestrator.py` — 5+ tests verdes.

#### 2.4 PhaseModes (Comportamientos del Agente)

| Archivo | Contenido |
|---------|-----------|
| `domain/pipeline/phase_modes/__init__.py` | Vacío |
| `domain/pipeline/phase_modes/discovery_mode.py` | `DiscoveryMode` — implementa `PhaseMode` Protocol |
| `domain/pipeline/phase_modes/features_mode.py` | `FeaturesMode` — implementa `PhaseMode` Protocol |
| `domain/pipeline/phase_modes/ears_mode.py` | `EARSMode` — implementa `PhaseMode` Protocol |

Cada `PhaseMode` contiene:
- `phase_name` property → `SpecPhase`
- `system_prompt` property → string constante (el prompt de la sección 8)
- `available_tools` property → `list[ToolDefinition]`
- `build_user_prompt(context)` → construye el user prompt con los datos del PhaseContext
- `validate_output(output)` → invoca los validadores de la fase correspondiente
- `build_retry_prompt(original, errors, attempt)` → construye prompt con feedback de errores

**Nota**: En el monolito, estos son funciones/dataclasses puras. No tienen estado mutable. El LLM no se invoca desde aquí — solo se construyen prompts y se valida.

**Tests** (por mode):
- `test_discovery_mode_system_prompt_not_empty`
- `test_discovery_mode_build_user_prompt_includes_raw_idea`
- `test_discovery_mode_validate_output_ok`
- `test_features_mode_system_prompt_mentions_C0X`
- `test_features_mode_build_retry_prompt_includes_errors`
- `test_ears_mode_system_prompt_mentions_REQ_X`
- `test_ears_mode_validate_output_detects_leaks`

**Verificación**: `uv run pytest tests/unit/test_phase_modes.py` — 7+ tests verdes.

#### 2.5 KOSMOAgent (El Corazón)

| Archivo | Contenido |
|---------|-----------|
| `domain/pipeline/kosmo_agent.py` | `KOSMOAgent` — el agente ReAct |

**Dependencias**: `LLMClient` (inyectado), `ContextBuilder` (inyectado), `dict[SpecPhase, PhaseMode]` (inyectado).

**Lógica interna** (ver sección 3.3 para el código completo):
- `__init__` recibe `llm_client`, `context_builder`, `modes`, `max_correction_cycles=3`
- `execute(pipeline_state)` — ciclo ReAct:
  1. Construye PhaseContext via `context_builder`
  2. Selecciona PhaseMode según `pipeline_state.current_phase`
  3. Bucle for `attempt in range(max_correction_cycles + 1)`:
     - Construye prompt → `llm_client.complete()` → parsea JSON
     - `mode.validate_output()` → si OK, retorna `PhaseOutput`
     - Si falla, `mode.build_retry_prompt()` → repite
  4. Si agota reintentos, retorna `PhaseOutput` con `validation_result.is_valid=False`
- `execute_suggest(pipeline_state)` — igual pero para suggest features (sub-modo)
- Métodos privados: `_build_phase_output()`, `_temperature_for_phase()`, `_collect_tool_results()`

**Tests** (con `NoopLLMClient` mock):
- `test_agent_execute_discovery_success` — genera discovery válido en 1 intento
- `test_agent_execute_features_with_retry` — falla 1 vez, corrige, éxito en 2do intento
- `test_agent_execute_ears_exhausts_retries` — falla 3 veces, retorna con errores
- `test_agent_execute_includes_reasoning_log` — `generation_metadata.reasoning_log` no vacío
- `test_agent_execute_suggest_features` — genera 3 sugerencias sin duplicados
- `test_agent_switches_mode_based_on_phase` — Discovery vs Features vs EARS usan prompts distintos

**Verificación**: `uv run pytest tests/unit/test_kosmo_agent.py` — 6+ tests verdes.

---

### Fase 3 — Aplicación (`application/`)

**Objetivo**: Casos de uso que orquestan dominio + persistencia.

**Dependencias**: `domain/pipeline/`, `contracts/sdd/repositories.py` (Protocols de repos), `contracts/llm/ports.py`.

#### 3.1 Use Cases del Pipeline

| Archivo | Contenido |
|---------|-----------|
| `application/pipeline/__init__.py` | Vacío |
| `application/pipeline/execute_phase.py` | `ExecutePhaseUseCase` |
| `application/pipeline/advance_pipeline.py` | `AdvancePipelineUseCase` |
| `application/pipeline/get_pipeline_status.py` | `GetPipelineStatusUseCase` |

**`ExecutePhaseUseCase`**:
```python
class ExecutePhaseUseCase:
    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        pipeline_repo: PipelineRepository,
    ) -> None: ...
    
    async def execute(
        self, project_id: ProjectId, phase: SpecPhase
    ) -> KOSMOPipelineState: ...
```

**`AdvancePipelineUseCase`**:
```python
class AdvancePipelineUseCase:
    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        pipeline_repo: PipelineRepository,
    ) -> None: ...
    
    async def execute(
        self, project_id: ProjectId, target_phase: SpecPhase
    ) -> KOSMOPipelineState: ...
```

**`GetPipelineStatusUseCase`**:
```python
class GetPipelineStatusUseCase:
    def __init__(self, pipeline_repo: PipelineRepository) -> None: ...
    async def execute(self, project_id: ProjectId) -> KOSMOPipelineState: ...
```

**Tests**: `uv run pytest tests/unit/test_pipeline_use_cases.py` — 5+ tests con repos mock.

#### 3.2 Use Cases de Discovery

| Archivo | Contenido |
|---------|-----------|
| `application/discovery/__init__.py` | Vacío |
| `application/discovery/generate_discovery.py` | `GenerateDiscoveryUseCase` |
| `application/discovery/save_discovery.py` | `SaveDiscoveryUseCase` |

**`GenerateDiscoveryUseCase`**:
```python
class GenerateDiscoveryUseCase:
    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        pipeline_repo: PipelineRepository,
    ) -> None: ...
    
    async def execute(
        self, project_id: ProjectId, raw_idea: RawIdea
    ) -> DiscoveryPhaseOutput: ...
    # 1. Carga/Crea KOSMOPipelineState
    # 2. Establece raw_idea
    # 3. orchestrator.execute_phase(state, DESCUBRIMIENTO)
    # 4. pipeline_repo.save(state)
    # 5. Retorna state.discovery_output
```

**`SaveDiscoveryUseCase`**:
```python
class SaveDiscoveryUseCase:
    def __init__(self, pipeline_repo: PipelineRepository) -> None: ...
    
    async def execute(
        self, project_id: ProjectId, document: RichTextDocument
    ) -> KOSMOPipelineState: ...
    # Persiste ediciones manuales del usuario en el documento de discovery
```

#### 3.3 Use Cases de Features

| Archivo | Contenido |
|---------|-----------|
| `application/features/__init__.py` | Vacío |
| `application/features/generate_features.py` | `GenerateFeaturesUseCase` (5 features C01-C05) |
| `application/features/suggest_features.py` | `SuggestFeaturesUseCase` (3 sugerencias del modal) |
| `application/features/approve_feature.py` | `ApproveFeatureUseCase` (BORRADOR → APROBADA) |
| `application/features/save_features.py` | `SaveSelectedFeaturesUseCase` (persistir features del modal) |

**`GenerateFeaturesUseCase`**:
```python
class GenerateFeaturesUseCase:
    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        pipeline_repo: PipelineRepository,
    ) -> None: ...
    
    async def execute(
        self, project_id: ProjectId
    ) -> FeaturesPhaseOutput: ...
    # 1. Carga KOSMOPipelineState
    # 2. orchestrator.advance_pipeline(state, CARACTERISTICAS)
    # 3. orchestrator.execute_phase(state, CARACTERISTICAS)
    # 4. Numerar features C01-C05 con number correlativo
    # 5. pipeline_repo.save(state)
    # 6. Retorna state.features_output
```

**`SuggestFeaturesUseCase`**:
```python
class SuggestFeaturesUseCase:
    def __init__(
        self,
        agent: KOSMOAgent,
        context_builder: ContextBuilder,
        pipeline_repo: PipelineRepository,
    ) -> None: ...
    
    async def execute(
        self, project_id: ProjectId
    ) -> SuggestFeaturesOutput: ...
    # 1. Carga KOSMOPipelineState
    # 2. context_builder.build_suggest_features_context()
    # 3. agent.execute_suggest() → 3 sugerencias
    # 4. NO persiste (usuario decide en el modal)
    # 5. Retorna SuggestFeaturesOutput
```

**`ApproveFeatureUseCase`**:
```python
class ApproveFeatureUseCase:
    def __init__(self, pipeline_repo: PipelineRepository) -> None: ...
    
    async def execute(
        self, project_id: ProjectId, feature_id: FeatureId
    ) -> Feature: ...
    # 1. Valida transición BORRADOR → APROBADA
    # 2. Actualiza feature.status
    # 3. pipeline_repo.save(state)
    # 4. Retorna feature actualizada
```

**`SaveSelectedFeaturesUseCase`**:
```python
class SaveSelectedFeaturesUseCase:
    def __init__(self, pipeline_repo: PipelineRepository) -> None: ...
    
    async def execute(
        self, project_id: ProjectId, selected_ids: list[str]
    ) -> list[Feature]: ...
    # 1. Carga KOSMOPipelineState
    # 2. Filtra sugerencias por selected_ids
    # 3. Asigna numbers continuos (C06, C07, etc.)
    # 4. Agrega features al state.features
    # 5. pipeline_repo.save(state)
    # 6. Retorna features creadas
```

#### 3.4 Use Cases de Requisitos

| Archivo | Contenido |
|---------|-----------|
| `application/requirements/__init__.py` | Vacío |
| `application/requirements/generate_ears.py` | `GenerateEARSUseCase` (por feature individual) |
| `application/requirements/save_requirements.py` | `SaveRequirementsUseCase` |

**`GenerateEARSUseCase`**:
```python
class GenerateEARSUseCase:
    def __init__(
        self,
        agent: KOSMOAgent,
        context_builder: ContextBuilder,
        orchestrator: AgentOrchestrator,
        pipeline_repo: PipelineRepository,
    ) -> None: ...
    
    async def execute(
        self, project_id: ProjectId, feature_id: FeatureId
    ) -> EARSPhaseOutput: ...
    # 1. Carga KOSMOPipelineState
    # 2. context_builder.build_ears_context_for_feature(state, feature_id)
    #    → Valida feature aprobada, lanza si no
    # 3. Cambia temporalmente current_phase a REQUISITOS
    # 4. agent.execute(state) → EARSMode → genera REQ-X.X
    # 5. Asigna feature_number a cada requisito
    # 6. Guarda en state.ears_outputs[feature_id]
    # 7. pipeline_repo.save(state)
    # 8. Retorna EARSPhaseOutput
```

**`SaveRequirementsUseCase`**: Similar a `SaveDiscoveryUseCase` pero para requisitos.

**Tests**: `uv run pytest tests/unit/test_discovery_use_cases.py`, `tests/unit/test_features_use_cases.py`, `tests/unit/test_ears_use_cases.py` — 12+ tests con mocks.

---

### Fase 4 — Infraestructura (`infrastructure/`)

**Objetivo**: Adaptadores concretos y wiring.

**Dependencias**: `application/pipeline/`, `application/discovery/`, `application/features/`, `application/requirements/`.

#### 4.1 PipelineRepository (Persistencia del PipelineState)

| Archivo | Contenido |
|---------|-----------|
| `contracts/pipeline/pipeline_ports.py` | Agregar `PipelineRepository` Protocol |
| `infrastructure/persistence/postgres/repositories/pipeline.py` | `SqlAlchemyPipelineRepository` |

**`PipelineRepository` Protocol** (en `contracts/pipeline/pipeline_ports.py`):
```python
class PipelineRepository(Protocol):
    async def get(self, project_id: ProjectId) -> KOSMOPipelineState | None: ...
    async def save(self, state: KOSMOPipelineState) -> KOSMOPipelineState: ...
    async def get_by_id(self, pipeline_id: str) -> KOSMOPipelineState | None: ...
```

**`SqlAlchemyPipelineRepository`**:
```python
class SqlAlchemyPipelineRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None: ...
    
    async def get(self, project_id: ProjectId) -> KOSMOPipelineState | None:
        # Busca en DB por project_id
        # Deserializa JSON a KOSMOPipelineState
    
    async def save(self, state: KOSMOPipelineState) -> KOSMOPipelineState:
        # Serializa state a JSON
        # UPSERT en tabla pipeline_states
        # Actualiza updated_at
```

#### 4.2 Migración de Base de Datos

**Nueva migración Alembic** (`alembic/versions/0002_pipeline_state.py`):

```python
# Tabla: pipeline_states
# - id: UUID o ULID string PK
# - project_id: string FK → projects(id)
# - user_id: string FK → users(id)
# - pipeline_id: string UNIQUE
# - current_phase: string (enum SpecPhase)
# - state_json: JSONB (KOSMOPipelineState serializado)
# - created_at: timestamp with time zone
# - updated_at: timestamp with time zone
```

**Extensión de tabla features** (si no existe el campo `number`):
```sql
ALTER TABLE features ADD COLUMN IF NOT EXISTS number INTEGER;
```

**Extensión de tabla requirements** (si no existe numeración):
```sql
ALTER TABLE requirements ADD COLUMN IF NOT EXISTS feature_number INTEGER;
ALTER TABLE requirements ADD COLUMN IF NOT EXISTS requirement_number INTEGER;
```

#### 4.3 Composition Root (Wiring)

**Archivo**: `infrastructure/api/composition.py`

Agregar al `lifespan` de FastAPI:

```python
# En build_sdd_components() o nueva función build_pipeline_components()

def build_pipeline_components(
    settings: Settings,
    session_factory: async_sessionmaker,
    llm_client: LLMClient,
) -> PipelineComponents:
    # --- Repos ---
    pipeline_repo = SqlAlchemyPipelineRepository(session_factory)
    
    # --- Domain (lógica pura) ---
    context_builder = ContextBuilder()
    sequential_orchestrator = SequentialOrchestrator()
    
    # --- PhaseModes ---
    modes = {
        SpecPhase.DESCUBRIMIENTO: DiscoveryMode(),
        SpecPhase.CARACTERISTICAS: FeaturesMode(),
        SpecPhase.REQUISITOS: EARSMode(),
    }
    
    # --- Agente ---
    agent = KOSMOAgent(
        llm_client=llm_client,
        context_builder=context_builder,
        modes=modes,
        max_correction_cycles=3,
    )
    
    # --- Use Cases ---
    execute_phase_uc = ExecutePhaseUseCase(
        orchestrator=sequential_orchestrator,
        pipeline_repo=pipeline_repo,
    )
    advance_pipeline_uc = AdvancePipelineUseCase(
        orchestrator=sequential_orchestrator,
        pipeline_repo=pipeline_repo,
    )
    generate_discovery_uc = GenerateDiscoveryUseCase(
        orchestrator=sequential_orchestrator,
        pipeline_repo=pipeline_repo,
    )
    save_discovery_uc = SaveDiscoveryUseCase(pipeline_repo=pipeline_repo)
    generate_features_uc = GenerateFeaturesUseCase(
        orchestrator=sequential_orchestrator,
        pipeline_repo=pipeline_repo,
    )
    suggest_features_uc = SuggestFeaturesUseCase(
        agent=agent,
        context_builder=context_builder,
        pipeline_repo=pipeline_repo,
    )
    approve_feature_uc = ApproveFeatureUseCase(pipeline_repo=pipeline_repo)
    save_features_uc = SaveSelectedFeaturesUseCase(pipeline_repo=pipeline_repo)
    generate_ears_uc = GenerateEARSUseCase(
        agent=agent,
        context_builder=context_builder,
        orchestrator=sequential_orchestrator,
        pipeline_repo=pipeline_repo,
    )
    save_requirements_uc = SaveRequirementsUseCase(pipeline_repo=pipeline_repo)
    
    return PipelineComponents(
        execute_phase_uc=execute_phase_uc,
        advance_pipeline_uc=advance_pipeline_uc,
        generate_discovery_uc=generate_discovery_uc,
        save_discovery_uc=save_discovery_uc,
        generate_features_uc=generate_features_uc,
        suggest_features_uc=suggest_features_uc,
        approve_feature_uc=approve_feature_uc,
        save_features_uc=save_features_uc,
        generate_ears_uc=generate_ears_uc,
        save_requirements_uc=save_requirements_uc,
    )
```

**`PipelineComponents`** dataclass (en el mismo archivo):
```python
@dataclass(frozen=True, slots=True)
class PipelineComponents:
    execute_phase_uc: ExecutePhaseUseCase
    advance_pipeline_uc: AdvancePipelineUseCase
    generate_discovery_uc: GenerateDiscoveryUseCase
    save_discovery_uc: SaveDiscoveryUseCase
    generate_features_uc: GenerateFeaturesUseCase
    suggest_features_uc: SuggestFeaturesUseCase
    approve_feature_uc: ApproveFeatureUseCase
    save_features_uc: SaveSelectedFeaturesUseCase
    generate_ears_uc: GenerateEARSUseCase
    save_requirements_uc: SaveRequirementsUseCase
```

Guardar en `app.state`:
```python
app.state.pipeline_components = build_pipeline_components(...)
```

#### 4.4 Routers (Endpoints)

**Archivo**: `infrastructure/api/routers/discovery.py` (extender existente)

```python
@router.post("/projects/{project_id}/discovery/generate")
async def generate_discovery(
    project_id: str,
    body: GenerateDiscoveryRequest,
    request: Request,
) -> DiscoveryPhaseOutput:
    uc = request.app.state.pipeline_components.generate_discovery_uc
    output = await uc.execute(
        project_id=ProjectId(project_id),
        raw_idea=RawIdea(text=body.raw_idea, optional_context=body.context),
    )
    return output

@router.put("/projects/{project_id}/discovery")
async def save_discovery(
    project_id: str,
    body: SaveDiscoveryRequest,
    request: Request,
) -> KOSMOPipelineState:
    uc = request.app.state.pipeline_components.save_discovery_uc
    return await uc.execute(
        project_id=ProjectId(project_id),
        document=body.document,
    )
```

**Archivo**: `infrastructure/api/routers/features.py` (extender existente)

```python
@router.post("/projects/{project_id}/features/generate")
async def generate_features(
    project_id: str, request: Request
) -> FeaturesPhaseOutput:
    uc = request.app.state.pipeline_components.generate_features_uc
    return await uc.execute(project_id=ProjectId(project_id))

@router.post("/projects/{project_id}/features/suggest")
async def suggest_features(
    project_id: str, request: Request
) -> SuggestFeaturesOutput:
    uc = request.app.state.pipeline_components.suggest_features_uc
    return await uc.execute(project_id=ProjectId(project_id))

@router.patch("/features/{feature_id}/status")
async def approve_feature(
    feature_id: str,
    body: ApproveFeatureRequest,
    request: Request,
) -> Feature:
    uc = request.app.state.pipeline_components.approve_feature_uc
    return await uc.execute(
        project_id=ProjectId(body.project_id),
        feature_id=FeatureId(feature_id),
    )

@router.post("/projects/{project_id}/features")
async def save_selected_features(
    project_id: str,
    body: SaveSelectedFeaturesRequest,
    request: Request,
) -> list[Feature]:
    uc = request.app.state.pipeline_components.save_features_uc
    return await uc.execute(
        project_id=ProjectId(project_id),
        selected_ids=body.selected_ids,
    )
```

**Archivo**: `infrastructure/api/routers/requirements.py` (extender existente)

```python
@router.post("/features/{feature_id}/requirements/generate")
async def generate_requirements(
    feature_id: str,
    body: GenerateRequirementsRequest,
    request: Request,
) -> EARSPhaseOutput:
    uc = request.app.state.pipeline_components.generate_ears_uc
    return await uc.execute(
        project_id=ProjectId(body.project_id),
        feature_id=FeatureId(feature_id),
    )

@router.put("/features/{feature_id}/requirements")
async def save_requirements(
    feature_id: str,
    body: SaveRequirementsRequest,
    request: Request,
) -> None:
    uc = request.app.state.pipeline_components.save_requirements_uc
    return await uc.execute(
        project_id=ProjectId(body.project_id),
        feature_id=FeatureId(feature_id),
        document=body.document,
    )
```

#### 4.5 Schemas de API (DTOs)

| Archivo | Contenido |
|---------|-----------|
| `infrastructure/api/routers/schemas.py` | Agregar: `GenerateDiscoveryRequest`, `SaveDiscoveryRequest`, `SaveSelectedFeaturesRequest`, `ApproveFeatureRequest`, `GenerateRequirementsRequest`, `SaveRequirementsRequest` |

---

### Fase 5 — Integración y Verificación End-to-End

**Objetivo**: Verificar que todo el flujo funciona de punta a punta.

#### 5.1 Tests de Integración

| Test | Qué verifica |
|------|-------------|
| `test_full_discovery_flow` | POST create project → POST generate discovery → GET discovery → PUT save discovery |
| `test_full_features_flow` | POST generate features (5) → POST suggest features (3) → POST save selected (2) → PATCH approve → PATCH approve |
| `test_full_ears_flow` | POST generate requirements for feature C01 → PUT save requirements |
| `test_cannot_generate_features_without_discovery` | POST generate features sin discovery → 409 PhaseTransitionError |
| `test_cannot_generate_ears_for_unapproved_feature` | POST generate requirements para feature BORRADOR → 409 FeatureNotApprovedError |
| `test_suggest_features_excludes_existing_titles` | Las 3 sugerencias no incluyen títulos ya existentes |

**Comando**: `uv run pytest tests/integration/test_pipeline_flow.py` — 6+ tests verdes (requiere Docker con PostgreSQL).

#### 5.2 Verificación Final

```bash
uv run ruff check .          # Sin errores de lint
uv run ruff format .          # Formato consistente
uv run pyright                # Type check estricto
uv run lint-imports           # Sin violaciones de arquitectura hexagonal
uv run pytest                 # Todos los tests verdes
uv run pytest --cov=kosmo --cov-report=html  # Cobertura >= 60%
```

---

### Diagrama de Dependencias entre Fases

```
Fase 0: Preparación
  │
  ▼
Fase 1: Contracts (phase_contexts, phase_outputs, pipeline_state, orchestrator_ports, phase_errors)
  │
  ▼
Fase 2: Domain (context_builder, phase_validators, sequential_orchestrator, phase_modes, kosmo_agent)
  │
  ├──────────────────────────────┐
  ▼                              ▼
Fase 3: Application           Fase 5: Migraciones BD
  (use cases)                   (pipeline_states, alter features/requirements)
  │                              │
  ▼                              │
Fase 4: Infrastructure           │
  (pipeline_repo, composition,   │
   routers, DTO schemas)         │
  │                              │
  └──────────────┬───────────────┘
                 ▼
         Fase 5: Integración
         (tests e2e, ruff, pyright, lint-imports)
```

---

### Orden de Trabajo Recomendado (Día a Día)

| Día | Fase | Entregable | Verificación |
|-----|------|-----------|-------------|
| 1 | 0 + 1.1-1.3 | Errores + PhaseContexts + PhaseOutputs listos | `pyright` compila `contracts/pipeline/` |
| 2 | 1.4-1.5 + 2.1 | PipelineState + OrchestratorPorts + ContextBuilder listos | Tests de ContextBuilder pasan |
| 3 | 2.2 | Todos los validadores listos | 11+ tests de validadores pasan |
| 4 | 2.3-2.5 | SequentialOrchestrator + PhaseModes + KOSMOAgent listos | ~18 tests de domain pasan |
| 5 | 3.1-3.2 | Use cases de pipeline + discovery listos | Tests de use cases pasan |
| 6 | 3.3-3.4 | Use cases de features + requirements listos | ~17 tests de application pasan |
| 7 | 4.1-4.2 | PipelineRepository + migraciones BD listas | Migración corre, tabla pipeline_states existe |
| 8 | 4.3-4.5 | Composition root + routers + DTO schemas listos | Endpoints responden 200 con NoopLLMClient |
| 9 | 5 | Tests de integración end-to-end | `pytest tests/integration/` verde |
| 10 | 5 | Verificación final (ruff, pyright, lint-imports, coverage) | Todo verde, coverage >= 60% |

---

*Fin de la propuesta técnica.*