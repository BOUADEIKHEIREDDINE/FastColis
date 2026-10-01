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
    product_scores = scored_data.dropna(subset=["_score", "produit_global"])
    grouped = (
        product_scores.groupby("produit_global")[["_score"]]
        .agg(
            nombre_notes=("_score", "count"),
            score_cumulatif=("_score", "sum"),
            satisfaction_moyenne=("_score", "mean"),
        )
        .reset_index()
        .sort_values("satisfaction_moyenne", ascending=False)
    )

    return {
        "nombre_enquetes": int(len(data)),
        "nombre_notes_valides": int(valid_scores.count()),
        "score_cumulatif_global": float(round(float(valid_scores.sum()), 3)),
        "satisfaction_moyenne_globale": (
            float(round(float(valid_scores.mean()), 3)) if not valid_scores.empty else None
        ),
        "scores_par_produit": [
            {
                "produit_global": str(row.produit_global),
                "nombre_notes": int(row.nombre_notes),
                "score_cumulatif": float(round(float(row.score_cumulatif), 3)),
                "satisfaction_moyenne": float(round(float(row.satisfaction_moyenne), 3)),
            }
            for row in grouped.itertuples(index=False)
        ],
    }


def answer_with_rag(
    data: pd.DataFrame,
    question: str,
    model: str = DEFAULT_MODEL,
    top_k: int = DEFAULT_TOP_K,
) -> str:
    """Answer from retrieved survey rows using a locally available Ollama model."""
    relevant_rows = retrieve_relevant_rows(data, question, top_k=top_k)
    global_statistics = _build_global_statistics(data)
    if not relevant_rows and not global_statistics.get("scores_par_produit"):
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
    prompt = f"""Tu es un assistant qui repond aux questions sur les enquetes FastColis.
Reponds uniquement a partir des statistiques et des lignes fournies. N'invente aucune information.
Pour comparer les produits, distingue la satisfaction moyenne du score cumulatif et
indique le nombre de notes qui permet d'interpreter chaque cumul. Les statistiques
globales portent sur toute la base; les lignes retrouvees servent aux questions detaillees.
Si les informations ne suffisent pas, dis-le clairement.
Reponds en francais, de maniere claire et concise.

STATISTIQUES CALCULEES SUR TOUTE LA BASE :
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
    return response.message.content.strip()
