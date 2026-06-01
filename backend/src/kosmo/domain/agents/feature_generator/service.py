import json

from jinja2 import Template

from kosmo.contracts.llm.ports import LLMClient, LLMResponse, PromptTemplate
from kosmo.contracts.sdd.feature import Feature, FeatureStatus
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.domain.sdd.document_converters import slugify_spanish
from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.domain.sdd.llm_helpers import extract_json


def _make_feature(project_id: ProjectId, title: str, description: str) -> Feature:
    return Feature(
        id=FeatureId(IdGenerator.generate("feature")),
        project_id=project_id,
        title=title,
        slug=slugify_spanish(title, max_length=60),
        description=description,
        status=FeatureStatus.BORRADOR,
    )


def _load_template(name: str) -> str:
    import os

    path = os.path.join(os.path.dirname(__file__), "prompts", f"{name}.j2")
    with open(path, encoding="utf-8") as f:
        return f.read()


async def generate_features_from_discovery(
    project_id: ProjectId,
    llm_client: LLMClient,
    discovery_markdown: str = "",
) -> list[Feature]:
    template_str = _load_template("features")
    jinja = Template(template_str)

    user_prompt = jinja.render(
        discovery_markdown=discovery_markdown,
    )

    prompt = PromptTemplate(
        system_prompt="Eres un analista de producto experto en descomposicion de capacidades.",
        user_prompt=user_prompt,
    )

    response: LLMResponse = await llm_client.complete(
        prompt=prompt,
        temperature=0.3,
    )

    raw_features = json.loads(extract_json(response.content))
    features: list[Feature] = []
    for rf in raw_features:
        features.append(_make_feature(project_id, rf["title"], rf["description"]))

    return features


async def improve_feature_description(
    feature: Feature,
    discovery_markdown: str,
    llm_client: LLMClient,
) -> Feature:
    template_str = _load_template("improve")
    jinja = Template(template_str)

    user_prompt = jinja.render(
        feature=feature.model_dump(),
        discovery_markdown=discovery_markdown,
    )

    prompt = PromptTemplate(
        system_prompt="Eres un analista de producto experto en refinar caracteristicas de negocio.",
        user_prompt=user_prompt,
    )

    response: LLMResponse = await llm_client.complete(
        prompt=prompt,
        temperature=0.3,
    )

    data = json.loads(extract_json(response.content))
    return Feature(
        id=feature.id,
        project_id=feature.project_id,
        title=data["title"],
        description=data["description"],
        status=feature.status,
        created_at=feature.created_at,
    )


async def suggest_feature_from_idea(
    idea: str,
    project_id: ProjectId,
    llm_client: LLMClient,
    discovery_markdown: str = "",
) -> Feature:
    template_str = _load_template("suggest_from_idea")
    jinja = Template(template_str)

    user_prompt = jinja.render(
        idea=idea,
        discovery_markdown=discovery_markdown if discovery_markdown else None,
    )

    prompt = PromptTemplate(
        system_prompt=(
            "Eres un analista de producto experto en formalizar ideas del usuario "
            "en caracteristicas de negocio bien definidas."
        ),
        user_prompt=user_prompt,
    )

    response: LLMResponse = await llm_client.complete(
        prompt=prompt,
        temperature=0.3,
    )

    data = json.loads(extract_json(response.content))
    return _make_feature(project_id, data["title"], data["description"])


async def suggest_alternative_features(
    project_id: ProjectId,
    llm_client: LLMClient,
    discovery_markdown: str = "",
) -> list[Feature]:
    template_str = _load_template("alternatives")
    jinja = Template(template_str)

    user_prompt = jinja.render(
        discovery_markdown=discovery_markdown,
    )

    prompt = PromptTemplate(
        system_prompt="Eres un analista de producto creativo experto en funcionalidades.",
        user_prompt=user_prompt,
    )

    response: LLMResponse = await llm_client.complete(
        prompt=prompt,
        temperature=0.7,
    )

    raw_features = json.loads(extract_json(response.content))
    suggestions: list[Feature] = []
    for rf in raw_features[:5]:
        suggestions.append(_make_feature(project_id, rf["title"], rf["description"]))

    return suggestions
