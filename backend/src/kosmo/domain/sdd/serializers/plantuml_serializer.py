from kosmo.contracts.sdd.domain_model import DomainModel


def to_plantuml(model: DomainModel) -> str:
    lines: list[str] = ["@startuml", ""]

    for cls in model.classes:
        stereotype = f" <<{cls.stereotype}>>" if cls.stereotype else ""
        abstract = "abstract " if cls.is_abstract else ""
        lines.append(f"{abstract}class {cls.name}{stereotype} {{")
        for attr in cls.attributes:
            static = "{static} " if attr.is_static else ""
            lines.append(f"  {static}{attr.name}: {attr.type}")
        for op in cls.operations:
            params = ", ".join(f"{p['name']}: {p['type']}" for p in op.parameters)
            lines.append(f"  {op.name}({params}): {op.return_type}")
        lines.append("}")
        lines.append("")

    for rel in model.relationships:
        card_src = f' "{rel.source_cardinality}"' if rel.source_cardinality else ""
        card_tgt = f' "{rel.target_cardinality}"' if rel.target_cardinality else ""
        label = f" : {rel.label}" if rel.label else ""
        lines.append(f"{rel.source_class_id}{card_src} --{card_tgt} {rel.target_class_id}{label}")

    lines.append("")
    lines.append("@enduml")
    return "\n".join(lines)
