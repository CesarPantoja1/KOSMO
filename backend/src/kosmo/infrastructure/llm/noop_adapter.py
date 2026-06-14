from __future__ import annotations

import json

from kosmo.contracts.llm.ports import LLMResponse, LLMUsage, PromptTemplate

_DISCOVERY_DOC = "\n\n".join(
    f"## {section}\n\nContenido de ejemplo para la seccion de {section.lower()}."
    for section in [
        "Vision del producto",
        "Espacio del problema",
        "Actores",
        "Propuesta de valor",
        "Casos de uso",
        "Capacidades principales",
        "Reglas de negocio",
        "Atributos de calidad",
        "Alcance",
    ]
)

_FEATURES = [
    {
        "number": i,
        "title": f"Caracteristica {i}",
        "description": f"Descripcion 4W de la caracteristica {i}",
        "slug": f"caracteristica-{i}",
        "rationale": f"Rationale de la caracteristica {i}",
        "inferred_from": ["Vision del producto"],
    }
    for i in range(1, 6)
]

_REQUIREMENTS = [
    {
        "pattern": "ubiquitous",
        "feature_number": 1,
        "requirement_number": 1,
        "trigger": "El sistema siempre",
        "system": "El sistema",
        "response": "debe gestionar los datos de forma segura",
        "source_statement": "El sistema shall gestionar los datos de forma segura",
        "rationale": "Requisito fundamental de seguridad",
        "traceability": ["C01"],
        "acceptance_criteria": [
            {
                "given": "un usuario autenticado",
                "when": "accede a sus datos",
                "then": "los datos se muestran correctamente",
            }
        ],
    }
]

_NOOP_RESPONSE = json.dumps(
    {
        "document": _DISCOVERY_DOC,
        "features": _FEATURES,
        "requirements": _REQUIREMENTS,
    }
)


class NoopLLMClient:
    """Adapter de desarrollo que retorna datos de ejemplo para todas las fases.

    Devuelve siempre la misma respuesta combinada que incluye ``document``,
    ``features`` y ``requirements``. Cada ``PhaseMode.validate_output``
    extrae la clave que necesita, haciendo que el adapter funcione
    uniformemente para discovery, características y requisitos sin
    lógica de detección de fase.
    """

    async def complete(
        self,
        prompt: PromptTemplate,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        return LLMResponse(
            text=_NOOP_RESPONSE,
            usage=LLMUsage(prompt_tokens=10, completion_tokens=100, total_tokens=110),
            model="noop",
        )

    async def complete_json(
        self,
        prompt: PromptTemplate,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        return await self.complete(prompt=prompt, temperature=temperature, max_tokens=max_tokens)
