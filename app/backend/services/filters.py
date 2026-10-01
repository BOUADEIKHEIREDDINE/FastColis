"""Apply user filters to cached datasets without reloading Excel files."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.backend.data.catalog import SOURCE_BY_ID


MULTI_VALUE_FILTERS = (
    "pays",
    "produit_global",
    "code_produit",
    "taille_colis",
    "statut_colis",
    "fragile",
    "categorie_reclamation",
    "statut_reclamation",
    "priorite_traitement",
    "canal_reclamation",
)

DATE_COLUMNS = ("date_enquete", "date_reclamation")
SCORE_COLUMNS = ("satisfaction_normalisee",)


def empty_filters() -> dict[str, Any]:
    return {
        "pays": [],
        "produit_global": [],
        "code_produit": [],
        "taille_colis": [],
        "statut_colis": [],
        "fragile": [],
        "categorie_reclamation": [],
        "statut_reclamation": [],
        "priorite_traitement": [],
        "canal_reclamation": [],
        "satisfaction_min": None,
        "satisfaction_max": None,
        "date_start": None,
        "date_end": None,
        "search": "",
        "chart_pays": [],
    }


def normalize_filters(raw: dict[str, Any] | None) -> dict[str, Any]:
    filters = empty_filters()
    if not raw:
        return filters
    for key in MULTI_VALUE_FILTERS:
        value = raw.get(key) or []
        if isinstance(value, str):
            value = [value]
        filters[key] = [str(item) for item in value if str(item).strip()]
    for key in ("satisfaction_min", "satisfaction_max"):
        value = raw.get(key)
        filters[key] = None if value in (None, "", []) else float(value)
    for key in ("date_start", "date_end"):
        value = raw.get(key)
        filters[key] = None if value in (None, "", []) else str(value)
    filters["search"] = str(raw.get("search") or "").strip()
    chart_pays = raw.get("chart_pays") or []
    if isinstance(chart_pays, str):
        chart_pays = [chart_pays]
    filters["chart_pays"] = [str(item) for item in chart_pays if str(item).strip()]
    return filters


def active_filter_count(filters: dict[str, Any]) -> int:
    count = 0
    for key in MULTI_VALUE_FILTERS:
        if filters.get(key):
            count += 1
    if filters.get("satisfaction_min") is not None or filters.get("satisfaction_max") is not None:
        count += 1
    if filters.get("date_start") or filters.get("date_end"):
        count += 1
    if filters.get("search"):
        count += 1
    if filters.get("chart_pays"):
        count += 1
    return count


def context_label(source_ids: list[str], filters: dict[str, Any]) -> str:
    labels = [SOURCE_BY_ID[source_id].label for source_id in source_ids if source_id in SOURCE_BY_ID]
    parts = [" + ".join(labels) if labels else "Aucune source"]
    if filters.get("pays"):
        parts.append(", ".join(filters["pays"]))
    if filters.get("produit_global"):
        parts.append(", ".join(filters["produit_global"]))
    if filters.get("satisfaction_min") is not None or filters.get("satisfaction_max") is not None:
        low = filters.get("satisfaction_min")
        high = filters.get("satisfaction_max")
        if low is not None and high is not None:
            parts.append(f"Satisfaction {low}–{high}")
        elif low is not None:
            parts.append(f"Satisfaction ≥ {low}")
        else:
            parts.append(f"Satisfaction ≤ {high}")
    if filters.get("date_start") or filters.get("date_end"):
        parts.append(f"{filters.get('date_start') or '…'} → {filters.get('date_end') or '…'}")
    if filters.get("categorie_reclamation"):
        parts.append(", ".join(filters["categorie_reclamation"]))
    if filters.get("chart_pays"):
        parts.append("Graphique: " + ", ".join(filters["chart_pays"]))
    return " · ".join(parts)


def _match_values(series: pd.Series, values: list[str]) -> pd.Series:
    normalized = {str(value).strip().lower() for value in values}
    return series.astype("string").str.strip().str.lower().isin(normalized)


def apply_filters(df: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    if df.empty:
        return df
    result = df
    country_values = list(filters.get("pays") or []) + list(filters.get("chart_pays") or [])
    if country_values and "pays" in result.columns:
        result = result.loc[_match_values(result["pays"], country_values)]

    for key in MULTI_VALUE_FILTERS:
        if key == "pays":
            continue
        values = filters.get(key) or []
        if not values or key not in result.columns:
            continue
        result = result.loc[_match_values(result[key], values)]

    low = filters.get("satisfaction_min")
    high = filters.get("satisfaction_max")
    for score_column in SCORE_COLUMNS:
        if score_column not in result.columns:
            continue
        scores = pd.to_numeric(result[score_column], errors="coerce")
        if low is not None:
            result = result.loc[scores >= low]
            scores = pd.to_numeric(result[score_column], errors="coerce")
        if high is not None:
            result = result.loc[scores <= high]
        break

    start = pd.to_datetime(filters.get("date_start"), errors="coerce") if filters.get("date_start") else None
    end = pd.to_datetime(filters.get("date_end"), errors="coerce") if filters.get("date_end") else None
    if start is not None or end is not None:
        date_column = next((column for column in DATE_COLUMNS if column in result.columns), None)
        if date_column:
            dates = pd.to_datetime(result[date_column], errors="coerce")
            if start is not None:
                result = result.loc[dates >= start]
                dates = pd.to_datetime(result[date_column], errors="coerce")
            if end is not None:
                result = result.loc[dates <= end + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]

    search = str(filters.get("search") or "").strip().lower()
    if search:
        text = result.astype(str).agg(" ".join, axis=1).str.lower()
        result = result.loc[text.str.contains(search, na=False)]
    return result.reset_index(drop=True)


def unique_options(frames: dict[str, pd.DataFrame], column: str) -> list[str]:
    values: set[str] = set()
    for frame in frames.values():
        if column not in frame.columns:
            continue
        for value in frame[column].dropna().unique().tolist():
            text = str(value).strip()
            if text and text.lower() not in {"nan", "none"}:
                values.add(text)
    return sorted(values)


def filter_options(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    date_series = []
    for frame in frames.values():
        for column in DATE_COLUMNS:
            if column in frame.columns:
                date_series.append(pd.to_datetime(frame[column], errors="coerce"))
    dates = pd.concat(date_series, ignore_index=True) if date_series else pd.Series(dtype="datetime64[ns]")
    valid_dates = dates.dropna()
    return {
        "pays": unique_options(frames, "pays"),
        "produit_global": unique_options(frames, "produit_global"),
        "code_produit": unique_options(frames, "code_produit"),
        "taille_colis": unique_options(frames, "taille_colis"),
        "statut_colis": unique_options(frames, "statut_colis"),
        "fragile": unique_options(frames, "fragile"),
        "categorie_reclamation": unique_options(frames, "categorie_reclamation"),
        "statut_reclamation": unique_options(frames, "statut_reclamation"),
        "priorite_traitement": unique_options(frames, "priorite_traitement"),
        "canal_reclamation": unique_options(frames, "canal_reclamation"),
        "date_min": None if valid_dates.empty else valid_dates.min().date().isoformat(),
        "date_max": None if valid_dates.empty else valid_dates.max().date().isoformat(),
        "columns": sorted({column for frame in frames.values() for column in frame.columns if not str(column).startswith("_")}),
    }
