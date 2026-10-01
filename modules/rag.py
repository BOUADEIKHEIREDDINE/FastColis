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


def answer_with_rag(
    data: pd.DataFrame,
    question: str,
    model: str = DEFAULT_MODEL,
    top_k: int = DEFAULT_TOP_K,
) -> str:
    """Answer from retrieved survey rows using a locally available Ollama model."""
    relevant_rows = retrieve_relevant_rows(data, question, top_k=top_k)
    if not relevant_rows:
        return "Je ne trouve pas de ligne pertinente dans les donnees fournies."

    try:
        from ollama import chat
    except ImportError as error:
        raise RuntimeError(
            "Le paquet Python 'ollama' est requis. Installez-le avec `pip install ollama`."
        ) from error

    context = json.dumps(relevant_rows, ensure_ascii=False, indent=2, default=str)
    prompt = f"""Tu es un assistant qui repond aux questions sur les enquetes FastColis.
Reponds uniquement a partir des lignes fournies. N'invente aucune information.
Si les lignes ne suffisent pas, dis-le clairement. Pour une question demandant une
statistique globale, precise que le contexte ne contient que des lignes retrouvees.
Reponds en francais, de maniere claire et concise.

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
