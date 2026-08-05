from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from kosmo.contracts.agent_memory import (
    AgentMemoryPort,
    KnowledgePattern,
    KnowledgePatternStore,
)
from kosmo.contracts.llm.ports import LLMClient, PromptTemplate
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.sdd.id_generator import IdGenerator

_log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ConsolidateInput:
    sessions_limit: int = 50


class ConsolidateKnowledgePatterns:
    def __init__(
        self,
        memory: AgentMemoryPort,
        pattern_store: KnowledgePatternStore,
        llm_client: LLMClient,
    ) -> None:
        self._memory = memory
        self._pattern_store = pattern_store
        self._llm_client = llm_client

    async def execute(self, input_data: ConsolidateInput) -> dict[str, int]:
        sessions = await self._memory.list_recent_sessions_global(limit=input_data.sessions_limit)
        completed = [s for s in sessions if s.is_completed]
        by_phase: dict[SpecPhase, list[str]] = {}
        for s in completed:
            snippet = s.reflection or s.user_instructions or ""
            if snippet.strip():
                by_phase.setdefault(s.phase, []).append(snippet)

        result: dict[str, int] = {}
        for phase, snippets in by_phase.items():
            if len(snippets) < 3:
                continue
            patterns = await self._synthesize(phase, snippets)
            await self._pattern_store.replace_patterns(phase, patterns)
            if patterns:
                result[phase.value] = len(patterns)

        return result

    async def _synthesize(self, phase: SpecPhase, snippets: list[str]) -> list[KnowledgePattern]:
        context = "\n".join(f"- {s}" for s in snippets if s.strip())
        prompt = PromptTemplate(
            system_prompt=(
                "Eres un analista de patrones. Tu tarea es extraer practicas recurrentes "
                "o errores repetidos a partir de reflexiones del agente en sesiones "
                f"de fase {phase.value}. Devuelve un JSON con la clave 'patterns', "
                "cada item con 'pattern' (texto) y 'support' (numero de reflexiones "
                "que respaldan el patron, estimado). Maximo 5 patrones."
            ),
            user_prompt=f"Reflexiones:\n\n{context}",
        )
        try:
            response = await self._llm_client.complete(prompt, temperature=0.2, max_tokens=2000)
            import json

            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            data: Any = json.loads(text)  # type: ignore[reportAny]
            raw: list[dict[str, object]] = (  # type: ignore[reportUnknownVariableType]
                data.get("patterns", []) if isinstance(data, dict) else []  # type: ignore[reportUnknownMemberType]
            )
            return [
                KnowledgePattern(
                    pattern_id=IdGenerator.generate("knowledge_pattern"),
                    phase=phase,
                    pattern_text=str(p.get("pattern", "")),  # type: ignore[reportUnknownMemberType,reportUnknownArgumentType]
                    support_count=int(p.get("support", 1)),  # type: ignore[reportUnknownMemberType,reportUnknownArgumentType]
                )
                for p in raw  # type: ignore[reportUnknownVariableType]
                if isinstance(p, dict) and p.get("pattern")  # type: ignore[reportUnknownMemberType]
            ]
        except Exception:
            _log.warning("knowledge.consolidate_synthesize_failed", phase=phase.value, exc_info=True)
            return []
