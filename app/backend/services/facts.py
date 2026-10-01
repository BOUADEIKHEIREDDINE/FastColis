"""Python-side facts used by the LLM so it does not invent numbers."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.backend.services.metrics import split_frames


def _round(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(round(float(value), 3))


def _product_stats(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty or "produit_global" not in df.columns or "satisfaction_normalisee" not in df.columns:
        return []
    work = df.copy()
    work["satisfaction_normalisee"] = pd.to_numeric(work["satisfaction_normalisee"], errors="coerce")
    work = work.dropna(subset=["produit_global", "satisfaction_normalisee"])
    if work.empty:
        return []
    grouped = (
        work.groupby("produit_global")["satisfaction_normalisee"]
        .agg(["mean", "count"])
        .reset_index()
        .sort_values("mean")
    )
    return [
        {
            "produit_global": str(row["produit_global"]),
            "satisfaction_moyenne": _round(row["mean"]),
            "nombre_notes": int(row["count"]),
        }
        for row in grouped.to_dict(orient="records")
    ]


def _country_stats(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty or "pays" not in df.columns or "satisfaction_normalisee" not in df.columns:
        return []
    work = df.copy()
    work["satisfaction_normalisee"] = pd.to_numeric(work["satisfaction_normalisee"], errors="coerce")
    work = work.dropna(subset=["pays", "satisfaction_normalisee"])
    grouped = (
        work.groupby("pays")["satisfaction_normalisee"]
        .agg(["mean", "count"])
        .reset_index()
        .sort_values("mean", ascending=False)
    )
    return [
        {
            "pays": str(row["pays"]),
            "satisfaction_moyenne": _round(row["mean"]),
            "nombre_reponses": int(row["count"]),
        }
        for row in grouped.to_dict(orient="records")
    ]


def _claims_stats(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"nombre_reclamations": 0}
    payload: dict[str, Any] = {"nombre_reclamations": int(len(df))}
    if "categorie_reclamation" in df.columns:
        payload["par_categorie"] = (
            df["categorie_reclamation"].dropna().astype("string").value_counts().head(8).astype(int).to_dict()
        )
    if "pays" in df.columns:
        payload["par_pays"] = df["pays"].dropna().astype("string").value_counts().astype(int).to_dict()
    if "statut_reclamation" in df.columns:
        payload["par_statut"] = (
            df["statut_reclamation"].dropna().astype("string").value_counts().astype(int).to_dict()
        )
    return payload


def quantitative_facts(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    satisfaction, claims = split_frames(frames)
    sat_scores = (
        pd.to_numeric(satisfaction["satisfaction_normalisee"], errors="coerce").dropna()
        if not satisfaction.empty and "satisfaction_normalisee" in satisfaction.columns
        else pd.Series(dtype=float)
    )
    product_stats = _product_stats(satisfaction)
    weakest = product_stats[0] if product_stats else None
    strongest = product_stats[-1] if product_stats else None
    join_possible = False
    join_reason = (
        "Les enquêtes utilisent id_unique (ex. FR-0001) alors que les réclamations "
        "utilisent colis_id (ex. COL-FR-00001). Aucune clé commune ne permet une jointure ligne à ligne. "
        "Seule une comparaison agrégée par pays / produit est possible."
    )
    return {
        "satisfaction": {
            "nombre_reponses": int(len(satisfaction)),
            "nombre_notes_valides": int(sat_scores.count()),
            "satisfaction_moyenne": _round(sat_scores.mean()) if not sat_scores.empty else None,
            "satisfaction_min": _round(sat_scores.min()) if not sat_scores.empty else None,
            "satisfaction_max": _round(sat_scores.max()) if not sat_scores.empty else None,
            "taux_notes_ge_4_pct": _round((sat_scores >= 4).mean() * 100) if not sat_scores.empty else None,
            "par_pays": _country_stats(satisfaction),
            "par_produit": product_stats,
            "produit_plus_faible": weakest,
            "produit_plus_fort": strongest,
        },
        "reclamations": _claims_stats(claims),
        "lien_satisfaction_reclamations": {
            "jointure_ligne_possible": join_possible,
            "raison": join_reason,
        },
    }


def evidence_rows(frames: dict[str, pd.DataFrame], limit: int = 8) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source_id, frame in frames.items():
        if frame.empty:
            continue
        sample = frame.head(max(1, limit // max(len(frames), 1)))
        records = sample.where(pd.notna(sample), None).to_dict(orient="records")
        for record in records:
            compact = {
                key: value
                for key, value in record.items()
                if not str(key).startswith("_") and value is not None
            }
            compact["_source"] = source_id
            rows.append(compact)
            if len(rows) >= limit:
                return rows
    return rows
