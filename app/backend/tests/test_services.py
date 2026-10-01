"""Lightweight tests for source isolation and filtering."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backend.data.loader import get_store
from app.backend.llm.sources import detect_sources_in_question, resolve_scope
from app.backend.services.filters import apply_filters, normalize_filters
from app.backend.services.metrics import dashboard_payload, split_frames


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_load_six_sources() -> None:
    sources = get_store().list_sources()
    assert_true(len(sources) == 6, "Six sources expected")
    available = [item for item in sources if item["available"]]
    assert_true(len(available) == 6, f"Unavailable sources: {sources}")


def test_france_only_dashboard() -> None:
    store = get_store()
    frames = {"france": apply_filters(store.frames(["france"])["france"], normalize_filters({}))}
    payload = dashboard_payload(["france"], frames, normalize_filters({}), "France", 0)
    countries = {row["label"] for row in payload["charts"]["satisfaction_by_country"]}
    assert_true(countries == {"France"}, f"Expected France only, got {countries}")
    assert_true(payload["satisfaction_rows"] == 200, payload["satisfaction_rows"])
    assert_true(payload["claims_rows"] == 0, "Claims should be excluded")


def test_france_spain_kpis() -> None:
    store = get_store()
    raw = store.frames(["france", "espagne"])
    frames = {key: apply_filters(value, normalize_filters({})) for key, value in raw.items()}
    payload = dashboard_payload(["france", "espagne"], frames, normalize_filters({}), "x", 0)
    countries = {row["label"] for row in payload["charts"]["satisfaction_by_country"]}
    assert_true(countries == {"France", "Espagne"}, countries)
    assert_true(payload["satisfaction_rows"] == 400, payload["satisfaction_rows"])


def test_claims_only() -> None:
    store = get_store()
    frames = {
        "reclamations": apply_filters(store.frames(["reclamations"])["reclamations"], normalize_filters({}))
    }
    satisfaction, claims = split_frames(frames)
    assert_true(satisfaction.empty, "Satisfaction should be empty")
    assert_true(len(claims) == 200, len(claims))


def test_question_scope_conflict() -> None:
    detection = detect_sources_in_question("Compare la France et le Maroc.")
    assert_true(set(detection) == {"france", "maroc"}, detection)
    scope = resolve_scope(["france"], "Compare la France et le Maroc.")
    assert_true(scope["conflict"] is True, scope)
    assert_true(set(scope["effective"]) == {"france", "maroc"}, scope)


def test_spain_question_uses_spain() -> None:
    scope = resolve_scope(["espagne"], "Quelle est la satisfaction moyenne ?")
    assert_true(scope["effective"] == ["espagne"], scope)
    assert_true(scope["conflict"] is False, scope)


def test_satisfaction_filter() -> None:
    store = get_store()
    frame = store.frames(["france"])["france"]
    filtered = apply_filters(frame, normalize_filters({"satisfaction_max": 3}))
    scores = filtered["satisfaction_normalisee"]
    assert_true((scores <= 3).all(), "Filter max satisfaction failed")
    assert_true(len(filtered) < len(frame), "Filter should reduce rows")


if __name__ == "__main__":
    tests = [
        test_load_six_sources,
        test_france_only_dashboard,
        test_france_spain_kpis,
        test_claims_only,
        test_question_scope_conflict,
        test_spain_question_uses_spain,
        test_satisfaction_filter,
    ]
    for test in tests:
        test()
        print("OK", test.__name__)
    print("All service tests passed.")
