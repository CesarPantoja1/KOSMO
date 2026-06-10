import difflib
from typing import Any

from kosmo.contracts.llm.ports import LLMClient, PromptTemplate
from kosmo.contracts.memory.repositories import UserPreferenceRepository
from kosmo.contracts.memory.user_preference import UserPreference
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.domain.sdd.document_converters import document_to_markdown
from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.domain.sdd.llm_helpers import extract_json


def delta_extractor(
    original_document: dict[str, Any],
    corrected_document: dict[str, Any],
) -> dict[str, Any]:
    original_md = document_to_markdown(original_document)
    corrected_md = document_to_markdown(corrected_document)

    diff_lines = list(
        difflib.unified_diff(
            original_md.splitlines(keepends=True),
            corrected_md.splitlines(keepends=True),
            fromfile="original",
            tofile="corrected",
        )
    )

    added_count = sum(
        1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
    )
    removed_count = sum(
        1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
    )

    return {
        "diff_text": "".join(diff_lines),
        "original_md": original_md,
        "corrected_md": corrected_md,
        "added_lines": added_count,
        "removed_lines": removed_count,
    }


async def rule_inferencer(
    delta: dict[str, Any],
    _document_type: str,
    llm_client: LLMClient,
) -> list[dict[str, Any]]:
    if delta["added_lines"] == 0 and delta["removed_lines"] == 0:
        return []

    prompt = PromptTemplate(
        system_prompt=(
            "Eres un analista de patrones de edicion. Tu tarea es identificar "
            "reglas de estilo y preferencias implicitas en las correcciones "
            "que un usuario hizo sobre un documento generado por IA."
        ),
        user_prompt=f"""## Documento original (IA)
{delta["original_md"][:3000]}

## Documento corregido (Usuario)
{delta["corrected_md"][:3000]}

## Instrucciones
Compara ambos documentos e identifica patrones de edicion que revelen preferencias del usuario.
Extrae reglas accionables que puedan aplicarse en futuras generaciones.

Ejemplos de reglas:
- "El usuario prefiere listas numeradas en lugar de parrafos para instrucciones tecnicas"
- "El usuario prefiere verbos en imperativo para casos de uso"
- "El usuario evita jerga tecnica en secciones de negocio"

Para cada regla identificada, proporciona:
1. rule_text: la regla en lenguaje natural (1-2 oraciones)
2. corpus: 2-4 palabras clave del dominio
3. context_snippet: la frase del documento original que fue modificada (max 200 chars)

Responde en JSON:
```json
[
  {{
    "rule_text": "...",
    "corpus": ["tag1", "tag2"],
    "context_snippet": "..."
  }}
]
```

Si no identificas patrones claros, responde con un array vacio [].""",
    )

    response = await llm_client.complete(prompt=prompt, temperature=0.3)
    data = extract_json(response.content)
    return data if isinstance(data, list) else []


async def preference_store(
    rules: list[dict[str, Any]],
    user_id: str,
    project_id: ProjectId,
    document_type: str,
    preference_repo: UserPreferenceRepository,
) -> list[UserPreference]:
    stored: list[UserPreference] = []
    for rule in rules:
        pref = UserPreference(
            id=IdGenerator.generate("preference"),
            user_id=user_id,
            project_id=project_id,
            document_type=document_type,
            rule_text=rule.get("rule_text", ""),
            corpus=rule.get("corpus", []),
            context_snippet=rule.get("context_snippet", ""),
        )
        await preference_repo.add(pref)
        stored.append(pref)
    return stored


async def conflict_resolver(
    new_rules: list[dict[str, Any]],
    user_id: str,
    project_id: ProjectId,
    preference_repo: UserPreferenceRepository,
) -> list[dict[str, Any]]:
    existing = await preference_repo.get_by_user(user_id=user_id, project_id=project_id, limit=100)

    existing_texts = {pref.rule_text.lower().strip() for pref in existing}

    resolved: list[dict[str, Any]] = []
    for rule in new_rules:
        rule_text = rule.get("rule_text", "").lower().strip()
        if rule_text not in existing_texts:
            resolved.append(rule)
        else:
            resolved.append({**rule, "duplicate": True})

    return resolved
