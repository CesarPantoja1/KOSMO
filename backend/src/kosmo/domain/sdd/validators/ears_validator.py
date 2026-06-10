from __future__ import annotations

import re
from dataclasses import dataclass, field

from kosmo.contracts.sdd.ears import AcceptanceCriterion, EARSPattern, EARSRequirement


class ValidationSeverity:
    BLOCKER = "blocker"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class LeakFinding:
    pattern: str
    matched_text: str
    category: str


@dataclass
class ValidationFinding:
    code: str
    severity: str
    message: str
    field: str = ""


@dataclass
class DimensionScore:
    name: str
    score: float
    max_score: float
    findings: list[str] = field(default_factory=list)


@dataclass
class RequirementScoreCard:
    requirement_id: str
    pattern: str
    overall_score: float
    passed: bool
    dimensions: list[DimensionScore] = field(default_factory=list)
    blocker_findings: list[str] = field(default_factory=list)


@dataclass
class BatchScoreCard:
    total_requirements: int
    passed: int
    failed: int
    overall_score: float
    category_coverage: dict[str, int]
    cards: list[RequirementScoreCard] = field(default_factory=list)
    summary_findings: list[str] = field(default_factory=list)


_TECH_LEAK_PATTERNS: list[tuple[str, str]] = [
    (r"\b(base\s*de\s*datos|bases\s*de\s*datos|database)\b", "base de datos"),
    (
        r"\b(tabla|columna|índice|indice|fila|registro\s+sql|schema)\b",
        "estructura de base de datos",
    ),
    (
        r"\b(sql|nosql|postgres|postgresql|mysql|oracle|mongodb|redis|dynamodb|cassandra|mariadb|sqlite)\b",
        "tecnología de base de datos",
    ),
    (
        r"\b(servidor|contenedor|pod|cluster|load\s*balancer|cdn|proxy\s*inverso)\b",
        "infraestructura",
    ),
    (
        r"\b(cloud|aws|amazon\s*web\s*services|azure|gcp|google\s*cloud|heroku|digital\s*ocean)\b",
        "proveedor cloud",
    ),
    (
        r"\b(api|endpoint|rest|graphql|grpc|soap|websocket|webhook)\b",
        "API o protocolo de comunicación",
    ),
    (
        r"\b(http|https|json|xml|yaml|protobuf|payload|header|status\s*code|código\s*de\s*estado)\b",
        "protocolo o formato de datos",
    ),
    (
        r"\b(react|angular|vue|svelte|next\.?js|nuxt\.?js|django|flask|fastapi|spring|express|node\.?js|laravel|rails)\b",
        "framework o librería",
    ),
    (
        r"\b(python|java|javascript|typescript|golang|rust|c\#|c\+\+|ruby|php|scala|kotlin|swift)\b",
        "lenguaje de programación",
    ),
    (
        r"\b(componente|módulo|clase|método|función|controlador|middleware|interceptor|factory|singleton|repositorio)\b",
        "patrón de código o diseño",
    ),
    (
        r"\b(orm|migraci[oó]n|migration|deploy|ci/cd|pipeline|docker|kubernetes|k8s|helm|terraform)\b",
        "herramienta de desarrollo",
    ),
    (
        r"\b(frontend|backend|front-end|back-end|microservicio|microservice|monolito)\b",
        "arquitectura de software",
    ),
    (r"\b(cach[ée]|cache|redis\s*cache|memcache)\b", "mecanismo de caché"),
    (
        r"\b(jwt|oauth|openid|saml|token\s*de\s*acceso|access\s*token|refresh\s*token|api\s*key)\b",
        "mecanismo de autenticación técnica",
    ),
    (
        r"\b(log|logging|métricas|metrics|tracing|otel|opentelemetry|prometheus|grafana)\b",
        "observabilidad técnica",
    ),
]

_AMBIGUITY_PATTERNS: list[tuple[str, str]] = [
    (r"\br[aá]pido\b(?!\s+(que|en\s+menos|en\s+menor))", '"rápido" sin métrica concreta'),
    (
        r"\bseguro\b(?!\s+(contra|ante|frente|mediante|usando))",
        '"seguro" sin especificar contra qué',
    ),
    (r"\brobusto\b", '"robusto" sin criterio verificable'),
    (r"\bf[áa]cil\s*de\s*usar\b", '"fácil de usar" sin métrica de usabilidad'),
    (r"\bintuitiv[oa]\b", '"intuitivo" sin criterio verificable'),
    (r"\bescalable\b(?!\s+(hasta|para|a))", '"escalable" sin criterio concreto'),
    (r"\beficiente\b(?!\s+(en|consumiendo|procesando))", '"eficiente" sin métrica'),
    (r"\bbuen[oa]\b\s+(rendimiento|performance|experiencia)", '"bueno" sin criterio medible'),
    (r"\bmodern[oa]\b", '"moderno" sin significado verificable'),
    (r"\bóptimo\b|'[oó]ptimo\b", '"óptimo" sin criterio cuantificable'),
    (r"\bmejor\s+posible\b", '"mejor posible" sin definición concreta'),
    (r"\bsiempre\b(?!\s+que)", '"siempre" absoluto no verificable en requisitos funcionales'),
    (r"\bnunca\b", '"nunca" absoluto no verificable'),
]

_CATEGORY_NAMES: dict[str, str] = {
    "ubiquitous": "Ubicuos",
    "event": "Eventos",
    "state": "Estados",
    "optional": "Opcionales",
    "unwanted": "Fallos",
    "complex": "Complejos",
}


def validate_requirement(req: EARSRequirement) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    if not req.id:
        findings.append(
            ValidationFinding("E001", ValidationSeverity.ERROR, "Requisito sin ID", "id")
        )

    if not req.system.strip():
        findings.append(
            ValidationFinding("E002", ValidationSeverity.ERROR, "Campo 'system' vacío", "system")
        )

    if not req.response.strip():
        findings.append(
            ValidationFinding(
                "E003", ValidationSeverity.ERROR, "Campo 'response' vacío", "response"
            )
        )

    if not req.source_statement.strip():
        findings.append(
            ValidationFinding(
                "E004", ValidationSeverity.ERROR, "source_statement vacío", "source_statement"
            )
        )

    if not req.acceptance_criteria:
        findings.append(
            ValidationFinding(
                "E005",
                ValidationSeverity.WARNING,
                "Sin criterios de aceptación",
                "acceptance_criteria",
            )
        )

    leaks = detect_implementation_leak(req.source_statement)
    for leak in leaks:
        findings.append(
            ValidationFinding(
                "E011",
                ValidationSeverity.BLOCKER,
                f"Fuga de implementación: {leak.category} ({leak.matched_text})",
                "source_statement",
            )
        )

    pattern = req.pattern
    text = req.source_statement.lower()

    if pattern == EARSPattern.EVENT:
        if not (text.startswith("when") or " when " in text):
            findings.append(
                ValidationFinding(
                    "E006",
                    ValidationSeverity.ERROR,
                    "Patrón EVENT requiere cláusula WHEN",
                    "source_statement",
                )
            )

    elif pattern == EARSPattern.STATE:
        if not (text.startswith("while") or " while " in text):
            findings.append(
                ValidationFinding(
                    "E007",
                    ValidationSeverity.ERROR,
                    "Patrón STATE requiere cláusula WHILE",
                    "source_statement",
                )
            )

    elif pattern == EARSPattern.OPTIONAL:
        if not (text.startswith("where") or " where " in text):
            findings.append(
                ValidationFinding(
                    "E008",
                    ValidationSeverity.ERROR,
                    "Patrón OPTIONAL requiere cláusula WHERE",
                    "source_statement",
                )
            )

    elif pattern == EARSPattern.UNWANTED:
        if not (text.startswith("if") or " if " in text):
            findings.append(
                ValidationFinding(
                    "E009",
                    ValidationSeverity.ERROR,
                    "Patrón UNWANTED requiere cláusula IF/THEN",
                    "source_statement",
                )
            )

    elif pattern == EARSPattern.UBIQUITOUS and "shall" not in text:
        findings.append(
            ValidationFinding(
                "E010",
                ValidationSeverity.WARNING,
                "Patrón UBIQUITOUS normalmente usa 'shall'",
                "source_statement",
            )
        )

    ambiguities = detect_ambiguity(req.source_statement)
    for amb in ambiguities:
        findings.append(
            ValidationFinding(
                "E012", ValidationSeverity.WARNING, f"Ambigüedad: {amb}", "source_statement"
            )
        )

    return findings


def detect_ears_pattern(statement: str) -> EARSPattern | None:
    normalized = statement.lower().strip()

    markers: list[tuple[EARSPattern, str]] = [
        (EARSPattern.EVENT, "when"),
        (EARSPattern.STATE, "while"),
        (EARSPattern.OPTIONAL, "where"),
        (EARSPattern.UNWANTED, "if"),
    ]
    for pattern, marker in markers:
        if normalized.startswith(marker + " ") or f" {marker} " in normalized:
            return pattern

    if "shall" in normalized or "debe" in normalized.lower():
        return EARSPattern.UBIQUITOUS

    return None


def detect_implementation_leak(text: str) -> list[LeakFinding]:
    findings: list[LeakFinding] = []
    for pattern, category in _TECH_LEAK_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            findings.append(
                LeakFinding(pattern=pattern, matched_text=match.group(0), category=category)
            )
    return findings


def detect_ambiguity(text: str) -> list[str]:
    ambiguities: list[str] = []
    lower = text.lower()
    for pattern, description in _AMBIGUITY_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            ambiguities.append(description)
    return ambiguities


def is_measurable(criterion: AcceptanceCriterion) -> bool:
    text = (
        criterion.description + " " + criterion.expected_result + " " + criterion.scenario
    ).lower()

    measurable_indicators = [
        r"\b(\d+)\s*(segundos|minutos|horas|días|dias|semanas|meses|años|anos)\b",
        r"\b(\d+)\s*(%|por\s*ciento|porcentaje)\b",
        r"\b(menos\s+de|más\s+de|al\s+menos|como\s+máximo|como\s+minimo|no\s+superior\s+a|no\s+inferior\s+a)\b",
        r"\b(muestra|indica|notifica|informa|registra|rechaza|acepta|redirige|bloquea|permite|deniega)\b",
        r"\b(antes\s+de|después\s+de|dentro\s+de|durante)\b",
        r"\b(estado\s+cambia|transición|pasa\s+a)\b",
    ]
    return any(re.search(indicator, text) for indicator in measurable_indicators)


def score_requirement(req: EARSRequirement) -> RequirementScoreCard:
    dimensions: list[DimensionScore] = []

    leaks = detect_implementation_leak(req.source_statement)
    leak_score = 0.0 if leaks else 10.0
    leak_findings = [f"{leak.category}: {leak.matched_text}" for leak in leaks]
    dimensions.append(
        DimensionScore(
            name="pureza_negocio",
            score=leak_score,
            max_score=10.0,
            findings=leak_findings,
        )
    )

    findings = validate_requirement(req)
    errors = [
        f for f in findings if f.severity in (ValidationSeverity.ERROR, ValidationSeverity.BLOCKER)
    ]

    ears_score = 10.0
    pattern_errors = [f for f in errors if f.code in ("E006", "E007", "E008", "E009")]
    if pattern_errors:
        ears_score = 2.0
    elif any(f.code == "E010" for f in findings):
        ears_score = 7.0
    dimensions.append(
        DimensionScore(
            name="correccion_ears",
            score=ears_score,
            max_score=10.0,
            findings=[f.message for f in pattern_errors],
        )
    )

    completeness_score = 10.0
    completeness_findings: list[str] = []
    if not req.source_statement.strip():
        completeness_score -= 4.0
        completeness_findings.append("source_statement vacío")
    if not req.response.strip():
        completeness_score -= 3.0
        completeness_findings.append("response vacío")
    if not req.trigger and req.pattern != EARSPattern.UBIQUITOUS:
        completeness_score -= 2.0
        completeness_findings.append(f"trigger ausente para patrón {req.pattern}")
    if not req.system.strip():
        completeness_score -= 1.0
        completeness_findings.append("system vacío")
    dimensions.append(
        DimensionScore(
            name="completitud",
            score=max(0.0, completeness_score),
            max_score=10.0,
            findings=completeness_findings,
        )
    )

    testability_score = 0.0
    testability_findings: list[str] = []
    if req.acceptance_criteria:
        measurable_count = sum(1 for ac in req.acceptance_criteria if is_measurable(ac))
        total = len(req.acceptance_criteria)
        testability_score = (measurable_count / total) * 10.0
        if measurable_count < total:
            testability_findings.append(f"{total - measurable_count} criterios no son medibles")
    else:
        testability_score = 0.0
        testability_findings.append("Sin criterios de aceptación")
    dimensions.append(
        DimensionScore(
            name="verificabilidad",
            score=testability_score,
            max_score=10.0,
            findings=testability_findings,
        )
    )

    ambiguities = detect_ambiguity(req.source_statement)
    ambiguity_score = 10.0 - (len(ambiguities) * 3.0)
    ambiguity_score = max(0.0, ambiguity_score)
    dimensions.append(
        DimensionScore(
            name="no_ambiguedad",
            score=ambiguity_score,
            max_score=10.0,
            findings=ambiguities,
        )
    )

    coverage_score = 5.0
    coverage_findings: list[str] = []
    if req.trigger:
        coverage_score += 2.0
    else:
        coverage_findings.append("Sin trigger/disparador explícito")
    if len(req.acceptance_criteria) >= 2:
        coverage_score += 2.0
    elif len(req.acceptance_criteria) == 1:
        coverage_score += 1.0
    if req.rationale:
        coverage_score += 1.0
    else:
        coverage_findings.append("Sin justificación de negocio")
    dimensions.append(
        DimensionScore(
            name="cobertura",
            score=min(10.0, coverage_score),
            max_score=10.0,
            findings=coverage_findings,
        )
    )

    weights = {
        "pureza_negocio": 0.30,
        "correccion_ears": 0.25,
        "verificabilidad": 0.20,
        "completitud": 0.10,
        "no_ambiguedad": 0.10,
        "cobertura": 0.05,
    }
    weighted_sum = sum(d.score * weights.get(d.name, 0) for d in dimensions)
    total_weight = sum(weights.get(d.name, 0) for d in dimensions)
    overall = weighted_sum / total_weight if total_weight > 0 else 0.0

    blocker_findings = [f.message for f in findings if f.severity == ValidationSeverity.BLOCKER]
    passed = leak_score > 0.0 and ears_score >= 5.0 and overall >= 6.0

    return RequirementScoreCard(
        requirement_id=str(req.id),
        pattern=req.pattern,
        overall_score=round(overall, 1),
        passed=passed,
        dimensions=dimensions,
        blocker_findings=blocker_findings,
    )


def score_requirements_batch(requirements: list[EARSRequirement]) -> BatchScoreCard:
    cards = [score_requirement(req) for req in requirements]

    passed = sum(1 for c in cards if c.passed)
    failed = len(cards) - passed

    overall = sum(c.overall_score for c in cards) / len(cards) if cards else 0.0

    category_coverage: dict[str, int] = {}
    for req in requirements:
        category_coverage[req.pattern] = category_coverage.get(req.pattern, 0) + 1

    summary_findings: list[str] = []
    for cat_name, _cat_label in _CATEGORY_NAMES.items():
        if cat_name not in category_coverage:
            summary_findings.append(f"Categoría '{_CATEGORY_NAMES[cat_name]}' sin requisitos")

    duplicates = _detect_duplicate_statements(requirements)
    if duplicates:
        summary_findings.append(f"{len(duplicates)} posibles duplicados detectados")

    return BatchScoreCard(
        total_requirements=len(requirements),
        passed=passed,
        failed=failed,
        overall_score=round(overall, 1),
        category_coverage=category_coverage,
        cards=cards,
        summary_findings=summary_findings,
    )


def _detect_duplicate_statements(requirements: list[EARSRequirement]) -> list[tuple[str, str]]:
    statements: dict[str, str] = {}
    duplicates: list[tuple[str, str]] = []
    for req in requirements:
        key = req.source_statement.lower().strip().rstrip(".")
        if key in statements:
            duplicates.append((statements[key], str(req.id)))
        else:
            statements[key] = str(req.id)
    return duplicates
