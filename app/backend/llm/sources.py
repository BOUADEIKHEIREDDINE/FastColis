"""Detect and resolve dataset sources for LLM questions."""

from __future__ import annotations

import re
import unicodedata

from app.backend.data.catalog import SOURCE_CATALOG, SOURCE_BY_ID


def _normalize(text: str) -> str:
    lowered = unicodedata.normalize("NFD", text.lower())
    return "".join(character for character in lowered if unicodedata.category(character) != "Mn")


SOURCE_PATTERNS: dict[str, tuple[str, ...]] = {
    "france": (r"\bfrance\b", r"\bfrancais\b", r"\bfrancaise\b"),
    "espagne": (r"\bespagne\b", r"\bspain\b", r"\bespagnol"),
    "maroc": (r"\bmaroc\b", r"\bmorocco\b", r"\bmarocain"),
    "allemagne": (r"\ballemagne\b", r"\bgermany\b", r"\ballemand"),
    "canada": (r"\bcanada\b", r"\bcanadien"),
    "reclamations": (
        r"\breclamation",
        r"\bplainte",
        r"\bclaims?\b",
        r"\breclams?\b",
    ),
}


def detect_sources_in_question(question: str) -> list[str]:
    text = _normalize(question)
    found: list[str] = []
    for source_id, patterns in SOURCE_PATTERNS.items():
        if any(re.search(pattern, text) for pattern in patterns):
            found.append(source_id)
    return found


def resolve_scope(selected_sources: list[str], question: str) -> dict[str, object]:
    """Resolve LLM scope.

    Priority:
    1. Interface selection is the default perimeter.
    2. Explicit sources in the question can narrow that perimeter.
    3. Explicit sources outside the selection are a visible conflict
       and override the data used, without doing so silently.
    """
    selected = [source_id for source_id in selected_sources if source_id in SOURCE_BY_ID]
    mentioned = detect_sources_in_question(question)
    if not selected:
        selected = [source.id for source in SOURCE_CATALOG if source.kind == "satisfaction"]

    if not mentioned:
        return {
            "effective": selected,
            "selected": selected,
            "mentioned": [],
            "mode": "interface",
            "conflict": False,
            "warning": None,
        }

    selected_set = set(selected)
    mentioned_set = set(mentioned)
    if mentioned_set <= selected_set:
        return {
            "effective": mentioned,
            "selected": selected,
            "mentioned": mentioned,
            "mode": "question_subset",
            "conflict": False,
            "warning": None,
        }

    selected_labels = [SOURCE_BY_ID[item].label for item in selected]
    mentioned_labels = [SOURCE_BY_ID[item].label for item in mentioned]
    warning = (
        "La question mentionne "
        + " + ".join(mentioned_labels)
        + " alors que l'interface sélectionne "
        + " + ".join(selected_labels)
        + ". L'analyse utilise le périmètre explicitement demandé dans la question."
    )
    return {
        "effective": mentioned,
        "selected": selected,
        "mentioned": mentioned,
        "mode": "question_override",
        "conflict": True,
        "warning": warning,
    }


def source_labels(source_ids: list[str]) -> list[str]:
    return [SOURCE_BY_ID[source_id].label for source_id in source_ids if source_id in SOURCE_BY_ID]
