"""Standardize the five raw survey schemas and export Excel and JSON copies."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd


CANONICAL_COLUMNS = (
    "id_enquete",
    "date_enquete",
    "pays",
    "code_produit",
    "taille_colis",
    "fragile",
    "poids_kg",
    "prix_livraison_eur",
    "statut_colis",
    "delai_livraison",
    "relation_livreur",
    "etat_colis",
    "service_client",
    "satisfaction_globale",
    "commentaire_global",
)


COUNTRY_MAPPINGS = {
    "Allemagne": {
        "umfrage_id": "id_enquete",
        "umfrage_datum": "date_enquete",
        "land": "pays",
        "produkt_code": "code_produit",
        "taille_colis": "taille_colis",
        "fragile": "fragile",
        "poids_kg": "poids_kg",
        "prix_livraison_eur": "prix_livraison_eur",
        "statut_colis": "statut_colis",
        "lieferzeit": "delai_livraison",
        "zusteller": "relation_livreur",
        "paket_zustand": "etat_colis",
        "kundenservice": "service_client",
        "gesamtzufriedenheit": "satisfaction_globale",
    },
    "Canada": {
        "survey_id": "id_enquete",
        "survey_date": "date_enquete",
        "country": "pays",
        "product_code": "code_produit",
        "taille_colis": "taille_colis",
        "fragile": "fragile",
        "poids_kg": "poids_kg",
        "prix_livraison_eur": "prix_livraison_eur",
        "statut_colis": "statut_colis",
        "delivery_time": "delai_livraison",
        "delivery_person": "relation_livreur",
        "parcel_condition": "etat_colis",
        "customer_service": "service_client",
        "overall_satisfaction": "satisfaction_globale",
    },
    "Espagne": {
        "id_encuesta": "id_enquete",
        "fecha_encuesta": "date_enquete",
        "pais": "pays",
        "producto": "code_produit",
        "taille_colis": "taille_colis",
        "fragile": "fragile",
        "poids_kg": "poids_kg",
        "prix_livraison_eur": "prix_livraison_eur",
        "statut_colis": "statut_colis",
        "plazo_entrega": "delai_livraison",
        "relacion_repartidor": "relation_livreur",
        "estado_paquete": "etat_colis",
        "servicio_cliente": "service_client",
        "satisfaccion_global": "satisfaction_globale",
    },
    "France": {
        "id_enquete": "id_enquete",
        "date_enquete": "date_enquete",
        "pays": "pays",
        "code_produit": "code_produit",
        "taille_colis": "taille_colis",
        "fragile": "fragile",
        "poids_kg": "poids_kg",
        "prix_livraison_eur": "prix_livraison_eur",
        "statut_colis": "statut_colis",
        "delai_livraison": "delai_livraison",
        "relation_livreur": "relation_livreur",
        "etat_colis": "etat_colis",
        "service_client": "service_client",
        "satisfaction_globale": "satisfaction_globale",
    },
    "Maroc": {
        "id_enquete": "id_enquete",
        "date_enquete": "date_enquete",
        "pays": "pays",
        "code_produit": "code_produit",
        "taille_colis": "taille_colis",
        "fragile": "fragile",
        "poids_kg": "poids_kg",
        "prix_livraison_eur": "prix_livraison_eur",
        "statut_colis": "statut_colis",
        "commentaire_global": "commentaire_global",
    },
}


def standardize_dataset(country: str, df: pd.DataFrame) -> pd.DataFrame:
    """Rename one country schema and add missing canonical columns as null."""
    if country not in COUNTRY_MAPPINGS:
        raise ValueError(f"Mapping absent pour {country}")

    mapping = COUNTRY_MAPPINGS[country]
    unknown_columns = [column for column in df.columns if column not in mapping]
    if unknown_columns:
        raise ValueError(f"Colonnes non mappees pour {country}: {unknown_columns}")

    standardized = df.rename(columns=mapping).reindex(columns=CANONICAL_COLUMNS).copy()
    standardized["pays"] = standardized["pays"].astype("string").str.strip()
    return standardized


def _json_value(value: object) -> object:
    """Convert pandas and NumPy values to JSON-compatible values."""
    if pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    return value


def export_standardized_dataset(
    country: str, df: pd.DataFrame, output_dir: Path
) -> dict[str, object]:
    """Write one standardized dataset to Excel and JSON."""
    standardized = standardize_dataset(country, df)
    excel_dir = output_dir / "excel"
    json_dir = output_dir / "json"
    excel_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    excel_path = excel_dir / f"{country.lower()}_standard.xlsx"
    json_path = json_dir / f"{country.lower()}_standard.json"
    standardized.to_excel(excel_path, index=False)

    records = [
        {column: _json_value(value) for column, value in row.items()}
        for row in standardized.to_dict(orient="records")
    ]
    json_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "country": country,
        "rows": len(standardized),
        "columns": len(standardized.columns),
        "missing_columns": ", ".join(
            column for column in CANONICAL_COLUMNS if standardized[column].isna().all()
        ),
        "excel_path": str(excel_path),
        "json_path": str(json_path),
        "status": "success",
    }


def standardize_all(
    datasets: dict[str, pd.DataFrame], output_dir: Path
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Standardize all five datasets and return data plus an in-memory audit."""
    standardized_datasets = {}
    report_rows = []
    for country, df in datasets.items():
        standardized = standardize_dataset(country, df)
        standardized_datasets[country] = standardized
        report_rows.append(export_standardized_dataset(country, df, output_dir))

    return standardized_datasets, pd.DataFrame(report_rows)