"""Expose existing pipeline quality reports without rerunning wrangling."""

from __future__ import annotations

import sys
from typing import Any

import pandas as pd

from app.backend.data.catalog import SOURCE_CATALOG
from app.backend.data.loader import get_store
from app.backend.paths import modules_dir, raw_dir


def _ensure_modules_path() -> None:
    path = str(modules_dir())
    if path not in sys.path:
        sys.path.insert(0, path)


def _serialize_records(df: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    work = df.head(limit) if limit else df
    return work.where(pd.notna(work), None).to_dict(orient="records")


def _normalized_profiles() -> list[dict[str, Any]]:
    store = get_store()
    rows = []
    for spec in SOURCE_CATALOG:
        loaded = store.get(spec.id)
        if not loaded.available or loaded.frame is None:
            rows.append(
                {
                    "source": spec.label,
                    "available": False,
                    "error": loaded.error,
                }
            )
            continue
        df = loaded.frame
        visible = df[[column for column in df.columns if not str(column).startswith("_")]]
        missing_by_column = (
            visible.isna().sum().sort_values(ascending=False).head(12).astype(int).to_dict()
        )
        rows.append(
            {
                "source": spec.label,
                "kind": spec.kind,
                "available": True,
                "rows": int(len(visible)),
                "columns": int(len(visible.columns)),
                "duplicate_rows": int(visible.duplicated().sum()),
                "total_missing": int(visible.isna().sum().sum()),
                "missing_rate_pct": round(float(visible.isna().mean().mean() * 100), 2)
                if len(visible.columns)
                else 0,
                "missing_by_column": missing_by_column,
            }
        )
    return rows


def pipeline_quality_reports() -> dict[str, Any]:
    """Reuse data_pipeline profiling on raw country files when they exist."""
    _ensure_modules_path()
    from data_pipeline import (
        build_missing_report,
        build_structure_report,
        calculate_correlations,
        calculate_outlier_rates,
        load_datasets,
    )

    errors: list[str] = []
    try:
        datasets = load_datasets(raw_dir())
    except Exception as error:  # noqa: BLE001
        return {
            "normalized": _normalized_profiles(),
            "raw_available": False,
            "error": str(error),
            "structure": [],
            "missing": [],
            "correlations": [],
            "outliers": [],
        }

    try:
        structure = build_structure_report(datasets)
        missing = build_missing_report(datasets)
        correlations = calculate_correlations(datasets)
        outliers = calculate_outlier_rates(datasets)
    except Exception as error:  # noqa: BLE001
        errors.append(str(error))
        structure = pd.DataFrame()
        missing = pd.DataFrame()
        correlations = pd.DataFrame()
        outliers = pd.DataFrame()

    removed_preview = []
    if not correlations.empty and "abs_r" in correlations.columns:
        removed_preview = _serialize_records(
            correlations[correlations["abs_r"] < 0.2].sort_values("abs_r"),
            limit=40,
        )

    return {
        "normalized": _normalized_profiles(),
        "raw_available": True,
        "error": None if not errors else errors[0],
        "structure": _serialize_records(structure),
        "missing": _serialize_records(missing),
        "correlations": _serialize_records(correlations.sort_values("abs_r", ascending=False) if not correlations.empty else correlations),
        "low_correlation_removed_candidates": removed_preview,
        "outliers": _serialize_records(outliers),
        "notes": [
            "Les indicateurs raw réutilisent les fonctions existantes de modules/data_pipeline.py.",
            "Le dashboard lui-même lit les fichiers déjà normalisés, sans relancer le nettoyage.",
            "Le seuil de faible corrélation affiché (0.2) est celui de la pipeline.",
        ],
    }
