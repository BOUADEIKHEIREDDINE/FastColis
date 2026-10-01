"""Acceptance checks for dashboard filtering and LLM scope resolution."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backend.data.loader import get_store
from app.backend.llm.sources import resolve_scope
from app.backend.services.facts import quantitative_facts
from app.backend.services.filters import apply_filters, normalize_filters
from app.backend.services.metrics import dashboard_payload


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK", message)


def main() -> None:
    store = get_store()

    # Test 1 — France only
    frames = {"france": apply_filters(store.frames(["france"])["france"], normalize_filters({}))}
    payload = dashboard_payload(["france"], frames, normalize_filters({}), "France", 0)
    check(
        {row["label"] for row in payload["charts"]["satisfaction_by_country"]} == {"France"},
        "Test1 dashboard France only",
    )
    check(resolve_scope(["france"], "Quelle est la satisfaction moyenne ?")["effective"] == ["france"], "Test1 LLM France")

    # Test 2 — France + Espagne
    raw = store.frames(["france", "espagne"])
    frames = {key: apply_filters(value, normalize_filters({})) for key, value in raw.items()}
    payload = dashboard_payload(["france", "espagne"], frames, normalize_filters({}), "x", 0)
    check(payload["satisfaction_rows"] == 400, "Test2 KPI rows France+Espagne")
    check(
        {row["label"] for row in payload["charts"]["satisfaction_by_country"]} == {"France", "Espagne"},
        "Test2 countries France+Espagne",
    )

    # Test 3 — Espagne question
    scope = resolve_scope(["espagne"], "Quelle est la satisfaction moyenne ?")
    check(scope["effective"] == ["espagne"] and not scope["conflict"], "Test3 Espagne scope")
    facts = quantitative_facts(
        {"espagne": apply_filters(store.frames(["espagne"])["espagne"], normalize_filters({}))}
    )
    check(facts["satisfaction"]["satisfaction_moyenne"] is not None, "Test3 Python mean for Espagne")

    # Test 4 — conflict France selected, question France+Maroc
    scope = resolve_scope(["france"], "Compare la France et le Maroc.")
    check(scope["conflict"] is True, "Test4 conflict visible")
    check(set(scope["effective"]) == {"france", "maroc"}, "Test4 override to France+Maroc")
    check(bool(scope["warning"]), "Test4 warning present")

    # Test 5 — reclamations
    frames = {
        "reclamations": apply_filters(store.frames(["reclamations"])["reclamations"], normalize_filters({}))
    }
    payload = dashboard_payload(["reclamations"], frames, normalize_filters({}), "Réclamations", 0)
    check(payload["claims_rows"] == 200 and payload["satisfaction_rows"] == 0, "Test5 claims only")
    check(resolve_scope(["reclamations"], "Quelles sont les principales réclamations ?")["effective"] == ["reclamations"], "Test5 LLM claims")

    # Test 6 — France + reclamations link honesty
    raw = store.frames(["france", "reclamations"])
    frames = {key: apply_filters(value, normalize_filters({})) for key, value in raw.items()}
    facts = quantitative_facts(frames)
    check(facts["lien_satisfaction_reclamations"]["jointure_ligne_possible"] is False, "Test6 no fake join")
    check("clé commune" in facts["lien_satisfaction_reclamations"]["raison"].lower() or "aucune clé" in facts["lien_satisfaction_reclamations"]["raison"].lower(), "Test6 explicit reason")

    # Test 7 — filter coherence
    filtered = apply_filters(store.frames(["france"])["france"], normalize_filters({"satisfaction_max": 3}))
    payload = dashboard_payload(["france"], {"france": filtered}, normalize_filters({"satisfaction_max": 3}), "x", 1)
    check(payload["satisfaction_rows"] == len(filtered), "Test7 filtered rows match KPI")
    check(payload["active_filters"] == 1, "Test7 active filter count")

    print("All acceptance scenarios passed.")


if __name__ == "__main__":
    main()
