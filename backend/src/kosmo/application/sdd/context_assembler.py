from kosmo.contracts.llm.ports import PromptTemplate
from kosmo.contracts.sdd.constitution import Constitution
from kosmo.contracts.sdd.discovery import DiscoveryDocument
from kosmo.contracts.sdd.tasks import Task


class ContextAssembler:
    def __init__(self) -> None:
        pass

    def build_for_discovery(
        self,
        description: str,
        _constitution: Constitution | None,
    ) -> PromptTemplate:
        return PromptTemplate(
            system_prompt="Eres un analista de negocio experto en descubrimiento de productos.",
            user_prompt=f"Descripcion del proyecto: {description}",
        )

    def build_for_requirements(
        self,
        discovery: DiscoveryDocument,
        _constitution: Constitution | None,
    ) -> PromptTemplate:
        return PromptTemplate(
            system_prompt="Eres un ingeniero de requisitos experto en EARS.",
            user_prompt=f"Descubrimiento: {discovery.vision}",
        )

    def build_for_task(
        self,
        task: Task,
        design_dump: str,
        upstream_notes: list[str] | None = None,
    ) -> PromptTemplate:
        notes_str = "\n".join(upstream_notes) if upstream_notes else ""
        return PromptTemplate(
            system_prompt="Eres un desarrollador experto.",
            user_prompt=f"Task: {task.title}\nDesign: {design_dump}\nNotes: {notes_str}",
        )
