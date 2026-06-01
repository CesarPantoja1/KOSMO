from kosmo.contracts.sdd.domain_model import DomainModel

XMI_VERSION = "2.5.1"
XMI_NS = "http://www.omg.org/spec/XMI/20131001"
UML_NS = "http://www.omg.org/spec/UML/20131001"


def to_xmi(model: DomainModel) -> str:
    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<xmi:XMI xmlns:xmi="{XMI_NS}" xmlns:uml="{UML_NS}" xmi:version="{XMI_VERSION}">',
        f'  <uml:Model xmi:id="model-{_safe_id("root")}" name="Design">',
        '    <packagedElement xmi:type="uml:Class" xmi:id="root"/>',
    ]

    for cls in model.classes:
        is_abstract = ' isAbstract="true"' if cls.is_abstract else ""
        line = (
            f'    <packagedElement xmi:type="uml:Class" '
            f'xmi:id="{cls.id}" name="{cls.name}"{is_abstract}>'
        )
        lines.append(line)
        for attr in cls.attributes:
            lines.append(
                f'      <ownedAttribute xmi:type="uml:Property" '
                f'name="{attr.name}" visibility="{attr.visibility}" '
                f'type="{attr.type}"/>'
            )
        for op in cls.operations:
            params_xml = ""
            if op.parameters:
                params_xml = " ".join(
                    f'<ownedParameter name="{p["name"]}" type="{p["type"]}"/>'
                    for p in op.parameters
                )
            lines.append(
                f'      <ownedOperation xmi:type="uml:Operation" '
                f'name="{op.name}" visibility="{op.visibility}">'
                f"        {params_xml}"
                f"      </ownedOperation>"
            )
        lines.append("    </packagedElement>")

    for rel in model.relationships:
        lines.append(
            f'    <packagedElement xmi:type="uml:Association" '
            f'xmi:id="{rel.id}" name="{rel.label}">'
            f'      <memberEnd xmi:idref="{rel.source_class_id}"/>'
            f'      <memberEnd xmi:idref="{rel.target_class_id}"/>'
            f"    </packagedElement>"
        )

    lines.append("  </uml:Model>")
    lines.append("</xmi:XMI>")
    return "\n".join(lines)


def _safe_id(name: str) -> str:
    return name.replace(" ", "_").replace("-", "_")
