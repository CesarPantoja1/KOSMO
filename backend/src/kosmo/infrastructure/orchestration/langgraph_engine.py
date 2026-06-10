from collections.abc import AsyncIterator
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph
from langgraph.types import Command

from kosmo.application.orchestration.kosmo_graph import build_kosmo_graph
from kosmo.config import Settings
from kosmo.contracts.orchestration.graph_deps import GraphDependencies
from kosmo.contracts.sdd.state import KOSMOState
from kosmo.domain.agents.tool_registry import InMemoryToolRegistry
from kosmo.infrastructure.orchestration.tool_handlers import build_sdd_tools


class LangGraphEngine:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._graph: StateGraph | None = None  # type: ignore[no-any-unimported]
        self._compiled: Any = None
        self._checkpointer: AsyncPostgresSaver | None = None
        self._checkpointer_cm: Any = None
        self._deps: GraphDependencies | None = None

    def configure_deps(
        self,
        llm_client: Any,
        preference_repo: Any,
        spec_repo: Any | None = None,
        project_repo: Any | None = None,
        feature_repo: Any | None = None,
    ) -> None:
        registry = InMemoryToolRegistry()
        for tool_def, handler in build_sdd_tools(
            spec_repo=spec_repo,
            project_repo=project_repo,
            feature_repo=feature_repo,
        ):
            registry.register(tool_def, handler)

        self._deps = GraphDependencies(
            llm_client=llm_client,
            preference_repo=preference_repo,
            tool_registry=registry,
        )

    async def _ensure_compiled(self) -> Any:
        if self._compiled is not None:
            return self._compiled

        self._graph = build_kosmo_graph()

        import sys as _sys

        if _sys.platform == "win32":
            from langgraph.checkpoint.memory import MemorySaver

            self._checkpointer = MemorySaver()
        else:
            db_url = self._settings.database_url.get_secret_value()
            db_url = db_url.replace("+asyncpg", "")
            self._checkpointer_cm = AsyncPostgresSaver.from_conn_string(db_url)
            self._checkpointer = await self._checkpointer_cm.__aenter__()
            await self._checkpointer.setup()

        self._compiled = self._graph.compile(checkpointer=self._checkpointer)
        return self._compiled

    def _build_config(self, config: dict[str, Any]) -> dict[str, Any]:
        merged = {**config}
        merged.setdefault("configurable", {})
        merged["configurable"]["deps"] = self._deps
        return merged

    async def invoke(self, state: KOSMOState, config: dict[str, Any]) -> KOSMOState:
        compiled = await self._ensure_compiled()
        merged_config = self._build_config(config)
        result = await compiled.ainvoke(state, merged_config)
        if isinstance(result, dict):
            return KOSMOState.model_validate(result)
        return result

    async def stream(
        self, state: KOSMOState, config: dict[str, Any]
    ) -> AsyncIterator[dict[str, Any]]:
        compiled = await self._ensure_compiled()
        merged_config = self._build_config(config)
        async for chunk in compiled.astream(state, merged_config):
            yield chunk

    async def resume(self, checkpoint_id: str, human_input: dict[str, Any]) -> KOSMOState:
        compiled = await self._ensure_compiled()
        config = {"configurable": {"thread_id": checkpoint_id, "deps": self._deps}}
        result = await compiled.ainvoke(Command(resume=human_input), config)
        if isinstance(result, dict):
            return KOSMOState.model_validate(result)
        return result

    async def close(self) -> None:
        if self._checkpointer_cm is not None:
            await self._checkpointer_cm.__aexit__(None, None, None)
