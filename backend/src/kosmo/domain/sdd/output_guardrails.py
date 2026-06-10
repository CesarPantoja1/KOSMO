import re
import unicodedata

from kosmo.contracts.sdd.guardrails import (
    DISCOVERY_SECTIONS,
    MIN_SECTION_LENGTH,
    PROHIBITED_TERMS,
    GuardrailResult,
    GuardrailViolation,
)


def _contains_prohibited_terms(text: str) -> list[str]:
    lower = text.lower()
    found: list[str] = []
    for term in PROHIBITED_TERMS:
        if term in lower:
            found.append(term)
    return found


def validate_discovery_output(data: dict) -> GuardrailResult:
    violations: list[GuardrailViolation] = []

    if not isinstance(data, dict):
        return GuardrailResult(
            is_valid=False,
            violations=[
                GuardrailViolation(
                    field="root",
                    message="El output no es un diccionario valido",
                    severity="blocker",
                )
            ],
            summary="Output no es un diccionario",
        )

    missing_sections: list[str] = []
    empty_sections: list[str] = []
    short_sections: list[str] = []

    for section in DISCOVERY_SECTIONS:
        value = data.get(section)
        if value is None:
            missing_sections.append(section)
            continue
        if not isinstance(value, str):
            missing_sections.append(section)
            continue
        stripped = value.strip()
        if not stripped:
            empty_sections.append(section)
        elif len(stripped) < MIN_SECTION_LENGTH:
            short_sections.append(section)

    for section in missing_sections:
        violations.append(
            GuardrailViolation(
                field=section,
                message=f"Seccion requerida '{section}' ausente",
                severity="blocker",
            )
        )

    for section in empty_sections:
        violations.append(
            GuardrailViolation(
                field=section,
                message=f"Seccion '{section}' esta vacia",
                severity="blocker",
            )
        )

    for section in short_sections:
        violations.append(
            GuardrailViolation(
                field=section,
                message=(
                    f"Seccion '{section}' es demasiado corta ({MIN_SECTION_LENGTH} car. minimo)"
                ),
                severity="warning",
            )
        )

    all_text = " ".join(str(data.get(s, "")) for s in DISCOVERY_SECTIONS)
    prohibited = _contains_prohibited_terms(all_text)
    for term in prohibited:
        violations.append(
            GuardrailViolation(
                field="prohibited_terms",
                message=f"Termino prohibido detectado: '{term}'",
                severity="blocker",
            )
        )

    populated_sections = [
        s for s in DISCOVERY_SECTIONS if isinstance(data.get(s), str) and data[s].strip()
    ]
    sanitized: dict = {}
    for s in DISCOVERY_SECTIONS:
        val = data.get(s, "")
        sanitized[s] = val if isinstance(val, str) else ""

    is_valid = not any(v.is_blocker for v in violations)
    return GuardrailResult(
        is_valid=is_valid,
        violations=violations,
        sanitized=sanitized,
        summary=(
            f"{len(populated_sections)}/{len(DISCOVERY_SECTIONS)} "
            f"secciones pobladas, {len(violations)} violaciones"
        ),
    )


def validate_features_output(
    data: list[dict],
    existing_titles: list[str],
) -> GuardrailResult:
    """Valida output de /suggest: exactamente 3 sugerencias."""
    return _validate_features_inner(data, existing_titles, expected_count=3, label="sugerencias")


def validate_generate_features_output(
    data: list[dict],
    existing_titles: list[str],
) -> GuardrailResult:
    """Valida output de /generate: exactamente 5 caracteristicas."""
    return _validate_features_inner(data, existing_titles, expected_count=5, label="caracteristicas")


def _validate_features_inner(
    data: list[dict],
    existing_titles: list[str],
    expected_count: int,
    label: str,
) -> GuardrailResult:
    violations: list[GuardrailViolation] = []

    if not isinstance(data, list):
        return GuardrailResult(
            is_valid=False,
            violations=[
                GuardrailViolation(
                    field="root",
                    message="El output no es una lista valida",
                    severity="blocker",
                )
            ],
            summary="Output no es una lista",
        )

    if len(data) != expected_count:
        violations.append(
            GuardrailViolation(
                field=label,
                message=f"Se requieren exactamente {expected_count} {label}, se recibieron {len(data)}",
                severity="blocker",
            )
        )

    existing_lower = {t.strip().lower() for t in existing_titles}

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            violations.append(
                GuardrailViolation(
                    field=f"suggestions[{i}]",
                    message="La sugerencia no es un diccionario",
                    severity="blocker",
                )
            )
            continue

        title = item.get("title", "")
        description = item.get("description", "")
        rationale = item.get("rationale", "")

        if not title or len(title.strip()) < 3:
            violations.append(
                GuardrailViolation(
                    field=f"suggestions[{i}].title",
                    message=f"Titulo vacio o demasiado corto: '{title}'",
                    severity="blocker",
                )
            )

        if not description or len(description.strip()) < 20:
            violations.append(
                GuardrailViolation(
                    field=f"suggestions[{i}].description",
                    message=(
                        f"Descripcion vacia o demasiado corta (min 20 car.): '{description[:50]}'"
                    ),
                    severity="blocker",
                )
            )

        if not rationale or len(rationale.strip()) < 10:
            violations.append(
                GuardrailViolation(
                    field=f"suggestions[{i}].rationale",
                    message=f"Rationale vacio o demasiado corto (min 10 car.): '{rationale[:50]}'",
                    severity="warning",
                )
            )

        title_lower = title.strip().lower()
        if title_lower in existing_lower:
            violations.append(
                GuardrailViolation(
                    field=f"suggestions[{i}].title",
                    message=f"Sugerencia duplica feature existente: '{title}'",
                    severity="blocker",
                )
            )

        for existing_title in existing_titles:
            if _is_paraphrase(title_lower, existing_title.lower().strip()):
                violations.append(
                    GuardrailViolation(
                        field=f"suggestions[{i}].title",
                        message=(
                            f"Sugerencia '{title}' es parafrasis "
                            f"de feature existente '{existing_title}'"
                        ),
                        severity="blocker",
                    )
                )

        prohibited = _contains_prohibited_terms(f"{title} {description}")
        for term in prohibited:
            violations.append(
                GuardrailViolation(
                    field=f"suggestions[{i}]",
                    message=f"Termino prohibido en sugerencia: '{term}'",
                    severity="warning",
                )
            )

    sanitized = [
        {
            "title": item.get("title", ""),
            "description": item.get("description", ""),
            "rationale": item.get("rationale", ""),
            "inferred_from": item.get("inferred_from", []),
            "category": item.get("category", ""),
        }
        for item in data
        if isinstance(item, dict) and item.get("title") and item.get("description")
    ]

    is_valid = not any(v.is_blocker for v in violations)
    return GuardrailResult(
        is_valid=is_valid,
        violations=violations,
        sanitized=sanitized,
        summary=f"{len(data)} sugerencias, {len(violations)} violaciones",
    )


_CHUNKS_PARAPHRASE: set[str] = {
    "gestion",
    "administrar",
    "manejo",
    "manejar",
    "administracion",
    "control",
    "operacion",
}


def _is_paraphrase(suggested: str, existing: str) -> bool:
    if suggested == existing:
        return True
    suggested_norm = _normalize_for_paraphrase(suggested)
    existing_norm = _normalize_for_paraphrase(existing)
    if suggested_norm == existing_norm:
        return True
    for chunk in _CHUNKS_PARAPHRASE:
        suggested_norm = suggested_norm.replace(chunk, "gestion")
        existing_norm = existing_norm.replace(chunk, "gestion")
    return suggested_norm == existing_norm


def _normalize_for_paraphrase(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower().strip())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    articles: set[str] = {
        "el",
        "la",
        "los",
        "las",
        "de",
        "del",
        "en",
        "un",
        "una",
        "y",
        "a",
        "con",
        "por",
        "para",
    }
    words = [w for w in normalized.split() if w not in articles]
    return " ".join(sorted(words))


EARS_CATEGORIES: list[str] = [
    "ubiquitous",
    "event",
    "state",
    "optional",
    "unwanted",
    "complex",
]

PATTERN_TRIGGER_REQUIRED: dict[str, str] = {
    "event": "WHEN",
    "state": "WHILE",
    "optional": "WHERE",
    "unwanted": "IF",
}


def validate_ears_output(data: dict) -> GuardrailResult:
    violations: list[GuardrailViolation] = []

    if not isinstance(data, dict):
        return GuardrailResult(
            is_valid=False,
            violations=[
                GuardrailViolation(
                    field="root",
                    message="El output no es un diccionario valido",
                    severity="blocker",
                )
            ],
            summary="Output no es un diccionario",
        )

    for category in EARS_CATEGORIES:
        if category not in data:
            violations.append(
                GuardrailViolation(
                    field=category,
                    message=f"Categoria EARS requerida ausente: '{category}'",
                    severity="blocker",
                )
            )

    total_requirements = 0
    for category in EARS_CATEGORIES:
        items = data.get(category, [])
        if not isinstance(items, list):
            violations.append(
                GuardrailViolation(
                    field=category,
                    message=f"Categoria '{category}' no es una lista",
                    severity="blocker",
                )
            )
            continue

        for i, item in enumerate(items):
            if not isinstance(item, dict):
                violations.append(
                    GuardrailViolation(
                        field=f"{category}[{i}]",
                        message=f"Requisito en '{category}[{i}]' no es un diccionario",
                        severity="blocker",
                    )
                )
                continue

            total_requirements += 1

            source = item.get("source_statement", "")
            response = item.get("response", "")
            rationale = item.get("rationale", "")
            pattern = item.get("pattern", category)
            trigger = item.get("trigger")
            acceptance = item.get("acceptance_criteria", [])

            if not source or len(source.strip()) < 10:
                violations.append(
                    GuardrailViolation(
                        field=f"{category}[{i}].source_statement",
                        message=f"source_statement vacio o demasiado corto en {category}[{i}]",
                        severity="blocker",
                    )
                )

            if not response or len(response.strip()) < 5:
                violations.append(
                    GuardrailViolation(
                        field=f"{category}[{i}].response",
                        message=f"response vacio o demasiado corto en {category}[{i}]",
                        severity="blocker",
                    )
                )

            if not rationale or len(rationale.strip()) < 5:
                violations.append(
                    GuardrailViolation(
                        field=f"{category}[{i}].rationale",
                        message=f"rationale vacio en {category}[{i}]",
                        severity="warning",
                    )
                )

            required_trigger = PATTERN_TRIGGER_REQUIRED.get(pattern)
            if required_trigger and not trigger:
                violations.append(
                    GuardrailViolation(
                        field=f"{category}[{i}].trigger",
                        message=f"trigger requerido para patron {pattern} en {category}[{i}]",
                        severity="warning",
                    )
                )

            if not acceptance or len(acceptance) < 1:
                violations.append(
                    GuardrailViolation(
                        field=f"{category}[{i}].acceptance_criteria",
                        message=f"Sin criterios de aceptacion en {category}[{i}]",
                        severity="warning",
                    )
                )

            all_text = f"{source} {response} {rationale}"
            prohibited = _contains_prohibited_terms(all_text)
            for term in prohibited:
                violations.append(
                    GuardrailViolation(
                        field=f"{category}[{i}]",
                        message=f"Termino prohibido en requisito: '{term}'",
                        severity="blocker",
                    )
                )

    if total_requirements < 3:
        violations.append(
            GuardrailViolation(
                field="total_requirements",
                message=f"Se requieren al menos 3 requisitos, se generaron {total_requirements}",
                severity="blocker",
            )
        )

    sanitized: dict = {}
    for category in EARS_CATEGORIES:
        items = data.get(category, [])
        if isinstance(items, list):
            sanitized[category] = items
        else:
            sanitized[category] = []

    is_valid = not any(v.is_blocker for v in violations)
    return GuardrailResult(
        is_valid=is_valid,
        violations=violations,
        sanitized=sanitized,
        summary=f"{total_requirements} requisitos, {len(violations)} violaciones",
    )


_ORTOGRAPHY_PATTERNS = [
    ("accion", "acción"),
    ("generacion", "generación"),
    ("descripcion", "descripción"),
    ("gestion", "gestión"),
    ("administracion", "administración"),
    ("configuracion", "configuración"),
    ("funcion", "función"),
    ("informacion", "información"),
    ("notificacion", "notificación"),
    ("organizacion", "organización"),
    ("validacion", "validación"),
    ("visualizacion", "visualización"),
    ("planificacion", "planificación"),
    ("especificacion", "especificación"),
    ("comunicacion", "comunicación"),
    ("categorizacion", "categorización"),
    ("operacion", "operación"),
    ("sesion", "sesión"),
]

_VISION_STARTERS = [
    "plataforma",
    "sistema",
    "herramienta",
    "aplicación",
    "aplicacion",
    "servicio",
    "producto",
    "solucion",
    "solución",
    "suite",
]


def validate_semantic_quality(
    *, vision: str = "", ears_requirements: list | None = None, feature_title: str = ""
) -> list[GuardrailViolation]:
    violations: list[GuardrailViolation] = []

    if vision and not any(vision.lower().strip().startswith(s) for s in _VISION_STARTERS):
        violations.append(
            GuardrailViolation(
                field="vision",
                message="La visión debería comenzar con 'Plataforma', 'Sistema', 'Herramienta', 'Solución' u otro sustantivo de producto",
                severity="warning",
            )
        )

    if vision and len(vision.strip()) < 100:
        violations.append(
            GuardrailViolation(
                field="vision",
                message=f"Visión demasiado corta ({len(vision.strip())} chars). Debe tener al menos 100 caracteres de contenido sustancial de negocio",
                severity="warning",
            )
        )

    text_for_orto = f"{vision} {feature_title}"
    for wrong, correct in _ORTOGRAPHY_PATTERNS:
        for match in re.finditer(rf"\b{wrong}\b", text_for_orto, re.IGNORECASE):
            violations.append(
                GuardrailViolation(
                    field="orthography",
                    message=f"Ortografía: '{match.group()}' debería llevar tilde → '{correct}'",
                    severity="warning",
                )
            )

    if ears_requirements:
        for req in ears_requirements:
            if not isinstance(req, dict):
                continue
            pattern = req.get("pattern", "")
            source = req.get("source_statement", "")
            if pattern in ("event", "state", "optional", "unwanted") and "shall" not in source.lower():
                violations.append(
                    GuardrailViolation(
                        field="ears_syntax",
                        message=f"Requisito EARS ({pattern}) sin 'shall': '{source[:80]}...'",
                        severity="warning",
                    )
                )

    if feature_title:
        verbs_start = [
            "gestionar", "administrar", "crear", "eliminar", "editar", "configurar",
            "visualizar", "notificar", "generar", "procesar", "validar", "enviar",
            "publicar", "analizar", "programar", "registrar", "modificar", "actualizar",
        ]
        title_lower = feature_title.lower().strip()
        if any(title_lower.startswith(v) for v in verbs_start):
            violations.append(
                GuardrailViolation(
                    field="feature_title",
                    message=f"Título de feature '{feature_title}' comienza con verbo. Usar frase nominal (ej: 'Gestión de...' en vez de 'Gestionar...')",
                    severity="warning",
                )
            )

    return violations


_SPANISH_TILDES: dict[str, list[str]] = {
    "ón": ["accion", "administracion", "aplicacion", "aprobacion", "autorizacion",
           "cancelacion", "categorizacion", "comunicacion", "configuracion",
           "conciliacion", "confirmacion", "decision", "definicion", "devolucion",
           "descripcion", "duracion", "especificacion", "facturacion", "funcion",
           "generacion", "gestion", "informacion", "integracion", "negociacion",
           "notificacion", "operacion", "organizacion", "planificacion", "poblacion",
           "posicion", "preparacion", "programacion", "promocion", "recomendacion",
           "reduccion", "relacion", "rendicion", "reposicion", "rotacion",
           "satisfaccion", "seccion", "seleccion", "sesion", "solucion",
           "supervision", "trazabilidad", "ubicacion", "validacion", "valoracion",
           "verificacion", "version", "visualizacion"],
    "ía": ["categoria", "compañia", "garantia", "gerencia", "mercancia", "tecnologia"],
    "és": ["interes", "despues", "traves"],
    "á": ["analisis", "baja", "capacitacion", "catalogo", "ciclico", "codigo",
          "comite", "critico", "demas", "estrategia", "estara", "fisico",
          "historico", "limite", "margen", "maximo", "metodo", "minimo",
          "optimo", "perdida", "perdidas", "periodo", "practico", "proximo",
          "publica", "rapido", "tactico", "tambien", "tendran", "ultimo",
          "unico", "util", "vacio"],
    "é": ["electronico", "estara", "genero", "numero", "tambien"],
    "í": ["critico", "fisico", "juridico", "maximo", "minimo", "optimo", "unico"],
}


def validate_discovery_quality(data: dict) -> dict[str, object]:
    all_text = " ".join(str(v) for v in data.values() if isinstance(v, str))
    violations: list[str] = []
    warnings: list[str] = []

    orthography_issues = 0
    orthography_checked = 0
    for _suffix, words in _SPANISH_TILDES.items():
        for word in words:
            if word in all_text.lower():
                orthography_checked += 1
                has_tilde = False
                for match in re.finditer(rf"\b{word}[a-z]*\b", all_text, re.IGNORECASE):
                    if any(c in match.group() for c in "áéíóúñ"):
                        has_tilde = True
                        break
                if not has_tilde:
                    orthography_issues += 1

    if orthography_checked > 0:
        ortho_pct = (orthography_checked - orthography_issues) / orthography_checked * 100
        if ortho_pct < 80:
            violations.append(
                f"Ortografia: solo {ortho_pct:.0f}% de tildes correctas ({orthography_issues} errores de {orthography_checked}). "
                f"Revisa: gestion->gestión, critico->crítico, descripcion->descripción, etc."
            )

    duplicates = re.findall(r"\*\*([^*]+)\*\*\1", all_text)
    if duplicates:
        violations.append(
            f"Duplicacion bold+plain detectada: {', '.join(d for d in duplicates[:3])}. "
            f"Usa **Palabra**: descripcion, NO **Palabra**Palabra."
        )

    for section_name in ["actors", "value_proposition", "use_cases",
                         "core_capabilities", "business_rules", "quality_attributes"]:
        section_text = str(data.get(section_name, ""))
        items = [line.strip() for line in section_text.split("\n") if line.strip()]
        if len(items) < 2:
            warnings.append(
                f"Seccion '{section_name}' tiene {len(items)} items visibles. "
                f"Debe tener al menos 3 items en lineas separadas."
            )

    summary_parts: list[str] = []
    blocker_count = len(violations)
    warning_count = len(warnings)
    if blocker_count:
        summary_parts.append(f"{blocker_count} bloqueo(s)")
    if warning_count:
        summary_parts.append(f"{warning_count} advertencia(s)")

    return {
        "is_valid": blocker_count == 0,
        "violations": violations,
        "warnings": warnings,
        "blocker_count": blocker_count,
        "warning_count": warning_count,
        "summary": "; ".join(summary_parts) if summary_parts else "Calidad OK",
    }
