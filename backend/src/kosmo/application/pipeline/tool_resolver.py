from __future__ import annotations

import contextlib
import json
from typing import Any

import structlog

from kosmo.contracts.llm.ports import LLMClient, PromptTemplate
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.pipeline.knowledge_tool_registry import KnowledgeToolRegistry

_log = structlog.get_logger(__name__)


class ToolResolver:
    """Resuelve que herramientas de conocimiento consultar antes de generar."""

    def __init__(self, llm_client: LLMClient, knowledge_tools: KnowledgeToolRegistry | None = None) -> None:
        self._llm_client = llm_client
        self._knowledge_tools = knowledge_tools

    async def resolve(
        self,
        system_prompt: str,
        base_user_prompt: str,
        project_id: ProjectId | None,
    ) -> tuple[str, list[dict[str, Any]], list[str]]:
        knowledge_context = ""
        tool_invocations: list[dict[str, Any]] = []
        reason_entries: list[str] = []

        if self._knowledge_tools is not None:
            tools_desc = self._knowledge_tools.describe_for_llm()
            if tools_desc:
                tool_system_prompt = system_prompt + "\n\n" + tools_desc
                knowledge_context, tool_invocations = await self.resolve_knowledge_tools(
                    tool_system_prompt, base_user_prompt, project_id
                )
                if knowledge_context:
                    reason_entries.append(
                        "pre_consulta_tools: herramientas consultadas: "
                        + ", ".join(t["tool"] for t in tool_invocations if t.get("found"))
                        or "ninguna encontrada"
                    )
                else:
                    reason_entries.append("pre_consulta_tools: sin consulta de herramientas")
            else:
                reason_entries.append("pre_consulta_tools: sin herramientas registradas")
        else:
            reason_entries.append("pre_consulta_tools: no disponible")

        return knowledge_context, tool_invocations, reason_entries

    async def resolve_knowledge_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        project_id: ProjectId | None,
    ) -> tuple[str, list[dict[str, Any]]]:
        if self._knowledge_tools is None:
            return ("", [])

        if getattr(self._llm_client, "supports_native_tools", False):
            try:
                text, records = await self._llm_client.complete_with_tools(
                    PromptTemplate(
                        system_prompt=system_prompt
                        + (
                            "\n\nPuedes consultar las herramientas disponibles para obtener "
                            "informacion adicional antes de responder. Si tienes suficiente contexto, "
                            "responde listo sin consultar herramientas."
                        ),
                        user_prompt=user_prompt,
                    ),
                    tools=self._knowledge_tools.defs(),
                    tool_handler=self._knowledge_tools.execute,
                    temperature=0.1,
                    max_tokens=2000,
                )
                invocations: list[dict[str, Any]] = [
                    {
                        "tool": r.name,
                        "args": {k: str(v)[:200] for k, v in r.args.items()},
                        "result_snippet": r.result_snippet[:500],
                        "found": "error" not in r.result_snippet.lower()[:20],
                    }
                    for r in records
                ]
                return (text.strip(), invocations)
            except Exception:
                _log.warning("agent.native_tools_failed", exc_info=True)

        tool_prompt = PromptTemplate(
            system_prompt=(
                system_prompt + "\n\nIMPORTANTE: Antes de generar, puedes consultar herramientas de conocimiento "
                "para obtener informacion adicional. Responde SOLO con uno de estos formatos:\n\n"
                '- [TOOL: nombre] {"arg": "valor"}  (para consultar una herramienta)\n'
                "- [CONTINUE]  (si ya tienes suficiente contexto)\n\n"
                "El resultado de la herramienta se te proporcionara y podras continuar."
            ),
            user_prompt=user_prompt,
        )

        collected: list[str] = []
        invocations = []
        for _ in range(3):
            try:
                response = await self._llm_client.complete(
                    prompt=tool_prompt,
                    temperature=0.1,
                    max_tokens=200,
                )
            except Exception:
                _log.warning("agent.text_tools_call_failed", exc_info=True)
                break

            text = response.text.strip()
            if "[CONTINUE]" in text:
                break

            tool_name, tool_args = _parse_tool_call(text)
            if tool_name is None:
                break

            if project_id is not None:
                tool_args.setdefault("project_id", str(project_id))

            result = await self._knowledge_tools.execute(tool_name, tool_args)
            not_found = result is None
            if not_found:
                collected.append(f"[TOOL: {tool_name}] Herramienta no encontrada")
            else:
                collected.append(f"[TOOL: {tool_name}]\n{result}")

            invocations.append(
                {
                    "tool": tool_name,
                    "args": {k: str(v)[:200] for k, v in tool_args.items()},
                    "result_snippet": (result or "herramienta no encontrada")[:500],
                    "found": not not_found,
                }
            )
            tool_prompt = PromptTemplate(
                system_prompt=tool_prompt.system_prompt,
                user_prompt=user_prompt + "\n\n" + collected[-1] + "\n\nResponde [CONTINUE] o [TOOL: ...]",
            )

        return ("\n\n".join(collected), invocations)


def _parse_tool_call(text: str) -> tuple[str | None, dict[str, Any]]:
    marker = "[TOOL:"
    if marker not in text:
        return None, {}

    idx = text.index(marker) + len(marker)
    end_name = text.index("]", idx) if "]" in text[idx:] else len(text)
    tool_name = text[idx:end_name].strip()

    args: dict[str, Any] = {}
    brace_start = text.find("{", end_name)
    if brace_start != -1:
        brace_end = text.find("}", brace_start)
        if brace_end != -1:
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                args = json.loads(text[brace_start : brace_end + 1])

    return tool_name, args
