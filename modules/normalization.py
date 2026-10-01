"""Normalize cleaned standardized FastColis datasets to a common business model."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd


FINAL_COLUMNS = (
    "id_unique",
    "date_enquete",
    "pays",
    "code_produit",
    "produit_global",
    "satisfaction_normalisee",
    "commentaire_global",
)

PRODUCT_REFERENCE = {
    "France": {
        "COLIS_STANDARD": "STANDARD",
        "COLIS_EXPRESS": "EXPRESS",
        "COLIS_PREMIUM": "PREMIUM",
    },
    "Espagne": {
        "PAQUETE_ESTANDAR": "STANDARD",
        "PAQUETE_EXPRESS": "EXPRESS",
        "PAQUETE_PREMIUM": "PREMIUM",
    },
    "Canada": {
        "PARCEL_STANDARD": "STANDARD",
        "PARCEL_EXPRESS": "EXPRESS",
        "PARCEL_PREMIUM": "PREMIUM",
    },
    "Maroc": {
        "COLIS_STANDARD": "STANDARD",
        "COLIS_EXPRESS": "EXPRESS",
        "COLIS_PREMIUM": "PREMIUM",
    },
    "Allemagne": {
        "PAK_001": "STANDARD",
        "PAK_002": "EXPRESS",
        "PAK_003": "PREMIUM",
    },
}

COUNTRY_ALIASES = {
    "Deutschland": "Allemagne",
    "España": "Espagne",
}


def canonical_country(value: object) -> str:
    """Return the project country label used by the reference tables."""
    return COUNTRY_ALIASES.get(str(value), str(value))


def build_product_reference() -> pd.DataFrame:
    """Build the explicit source-code to global-product reference."""
    return pd.DataFrame(
        [
            {
                "pays": country,
                "code_produit_source": code,
                "produit_global": product,
            }
            for country, mapping in PRODUCT_REFERENCE.items()
            for code, product in mapping.items()
        ]
    )


def harmonize_products(df: pd.DataFrame) -> pd.DataFrame:
    """Add the global product label without changing source product codes."""
    result = df.copy()
    result["pays"] = result["pays"].map(canonical_country)
    result["produit_global"] = [
        PRODUCT_REFERENCE.get(country, {}).get(code)
        for country, code in zip(result["pays"], result["code_produit"])
    ]
    if result["produit_global"].isna().any():
        unknown = result.loc[result["produit_global"].isna(), ["pays", "code_produit"]]
        raise ValueError(f"Codes produits non mappes: {unknown.drop_duplicates().to_dict('records')}")
    return result


def _normalize_text(value: object) -> str:
    text = "" if pd.isna(value) else str(value).lower()
    return "".join(
        character
        for character in unicodedata.normalize("NFD", text)
        if unicodedata.category(character) != "Mn"
    )


def score_morocco_comment(value: object) -> float:
    """Convert a Moroccan comment to a documented provisional score on five."""
    if pd.isna(value):
        return np.nan

    text = _normalize_text(value)
    strong_positive = ("tout etait parfait", "excellente experience", "pleinement satisfait")
    strong_negative = ("tres insatisfait", "tres insatisfaite", "experience decevante")
    positive = ("excellent", "parfait", "satisfait", "bonne", "bien", "rapide", "professionnel")
    negative = ("insatisfaisant", "insatisfait", "decevant", "retard", "endommage", "probleme", "mauvais", "lent")

    if any(phrase in text for phrase in strong_positive):
        return 5.0
    if any(phrase in text for phrase in strong_negative):
        return 1.0

    positive_count = sum(bool(re.search(rf"\b{re.escape(word)}\b", text)) for word in positive)
    negative_count = sum(bool(re.search(rf"\b{re.escape(word)}\b", text)) for word in negative)
    if negative_count >= 2:
        return 2.0
    if negative_count and positive_count:
        return 3.0
    if negative_count:
        return 2.0
    if positive_count:
        return 4.0
    return 3.0


def normalize_satisfaction(country: str, df: pd.DataFrame) -> pd.Series:
    """Convert one country's satisfaction representation to a score from 1 to 5."""
    if country in {"France", "Allemagne"}:
        scores = pd.to_numeric(df["satisfaction_globale"], errors="coerce")
    elif country == "Canada":
        scores = pd.to_numeric(df["satisfaction_globale"], errors="coerce") / 2
    elif country == "Espagne":
        scores = df["satisfaction_globale"].map({"Bajo": 1.0, "Medio": 3.0, "Alto": 5.0})
    elif country == "Maroc":
        scores = df["commentaire_global"].map(score_morocco_comment)
    else:
        raise ValueError(f"Pays non supporte: {country}")

    return scores.where(scores.between(1, 5))


def normalize_dataset(country: str, df: pd.DataFrame) -> pd.DataFrame:
    """Normalize products, identifiers, dates, and satisfaction for one country."""
    result = harmonize_products(df)
    result["id_unique"] = result["id_enquete"]
    result["satisfaction_normalisee"] = normalize_satisfaction(country, result)
    return result.reindex(columns=FINAL_COLUMNS)


def normalize_all(
    datasets: dict[str, pd.DataFrame],
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    """Normalize all countries and return country tables, a consolidated table, and an audit."""
    normalized = {}
    audit_rows = []
    for country, df in datasets.items():
        normalized_df = normalize_dataset(country, df)
        normalized[country] = normalized_df
        audit_rows.append(
            {
                "pays": country,
                "lignes": len(normalized_df),
                "colonnes": len(normalized_df.columns),
                "scores_renseignes": int(normalized_df["satisfaction_normalisee"].notna().sum()),
                "produits_manquants": int(normalized_df["produit_global"].isna().sum()),
            }
        )

    consolidated = pd.concat(normalized.values(), ignore_index=True)
    if len(consolidated) != sum(len(df) for df in datasets.values()):
        raise ValueError("Le nombre de lignes a changé pendant la normalisation")
    return normalized, consolidated, pd.DataFrame(audit_rows)


def export_normalized_outputs(
    normalized_datasets: dict[str, pd.DataFrame],
    consolidated: pd.DataFrame,
    output_dir: Path,
) -> dict[str, Path]:
    """Export one normalized Excel and JSON database per country."""
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = {}
    country_slugs = {
        "Allemagne": "allemagne",
        "Canada": "canada",
        "Espagne": "espagne",
        "France": "france",
        "Maroc": "maroc",
    }
    for country, df in normalized_datasets.items():
        if not df["satisfaction_normalisee"].dropna().between(1, 5).all():
            raise ValueError(f"Scores hors intervalle pour {country}")
        slug = country_slugs[country]
        excel_path = output_dir / f"{slug}_normalisee.xlsx"
        json_path = output_dir / f"{slug}_normalisee.json"
        df.to_excel(excel_path, index=False)
        df.to_json(json_path, orient="records", force_ascii=False, date_format="iso", indent=2)
        outputs[f"{country}_excel"] = excel_path
        outputs[f"{country}_json"] = json_path

    base_excel = output_dir / "fastcolis_base_normalisee.xlsx"
    base_json = output_dir / "fastcolis_base_normalisee.json"
    consolidated.to_excel(base_excel, index=False)
    consolidated.to_json(base_json, orient="records", force_ascii=False, date_format="iso", indent=2)
    reference = build_product_reference()
    reference_excel = output_dir / "referentiel_produits.xlsx"
    reference_json = output_dir / "referentiel_produits.json"
    reference.to_excel(reference_excel, index=False)
    reference.to_json(reference_json, orient="records", force_ascii=False, indent=2)

    outputs.update({
        "base_excel": base_excel,
        "base_json": base_json,
        "reference_excel": reference_excel,
        "reference_json": reference_json,
    })
    return outputs