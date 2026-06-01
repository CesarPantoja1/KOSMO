import json

from jinja2 import Template

from kosmo.contracts.llm.ports import LLMClient, LLMResponse, PromptTemplate
from kosmo.contracts.sdd.discovery import DiscoveryDocument
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.contracts.sdd.ids import RequirementId
from kosmo.contracts.sdd.requirements_document import RequirementsDocument
from kosmo.domain.sdd.document_converters import (
    markdown_to_document,
    requirements_document_to_markdown,
)
from kosmo.domain.sdd.llm_helpers import extract_json
from kosmo.domain.sdd.validators.ears_validator import validate_requirement

MAX_RETRIES = 3


def _load_template() -> str:
    import os

    path = os.path.join(os.path.dirname(__file__), "prompts", "requirements.j2")
    with open(path, encoding="utf-8") as f:
        return f.read()


def _assign_sequential_ids(doc: RequirementsDocument) -> RequirementsDocument:
    counter = 1
    for category in [
        "ubiquitous",
        "event",
        "state",
        "optional",
        "unwanted",
        "complex",
    ]:
        updated: list[EARSRequirement] = []
        for req in getattr(doc, category):
            new_id = RequirementId(f"R-{counter}")
            updated.append(
                EARSRequirement(
                    id=new_id,
                    pattern=req.pattern,
                    trigger=req.trigger,
                    system=req.system,
                    response=req.response,
                    acceptance_criteria=req.acceptance_criteria,
                    source_statement=req.source_statement,
                    traceability=req.traceability,
                )
            )
            counter += 1
        setattr(doc, category, updated)
    return doc


async def generate_feature_requirements(
    feature_title: str,
    feature_description: str,
    discovery: DiscoveryDocument | None,
    llm_client: LLMClient,
) -> tuple[RequirementsDocument, dict]:
    template_str = _load_template()
    jinja = Template(template_str)

    user_prompt = jinja.render(
        feature_title=feature_title,
        feature_description=feature_description,
        discovery=discovery.model_dump() if discovery else None,
    )

    prompt = PromptTemplate(
        system_prompt="Eres un Ingeniero de Requisitos Senior en EARS y analisis de dominio.",
        user_prompt=user_prompt,
    )

    response: LLMResponse = await llm_client.complete(
        prompt=prompt,
        temperature=0,
    )

    raw = json.loads(extract_json(response.content))

    for category in [
        "ubiquitous",
        "event",
        "state",
        "optional",
        "unwanted",
        "complex",
    ]:
        if category in raw:
            cleaned: list[dict[str, object]] = []
            for idx, item in enumerate(raw[category], 1):
                item.pop("id", None)
                item["id"] = f"R-TMP-{idx}"
                if "pattern" not in item:
                    item["pattern"] = category
                cleaned.append(item)
            raw[category] = cleaned

    doc = RequirementsDocument.model_validate(raw)

    for category in [
        "ubiquitous",
        "event",
        "state",
        "optional",
        "unwanted",
        "complex",
    ]:
        validated: list[EARSRequirement] = []
        for req in getattr(doc, category):
            findings = validate_requirement(req)
            errors = [f for f in findings if f.severity == "error"]
            if errors:
                retry_count = 0
                while errors and retry_count < MAX_RETRIES:
                    retry_count += 1
                    error_msgs = [e.message for e in errors]
                    retry_prompt = PromptTemplate(
                        system_prompt=f"Corrige errores: {error_msgs}",
                        user_prompt=req.model_dump_json(),
                    )
                    retry_response = await llm_client.complete(prompt=retry_prompt, temperature=0)
                    try:
                        fixed = json.loads(retry_response.content)
                        fixed.pop("id", None)
                        fixed["id"] = str(req.id)
                        req = EARSRequirement.model_validate(fixed)
                        findings = validate_requirement(req)
                        errors = [f for f in findings if f.severity == "error"]
                    except Exception:
                        break
            validated.append(req)
        setattr(doc, category, validated)

    doc = _assign_sequential_ids(doc)
    markdown = requirements_document_to_markdown(doc, feature_title)
    document_tree = markdown_to_document(markdown)
    return doc, document_tree
