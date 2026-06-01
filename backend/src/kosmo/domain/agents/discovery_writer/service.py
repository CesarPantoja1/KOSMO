from jinja2 import Template

from kosmo.contracts.llm.ports import LLMClient, LLMResponse, PromptTemplate
from kosmo.contracts.sdd.constitution import Constitution
from kosmo.contracts.sdd.discovery import DiscoveryDocument
from kosmo.domain.sdd.document_converters import (
    discovery_to_markdown,
    markdown_to_document,
)
from kosmo.domain.sdd.llm_helpers import extract_json


def _load_template() -> str:
    import os

    path = os.path.join(os.path.dirname(__file__), "prompts", "discovery.j2")
    with open(path, encoding="utf-8") as f:
        return f.read()


async def generate_discovery(
    project_description: str,
    constitution: Constitution | None,
    llm_client: LLMClient,
    optional_context: str = "",
) -> tuple[DiscoveryDocument, dict]:
    template_str = _load_template()
    jinja = Template(template_str)

    user_prompt = jinja.render(
        project_description=project_description,
        optional_context=optional_context,
        constitution=constitution.model_dump() if constitution else None,
    )

    prompt = PromptTemplate(
        system_prompt="Eres un analista de negocio experto en descubrimiento de productos.",
        user_prompt=user_prompt,
    )

    response: LLMResponse = await llm_client.complete(
        prompt=prompt,
        temperature=0,
    )

    discovery = DiscoveryDocument.model_validate_json(extract_json(response.content))
    markdown = discovery_to_markdown(discovery)
    document_tree = markdown_to_document(markdown)
    return discovery, document_tree
