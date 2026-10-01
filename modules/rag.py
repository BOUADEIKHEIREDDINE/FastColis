"""Retrieve relevant normalized survey rows and answer questions with Ollama."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

import pandas as pd


DEFAULT_MODEL = "mistral:latest"
DEFAULT_TOP_K = 8
_STOP_WORDS = {
    "avec", "dans", "des", "est", "les", "leur", "mais", "mon", "pour",
    "que", "qui", "sur", "une", "vous", "the", "and", "for", "from",
    "how", "what", "when", "where", "which", "with", "about", "does",
}
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _normalize_text(value: object) -> str:
    text = "" if pd.isna(value) else str(value).lower()
    return "".join(
        character
        for character in unicodedata.normalize("NFD", text)
        if unicodedata.category(character) != "Mn"
    )


def _query_tokens(question: str) -> set[str]:
    return {
        token
        for token in _TOKEN_PATTERN.findall(_normalize_text(question))
        if len(token) > 2 and token not in _STOP_WORDS
    }


def retrieve_relevant_rows(
    data: pd.DataFrame,
    question: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    """Return up to ``top_k`` rows ranked by lexical overlap with the question."""
    if not question.strip():
        raise ValueError("La question ne peut pas etre vide.")
    if top_k < 1:
        raise ValueError("top_k doit etre superieur ou egal a 1.")

    query_tokens = _query_tokens(question)
    if not query_tokens:
        return []

    ranked_rows = []
    for row_number, row in enumerate(data.to_dict(orient="records")):
        row_text = _normalize_text(" ".join(str(value) for value in row.values() if pd.notna(value)))
        row_tokens = set(_TOKEN_PATTERN.findall(row_text))
        overlap = len(query_tokens & row_tokens)
        if overlap:
            ranked_rows.append((overlap, row_number, row))

    ranked_rows.sort(key=lambda item: (-item[0], item[1]))
    return [row for _, _, row in ranked_rows[:top_k]]


def _aggregate_score_groups(scored_data: pd.DataFrame, group_column: str) -> list[dict[str, Any]]:
    if group_column not in scored_data.columns:
        return []
    grouped = (
        scored_data.dropna(subset=["_score", group_column])
        .groupby(group_column)[["_score"]]
        .agg(
            nombre_notes=("_score", "count"),
            score_cumulatif=("_score", "sum"),
            satisfaction_moyenne=("_score", "mean"),
        )
        .reset_index()
        .sort_values("satisfaction_moyenne", ascending=False)
    )
    return [
        {
            group_column: str(getattr(row, group_column)),
            "nombre_notes": int(row.nombre_notes),
            "score_cumulatif": float(round(float(row.score_cumulatif), 3)),
            "satisfaction_moyenne": float(round(float(row.satisfaction_moyenne), 3)),
        }
        for row in grouped.itertuples(index=False)
    ]


def _build_global_statistics(data: pd.DataFrame) -> dict[str, Any]:
    """Calculate full-dataset satisfaction totals and product aggregates."""
    required_columns = {"produit_global", "satisfaction_normalisee"}
    if not required_columns.issubset(data.columns):
        return {
            "nombre_enquetes": int(len(data)),
            "statistiques_indisponibles": sorted(required_columns - set(data.columns)),
        }

    scored_data = data.assign(
        _score=pd.to_numeric(data["satisfaction_normalisee"], errors="coerce")
    )
    valid_scores = scored_data["_score"].dropna()

    statistics = {
        "nombre_enquetes": int(len(data)),
        "nombre_notes_valides": int(valid_scores.count()),
        "score_cumulatif_global": float(round(float(valid_scores.sum()), 3)),
        "satisfaction_moyenne_globale": (
            float(round(float(valid_scores.mean()), 3)) if not valid_scores.empty else None
        ),
        "scores_par_produit": _aggregate_score_groups(scored_data, "produit_global"),
        "scores_par_pays": _aggregate_score_groups(scored_data, "pays"),
    }
    return statistics


def _format_source_preamble(sources: list[str] | None) -> str:
    if not sources:
        return ""
    labels = " · ".join(sources)
    heading = "Source analysée" if len(sources) == 1 else "Sources analysées"
    return f"{heading}\n{labels}\n\nRéponse\n\n"


def answer_with_rag(
    data: pd.DataFrame,
    question: str,
    model: str = DEFAULT_MODEL,
    top_k: int = DEFAULT_TOP_K,
    sources: list[str] | None = None,
    extra_context: dict[str, Any] | None = None,
) -> str:
    """Answer from retrieved survey rows using a locally available Ollama model."""
    relevant_rows = retrieve_relevant_rows(data, question, top_k=top_k)
    global_statistics = _build_global_statistics(data)
    has_extra = bool(extra_context)
    if not relevant_rows and not global_statistics.get("scores_par_produit") and not has_extra:
        return "Je ne trouve pas de ligne pertinente dans les donnees fournies."

    try:
        from ollama import chat
    except ImportError as error:
        raise RuntimeError(
            "Le paquet Python 'ollama' est requis. Installez-le avec `pip install ollama`."
        ) from error

    context = json.dumps(relevant_rows, ensure_ascii=False, indent=2, default=str)
    statistics_context = json.dumps(
        global_statistics, ensure_ascii=False, indent=2, default=str
    )
    extra_block = ""
    if extra_context:
        extra_block = (
            "\nFAITS CALCULES EN PYTHON (a utiliser tels quels, ne pas recalculer) :\n"
            + json.dumps(extra_context, ensure_ascii=False, indent=2, default=str)
            + "\n"
        )
    source_block = ""
    if sources:
        source_block = (
            "\nPERIMETRE DES SOURCES AUTORISEES :\n"
            + json.dumps(sources, ensure_ascii=False)
            + "\nNe melange pas d'autres pays ou bases.\n"
        )
    prompt = f"""Tu es un assistant qui repond aux questions sur les enquetes FastColis.
Reponds uniquement a partir des statistiques, des faits calcules et des lignes fournies. N'invente aucune information.
Pour comparer les produits, distingue la satisfaction moyenne du score cumulatif et
indique le nombre de notes qui permet d'interpreter chaque cumul. Les statistiques
globales portent sur le perimetre fourni; les lignes retrouvees servent aux questions detaillees.
Si les informations ne suffisent pas, dis-le clairement.
Reponds en francais, de maniere claire et concise.
{source_block}{extra_block}
STATISTIQUES CALCULEES SUR LE PERIMETRE :
{statistics_context}

LIGNES RETROUVEES :
{context}

QUESTION :
{question}
"""

    response = chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    answer = response.message.content.strip()
    if not answer:
        raise RuntimeError(
            f"Le modele Ollama '{model}' a renvoye une reponse vide. "
            "Essayez un autre modele, par exemple 'mistral:latest'."
        )
    return _format_source_preamble(sources) + answer
