"""Source-aware LLM queries built on the existing answer_with_rag function."""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any

import pandas as pd

from app.backend.data.loader import get_store
from app.backend.llm.sources import resolve_scope, source_labels
from app.backend.paths import modules_dir
from app.backend.services.facts import evidence_rows, quantitative_facts
from app.backend.services.filters import apply_filters, context_label, normalize_filters
from app.backend.services.metrics import combine_for_table, split_frames


DEFAULT_MODEL = "mistral:latest"
OLLAMA_TIMEOUT_SECONDS = 25


def _ensure_modules_path() -> None:
    path = str(modules_dir())
    if path not in sys.path:
        sys.path.insert(0, path)


def _prepare_frames(source_ids: list[str], filters: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], list[str]]:
    store = get_store()
    missing = store.missing(source_ids)
    frames = {}
    for source_id, frame in store.frames(source_ids).items():
        frames[source_id] = apply_filters(frame, filters)
    return frames, missing


def _format_source_preamble(labels: list[str]) -> str:
    if not labels:
        return ""
    heading = "Source analysée" if len(labels) == 1 else "Sources analysées"
    return f"{heading}\n{' · '.join(labels)}\n\nRéponse\n\n"


def _deterministic_answer(labels: list[str], facts: dict[str, Any], warning: str | None) -> str:
    """Build a traceable answer from Python facts when Ollama is unavailable."""
    sat = facts.get("satisfaction") or {}
    claims = facts.get("reclamations") or {}
    lines = [_format_source_preamble(labels).rstrip(), ""]
    if warning:
        lines.extend([f"Avertissement : {warning}", ""])
    if sat.get("satisfaction_moyenne") is not None:
        lines.append(
            f"{' · '.join(labels)} · {sat.get('nombre_reponses', 0):,} réponses".replace(",", " ")
        )
        lines.append(f"Satisfaction moyenne : {sat['satisfaction_moyenne']:.2f} / 5")
        if sat.get("taux_notes_ge_4_pct") is not None:
            lines.append(f"Taux de notes >= 4 : {sat['taux_notes_ge_4_pct']:.1f} %")
        weakest = sat.get("produit_plus_faible")
        if weakest:
            lines.append(
                "Le produit avec la satisfaction moyenne la plus faible est "
                f"{weakest['produit_global']} avec {weakest['satisfaction_moyenne']:.2f} / 5 "
                f"({weakest['nombre_notes']} notes)."
            )
        by_country = sat.get("par_pays") or []
        if len(by_country) > 1:
            lines.append("")
            lines.append("Comparaison par pays :")
            for row in by_country:
                lines.append(
                    f"- {row['pays']} : {row['satisfaction_moyenne']:.2f} / 5 "
                    f"({row['nombre_reponses']} réponses)"
                )
    if claims.get("nombre_reclamations"):
        lines.append("")
        lines.append(f"Réclamations : {claims['nombre_reclamations']}")
        categories = claims.get("par_categorie") or {}
        if categories:
            lines.append("Principales catégories :")
            for name, count in list(categories.items())[:5]:
                lines.append(f"- {name} : {count}")
    link = facts.get("lien_satisfaction_reclamations") or {}
    if sat.get("nombre_reponses") and claims.get("nombre_reclamations"):
        lines.append("")
        lines.append(link.get("raison") or "Jointure satisfaction / réclamations non disponible.")
    if len(lines) <= 2:
        lines.append("Aucune statistique calculable sur le périmètre sélectionné.")
    lines.append("")
    lines.append("(Réponse calculée en Python — le modèle Ollama était indisponible.)")
    return "\n".join(lines).strip()


def _scope_payload(scope: dict[str, object], labels: list[str]) -> dict[str, Any]:
    return {
        "mode": scope["mode"],
        "conflict": scope["conflict"],
        "warning": scope["warning"],
        "selected": source_labels(list(scope["selected"])),  # type: ignore[arg-type]
        "mentioned": source_labels(list(scope["mentioned"])),  # type: ignore[arg-type]
        "effective": labels,
    }


def ask_fastcolis(
    question: str,
    selected_sources: list[str],
    filters: dict[str, Any] | None = None,
    model: str = DEFAULT_MODEL,
    top_k: int = 8,
) -> dict[str, Any]:
    _ensure_modules_path()
    from rag import answer_with_rag

    question = (question or "").strip()
    if not question:
        return {
            "ok": False,
            "error": "La question ne peut pas être vide.",
        }

    filters = normalize_filters(filters)
    scope = resolve_scope(selected_sources, question)
    effective_ids = list(scope["effective"])
    frames, missing = _prepare_frames(effective_ids, filters)
    labels = source_labels(effective_ids)
    facts = quantitative_facts(frames)
    extra_context = {
        "sources_utilisees": labels,
        "mode_perimetre": scope["mode"],
        "conflit_perimetre": scope["conflict"],
        "avertissement": scope["warning"],
        "filtres": {key: value for key, value in filters.items() if value not in (None, "", [])},
        "faits": facts,
    }
    combined = combine_for_table(frames)
    satisfaction, claims = split_frames(frames)
    rag_data = satisfaction if not satisfaction.empty else claims
    if rag_data.empty:
        rag_data = combined

    base = {
        "sources": labels,
        "source_ids": effective_ids,
        "scope": _scope_payload(scope, labels),
        "facts": facts,
        "evidence": evidence_rows(frames),
        "row_count": int(sum(len(frame) for frame in frames.values())),
        "missing_files": missing,
        "context": context_label(effective_ids, filters),
        "model": model,
    }

    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(
            answer_with_rag,
            rag_data,
            question,
            model,
            top_k,
            labels,
            extra_context,
        )
        answer = future.result(timeout=OLLAMA_TIMEOUT_SECONDS)
    except FuturesTimeoutError:
        message = (
            f"Ollama n'a pas répondu dans le délai de {OLLAMA_TIMEOUT_SECONDS}s "
            f"(modèle '{model}'). Une réponse calculée en Python est fournie."
        )
        fallback = _deterministic_answer(
            labels,
            facts,
            scope.get("warning") if isinstance(scope.get("warning"), str) else None,
        )
        return {
            **base,
            "ok": True,
            "answer": fallback,
            "fallback": True,
            "error": message,
        }
    except Exception as error:  # noqa: BLE001
        message = str(error)
        lowered = message.lower()
        if any(token in lowered for token in ("ollama", "connection", "out-of-memory", "allocate", "llama-server")):
            message = (
                "Impossible d'obtenir une réponse Ollama "
                f"(modèle '{model}'). Une réponse calculée en Python est fournie. Détail: {error}"
            )
        fallback = _deterministic_answer(
            labels,
            facts,
            scope.get("warning") if isinstance(scope.get("warning"), str) else None,
        )
        return {
            **base,
            "ok": True,
            "answer": fallback,
            "fallback": True,
            "error": message,
        }
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return {
        **base,
        "ok": True,
        "answer": answer,
        "fallback": False,
    }
