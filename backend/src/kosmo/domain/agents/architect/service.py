import json

from jinja2 import Template

from kosmo.contracts.llm.ports import LLMClient, LLMResponse, PromptTemplate
from kosmo.contracts.sdd.constitution import Constitution
from kosmo.contracts.sdd.domain_model import DomainModel
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.domain.sdd.llm_helpers import extract_json
from kosmo.domain.sdd.serializers.plantuml_serializer import to_plantuml
from kosmo.domain.sdd.serializers.xmi_serializer import to_xmi


def _load_template() -> str:
    import os

    path = os.path.join(os.path.dirname(__file__), "prompts", "design.j2")
    with open(path, encoding="utf-8") as f:
        return f.read()


async def generate_design(
    requirements: list[EARSRequirement],
    constitution: Constitution | None,
    llm_client: LLMClient,
) -> DomainModel:
    template_str = _load_template()
    jinja = Template(template_str)

    user_prompt = jinja.render(
        requirements=[r.model_dump() for r in requirements],
        constitution=constitution.model_dump() if constitution else None,
    )

    prompt = PromptTemplate(
        system_prompt="Eres un arquitecto de software experto en DDD.",
        user_prompt=user_prompt,
    )

    response: LLMResponse = await llm_client.complete(
        prompt=prompt,
        temperature=0,
    )

    model = DomainModel.model_validate(json.loads(extract_json(response.content)))
    model.plantuml = to_plantuml(model)
    model.xmi = to_xmi(model)
    return model
