import json

from jinja2 import Template

from kosmo.contracts.llm.ports import LLMClient, LLMResponse, PromptTemplate
from kosmo.contracts.sdd.constitution import Constitution
from kosmo.contracts.sdd.domain_model import DomainModel
from kosmo.contracts.sdd.tasks import Task
from kosmo.domain.sdd.llm_helpers import extract_json
from kosmo.domain.sdd.validators.task_dag_validator import validate_task_dag


def _load_template() -> str:
    import os

    path = os.path.join(os.path.dirname(__file__), "prompts", "tasks.j2")
    with open(path, encoding="utf-8") as f:
        return f.read()


async def decompose_tasks(
    domain_model: DomainModel,
    constitution: Constitution | None,
    llm_client: LLMClient,
) -> list[Task]:
    template_str = _load_template()
    jinja = Template(template_str)

    user_prompt = jinja.render(
        classes=[c.model_dump() for c in domain_model.classes],
        relationships=[r.model_dump() for r in domain_model.relationships],
        boundaries=[b.model_dump() for b in domain_model.boundaries],
        constitution=constitution.model_dump() if constitution else None,
    )

    prompt = PromptTemplate(
        system_prompt="Eres un planificador experto en descomposición de tareas.",
        user_prompt=user_prompt,
    )

    response: LLMResponse = await llm_client.complete(
        prompt=prompt,
        temperature=0,
    )

    tasks = [Task.model_validate(t) for t in json.loads(extract_json(response.content))]

    findings = validate_task_dag(tasks, domain_model)
    errors = [f for f in findings if f.severity == "error"]
    if errors:
        raise Exception("Validación de DAG fallida: " + "; ".join(e.message for e in errors))

    return tasks
