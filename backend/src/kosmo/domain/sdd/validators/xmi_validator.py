from lxml import etree


class ValidationFinding:
    def __init__(self, code: str, severity: str, message: str, field: str = "") -> None:
        self.code = code
        self.severity = severity
        self.message = message
        self.field = field


XMI_NAMESPACE = "http://www.omg.org/spec/XMI/20131001"
UML_NAMESPACE = "http://www.omg.org/spec/UML/20131001"


def validate_xmi(xmi_content: str) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    try:
        root = etree.fromstring(xmi_content.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        findings.append(ValidationFinding("XM001", "error", f"XML inválido: {e}", "xmi"))
        return findings

    root_ns = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""
    if root_ns != XMI_NAMESPACE:
        findings.append(
            ValidationFinding(
                "XM002",
                "warning",
                f"Namespace XMI esperado {XMI_NAMESPACE}, encontrado {root_ns}",
                "xmi",
            )
        )

    packaged_elements = root.findall(f"{{{UML_NAMESPACE}}}Model")
    if not packaged_elements:
        packaged_elements_any = root.findall("{*}Model")
        if not packaged_elements_any:
            findings.append(
                ValidationFinding(
                    "XM003",
                    "warning",
                    "XMI no contiene elementos Model (packagedElement)",
                    "xmi",
                )
            )

    return findings
