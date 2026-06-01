from kosmo.contracts.sdd.ears import EARSPattern, EARSRequirement


class ValidationFinding:
    def __init__(self, code: str, severity: str, message: str, field: str = "") -> None:
        self.code = code
        self.severity = severity
        self.message = message
        self.field = field


def validate_requirement(req: EARSRequirement) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    if not req.id:
        findings.append(ValidationFinding("E001", "error", "Requisito sin ID", "id"))

    if not req.system.strip():
        findings.append(ValidationFinding("E002", "error", "Campo 'system' vacío", "system"))

    if not req.response.strip():
        findings.append(ValidationFinding("E003", "error", "Campo 'response' vacío", "response"))

    if not req.source_statement.strip():
        findings.append(
            ValidationFinding("E004", "error", "source_statement vacío", "source_statement")
        )

    if not req.acceptance_criteria:
        findings.append(
            ValidationFinding(
                "E005", "warning", "Sin criterios de aceptación", "acceptance_criteria"
            )
        )

    pattern = req.pattern
    text = req.source_statement.lower()

    if pattern == EARSPattern.EVENT:
        if not (text.startswith("when") or " when " in text):
            findings.append(
                ValidationFinding(
                    "E006",
                    "error",
                    "Patrón EVENT requiere cláusula WHEN",
                    "source_statement",
                )
            )

    elif pattern == EARSPattern.STATE:
        if not (text.startswith("while") or " while " in text):
            findings.append(
                ValidationFinding(
                    "E007",
                    "error",
                    "Patrón STATE requiere cláusula WHILE",
                    "source_statement",
                )
            )

    elif pattern == EARSPattern.OPTIONAL:
        if not (text.startswith("where") or " where " in text):
            findings.append(
                ValidationFinding(
                    "E008",
                    "error",
                    "Patrón OPTIONAL requiere cláusula WHERE",
                    "source_statement",
                )
            )

    elif pattern == EARSPattern.UNWANTED:
        if not (text.startswith("if") or " if " in text):
            findings.append(
                ValidationFinding(
                    "E009",
                    "error",
                    "Patrón UNWANTED requiere cláusula IF",
                    "source_statement",
                )
            )

    elif pattern == EARSPattern.UBIQUITOUS and "shall" not in text:
        findings.append(
            ValidationFinding(
                "E010",
                "warning",
                "Patrón UBIQUITOUS normalmente usa 'shall'",
                "source_statement",
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
