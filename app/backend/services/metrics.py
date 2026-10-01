"""Compute dashboard KPIs and chart series from filtered frames."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.backend.data.catalog import SOURCE_BY_ID


def _json_number(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(round(float(value), 3))


def split_frames(frames: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    satisfaction_parts = []
    claims_parts = []
    for source_id, frame in frames.items():
        kind = SOURCE_BY_ID[source_id].kind
        if kind == "reclamations":
            claims_parts.append(frame)
        else:
            satisfaction_parts.append(frame)
    satisfaction = (
        pd.concat(satisfaction_parts, ignore_index=True) if satisfaction_parts else pd.DataFrame()
    )
    claims = pd.concat(claims_parts, ignore_index=True) if claims_parts else pd.DataFrame()
    return satisfaction, claims


def _mean_score(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns or df.empty:
        return None
    scores = pd.to_numeric(df[column], errors="coerce").dropna()
    if scores.empty:
        return None
    return _json_number(scores.mean())


def _group_mean(df: pd.DataFrame, group: str, value: str) -> list[dict[str, Any]]:
    if df.empty or group not in df.columns or value not in df.columns:
        return []
    work = df[[group, value]].copy()
    work[value] = pd.to_numeric(work[value], errors="coerce")
    work = work.dropna(subset=[group, value])
    if work.empty:
        return []
    grouped = work.groupby(group)[value].agg(["mean", "count"]).reset_index()
    grouped = grouped.sort_values("mean", ascending=False)
    return [
        {
            "label": str(row[group]),
            "value": _json_number(row["mean"]),
            "count": int(row["count"]),
        }
        for _, row in grouped.iterrows()
    ]


def _value_counts(df: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    if df.empty or column not in df.columns:
        return []
    counts = df[column].dropna().astype("string").value_counts()
    return [{"label": str(label), "value": int(value)} for label, value in counts.items()]


def _monthly_mean(df: pd.DataFrame, date_column: str, value_column: str) -> list[dict[str, Any]]:
    if df.empty or date_column not in df.columns or value_column not in df.columns:
        return []
    work = df[[date_column, value_column]].copy()
    work[date_column] = pd.to_datetime(work[date_column], errors="coerce")
    work[value_column] = pd.to_numeric(work[value_column], errors="coerce")
    work = work.dropna(subset=[date_column, value_column])
    if work.empty:
        return []
    work["month"] = work[date_column].dt.to_period("M").astype(str)
    grouped = work.groupby("month")[value_column].agg(["mean", "count"]).reset_index()
    return [
        {
            "label": row["month"],
            "value": _json_number(row["mean"]),
            "count": int(row["count"]),
        }
        for _, row in grouped.iterrows()
    ]


def _monthly_count(df: pd.DataFrame, date_column: str) -> list[dict[str, Any]]:
    if df.empty or date_column not in df.columns:
        return []
    dates = pd.to_datetime(df[date_column], errors="coerce").dropna()
    if dates.empty:
        return []
    months = dates.dt.to_period("M").astype(str).value_counts().sort_index()
    return [{"label": str(label), "value": int(value)} for label, value in months.items()]


def _distribution(df: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    if df.empty or column not in df.columns:
        return []
    scores = pd.to_numeric(df[column], errors="coerce").dropna().round().astype(int)
    if scores.empty:
        return []
    counts = scores.value_counts().sort_index()
    return [{"label": str(int(label)), "value": int(value)} for label, value in counts.items()]


def dashboard_payload(
    source_ids: list[str],
    frames: dict[str, pd.DataFrame],
    filters: dict[str, Any],
    context: str,
    active_filters: int,
) -> dict[str, Any]:
    satisfaction, claims = split_frames(frames)
    sat_mean = _mean_score(satisfaction, "satisfaction_normalisee")
    valid_scores = (
        pd.to_numeric(satisfaction["satisfaction_normalisee"], errors="coerce").dropna()
        if not satisfaction.empty and "satisfaction_normalisee" in satisfaction.columns
        else pd.Series(dtype=float)
    )
    satisfaction_rate = (
        _json_number((valid_scores >= 4).mean() * 100) if not valid_scores.empty else None
    )
    products = (
        int(satisfaction["produit_global"].nunique())
        if not satisfaction.empty and "produit_global" in satisfaction.columns
        else 0
    )
    kpis = [
        {
            "id": "satisfaction",
            "label": "Satisfaction moyenne",
            "value": None if sat_mean is None else f"{sat_mean:.2f} / 5",
            "hint": f"{int(valid_scores.count())} notes valides" if not valid_scores.empty else "Aucune note",
            "available": sat_mean is not None,
        },
        {
            "id": "responses",
            "label": "Réponses",
            "value": f"{len(satisfaction):,}".replace(",", " "),
            "hint": "Enquêtes de satisfaction du périmètre",
            "available": not satisfaction.empty,
        },
        {
            "id": "products",
            "label": "Produits",
            "value": str(products),
            "hint": "Produits globaux distincts",
            "available": not satisfaction.empty,
        },
        {
            "id": "claims",
            "label": "Réclamations",
            "value": f"{len(claims):,}".replace(",", " "),
            "hint": "Lignes de la base réclamations filtrée",
            "available": not claims.empty or "reclamations" in source_ids,
        },
        {
            "id": "rate",
            "label": "Taux de satisfaction",
            "value": None if satisfaction_rate is None else f"{satisfaction_rate:.1f} %",
            "hint": "Part des notes ≥ 4 / 5",
            "available": satisfaction_rate is not None,
        },
    ]
    if not claims.empty and "sla_respecte" in claims.columns:
        sla = claims["sla_respecte"].astype("string").str.lower().isin(["oui", "yes", "true", "1"])
        kpis.append(
            {
                "id": "sla",
                "label": "SLA respecté",
                "value": f"{_json_number(sla.mean() * 100):.1f} %",
                "hint": "Part des réclamations au SLA",
                "available": True,
            }
        )

    return {
        "context": context,
        "source_ids": source_ids,
        "row_count": int(sum(len(frame) for frame in frames.values())),
        "satisfaction_rows": int(len(satisfaction)),
        "claims_rows": int(len(claims)),
        "active_filters": active_filters,
        "kpis": kpis,
        "charts": {
            "satisfaction_by_country": _group_mean(satisfaction, "pays", "satisfaction_normalisee"),
            "satisfaction_by_product": _group_mean(satisfaction, "produit_global", "satisfaction_normalisee"),
            "satisfaction_over_time": _monthly_mean(satisfaction, "date_enquete", "satisfaction_normalisee"),
            "score_distribution": _distribution(satisfaction, "satisfaction_normalisee"),
            "claims_by_category": _value_counts(claims, "categorie_reclamation"),
            "claims_by_country": _value_counts(claims, "pays"),
            "claims_over_time": _monthly_count(claims, "date_reclamation"),
            "claims_by_status": _value_counts(claims, "statut_reclamation"),
        },
        "has_satisfaction": not satisfaction.empty,
        "has_claims": not claims.empty,
    }


def combine_for_table(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(list(frames.values()), ignore_index=True, sort=False)
    hidden = [column for column in combined.columns if str(column).startswith("_")]
    ordered = ["_source_label", "_kind"] + [column for column in combined.columns if column not in hidden]
    existing = [column for column in ordered if column in combined.columns]
    return combined[existing]
