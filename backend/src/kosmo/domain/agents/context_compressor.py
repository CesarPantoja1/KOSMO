from __future__ import annotations

from kosmo.contracts.llm.ports import LLMClient, PromptTemplate
from kosmo.contracts.sdd.state import KOSMOState

TOKEN_THRESHOLD = 8000


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def should_compress(state: KOSMOState) -> bool:
    history_text = _build_history_text(state)
    return estimate_tokens(history_text) > TOKEN_THRESHOLD


async def compress_context(
    state: KOSMOState,
    llm_client: LLMClient,
) -> str | None:
    history_text = _build_history_text(state)
    if estimate_tokens(history_text) <= TOKEN_THRESHOLD:
        return None

    prompt = PromptTemplate(
        system_prompt=(
            "Eres un compresor de contexto. Resume la siguiente informacion "
            "preservando SOLO los hechos operacionalmente relevantes: "
            "decisiones tomadas, errores encontrados, preferencias del usuario, "
            "y contenido generado. Descarta ruido y repeticiones."
        ),
        user_prompt=(
            f"## Historial\n{history_text[:6000]}\n\nGenera un resumen conciso (max 500 tokens)."
        ),
    )

    try:
        response = await llm_client.complete(prompt=prompt, temperature=0, max_tokens=1024)
        return response.content
    except Exception:
        return history_text[:4000]


def _build_history_text(state: KOSMOState) -> str:
    parts: list[str] = []

    if state.critique_log:
        parts.append("## Cronicas de criticos")
        for c in state.critique_log[-10:]:
            parts.append(f"- [{c.severity}] {c.agent_id}: {c.message}")

    if state.errors:
        parts.append("## Errores")
        for e in state.errors[-5:]:
            parts.append(f"- {e}")

    if state.tool_call_history:
        parts.append("## Herramientas invocadas")
        for tc in state.tool_call_history[-20:]:
            parts.append(f"- {tc.agent_id}/{tc.tool_name}: {tc.result}")

    generated = state.shared_scratchpad.get("generated_document_md", "")
    if generated:
        parts.append(f"## Contenido generado\n{str(generated)[:2000]}")

    prefs = state.shared_scratchpad.get("preference_retriever_output", {})
    if isinstance(prefs, dict) and prefs.get("preferences_prompt"):
        parts.append(
            f"## Preferencias del Usuario (PRESERVAR)\n{prefs['preferences_prompt'][:1500]}"
        )

    return "\n".join(parts)
