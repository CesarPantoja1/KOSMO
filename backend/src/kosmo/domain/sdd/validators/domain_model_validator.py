from kosmo.contracts.sdd.domain_model import DomainModel


class ValidationFinding:
    def __init__(self, code: str, severity: str, message: str, field: str = "") -> None:
        self.code = code
        self.severity = severity
        self.message = message
        self.field = field


def validate_domain_model(model: DomainModel) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    class_ids = {c.id for c in model.classes}
    if len(class_ids) < len(model.classes):
        findings.append(ValidationFinding("DM001", "error", "IDs de clase duplicados", "classes"))

    rel_ids = {r.id for r in model.relationships}
    if len(rel_ids) < len(model.relationships):
        findings.append(
            ValidationFinding("DM002", "error", "IDs de relación duplicados", "relationships")
        )

    for rel in model.relationships:
        if rel.source_class_id not in class_ids:
            findings.append(
                ValidationFinding(
                    "DM003",
                    "error",
                    f"Relación {rel.id}: source_class_id '{rel.source_class_id}' no existe",
                    "relationships",
                )
            )
        if rel.target_class_id not in class_ids:
            findings.append(
                ValidationFinding(
                    "DM004",
                    "error",
                    f"Relación {rel.id}: target_class_id '{rel.target_class_id}' no existe",
                    "relationships",
                )
            )

        if not rel.source_cardinality and not rel.target_cardinality:
            findings.append(
                ValidationFinding(
                    "DM005",
                    "warning",
                    f"Relación {rel.id}: sin cardinalidad declarada",
                    "relationships",
                )
            )

    boundary_ids = {b.name for b in model.boundaries}
    if len(boundary_ids) < len(model.boundaries):
        findings.append(
            ValidationFinding("DM006", "error", "Nombres de frontera duplicados", "boundaries")
        )

    return findings
