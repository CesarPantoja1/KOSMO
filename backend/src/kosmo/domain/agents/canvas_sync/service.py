import json

from jinja2 import Template
from pydantic import BaseModel

from kosmo.contracts.llm.ports import LLMClient, LLMResponse, PromptTemplate
from kosmo.contracts.sdd.domain_model import DomainModel


class CanvasEdit(BaseModel):
    change_type: str
    class_id: str | None = None
    requirement_id: str | None = None
    new_value: dict[str, object] | None = None
    instruction: str = ""


class ChangeDelta(BaseModel):
    added_classes: list[str] = []
    removed_classes: list[str] = []
    modified_classes: list[str] = []
    affected_requirements: list[str] = []
    affected_tasks: list[str] = []


def _load_template() -> str:
    import os

    path = os.path.join(os.path.dirname(__file__), "prompts", "canvas_sync.j2")
    with open(path, encoding="utf-8") as f:
        return f.read()


async def apply_canvas_edit(
    edit: CanvasEdit,
    current_model: DomainModel,
    llm_client: LLMClient,
) -> tuple[DomainModel, ChangeDelta]:
    template_str = _load_template()
    jinja = Template(template_str)

    user_prompt = jinja.render(
        edit=edit.model_dump(),
        current_model=current_model.model_dump(),
    )

    prompt = PromptTemplate(
        system_prompt="Eres un sincronizador de modelos de dominio.",
        user_prompt=user_prompt,
    )

    response: LLMResponse = await llm_client.complete(
        prompt=prompt,
        temperature=0,
    )

    result = json.loads(response.content)
    updated_model = DomainModel.model_validate(result["updated_model"])
    delta = ChangeDelta.model_validate(result["delta"])
    return updated_model, delta
