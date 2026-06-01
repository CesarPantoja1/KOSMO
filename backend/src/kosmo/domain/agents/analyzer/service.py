import json

from jinja2 import Template

from kosmo.contracts.llm.ports import LLMClient, LLMResponse, PromptTemplate
from kosmo.contracts.sdd.constitution import Constitution
from kosmo.contracts.sdd.discovery import DiscoveryDocument
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.domain.sdd.llm_helpers import extract_json
from kosmo.domain.sdd.validators.ears_validator import validate_requirement

MAX_RETRIES = 3


def _load_template() -> str:
    import os

    path = os.path.join(os.path.dirname(__file__), "prompts", "requirements.j2")
    with open(path, encoding="utf-8") as f:
        return f.read()


async def generate_requirements(
    discovery: DiscoveryDocument,
    constitution: Constitution | None,
    llm_client: LLMClient,
) -> list[EARSRequirement]:
    template_str = _load_template()
    jinja = Template(template_str)

    user_prompt = jinja.render(
        discovery=discovery.model_dump() if discovery else {},
        constitution=constitution.model_dump() if constitution else None,
    )

    prompt = PromptTemplate(
        system_prompt="Eres un ingeniero de requisitos experto en sintaxis EARS.",
        user_prompt=user_prompt,
    )

    response: LLMResponse = await llm_client.complete(
        prompt=prompt,
        temperature=0,
    )

    requirements = [
        EARSRequirement.model_validate(r) for r in json.loads(extract_json(response.content))
    ]

    validated: list[EARSRequirement] = []
    for req in requirements:
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
                    req = EARSRequirement.model_validate_json(retry_response.content)
                    findings = validate_requirement(req)
                    errors = [f for f in findings if f.severity == "error"]
                except Exception:
                    break
            if errors:
                raise Exception(
                    f"Requisito {req.id} no pudo validarse tras {MAX_RETRIES} intentos: "
                    + "; ".join(e.message for e in errors)
                )
        validated.append(req)

    return validated
