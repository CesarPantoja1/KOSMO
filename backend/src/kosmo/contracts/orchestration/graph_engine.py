from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from kosmo.contracts.sdd.state import KOSMOState


@runtime_checkable
class GraphEngine(Protocol):
    async def invoke(self, state: KOSMOState, config: dict[str, Any]) -> KOSMOState: ...
    async def stream(
        self, state: KOSMOState, config: dict[str, Any]
    ) -> AsyncIterator[dict[str, Any]]: ...
    async def resume(self, checkpoint_id: str, human_input: dict[str, Any]) -> KOSMOState: ...
