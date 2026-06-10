from dataclasses import dataclass

from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.memory.repositories import UserPreferenceRepository
from kosmo.contracts.orchestration.tools import ToolRegistry


@dataclass(frozen=True, slots=True)
class GraphDependencies:
    llm_client: LLMClient
    preference_repo: UserPreferenceRepository | None = None
    tool_registry: ToolRegistry | None = None
