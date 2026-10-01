"""Reusable data loading, profiling, filtering, and imputation functions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


TARGET_ALIASES = (
    "rating",
    "overall_satisfaction",
    "satisfaction_globale",
    "satisfaction",
    "global_satisfaction",
)

FINAL_DATABASE_COLUMNS = {
    "taille_colis",
    "fragile",
    "poids_kg",
    "prix_livraison_eur",
    "statut_colis",
}


def normalize_column_name(name: Any) -> str:
    """Return a stable comparison form for a column name."""
    return (
        str(name).strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")
    )


def find_target_column(df: pd.DataFrame) -> str | None:
    """Find the first supported satisfaction/rating column."""
    normalized = {normalize_column_name(column): column for column in df.columns}
    for alias in TARGET_ALIASES:
        if alias in normalized:
            return normalized[alias]
    return None


def load_dataset(country: str, path: Path) -> pd.DataFrame:
    """Load one Excel or JSON dataset and normalize its column labels."""
    if not path.exists():
        raise FileNotFoundError(f"Dataset absent pour {country}: {path}")

    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    elif path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
        df = pd.json_normalize(raw if isinstance(raw, list) else [raw])
    else:
        raise ValueError(f"Format non supporte: {path.suffix}")

    df.columns = [str(column).strip() for column in df.columns]
    return df


def load_datasets(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Load the five country files from the raw data directory."""
    files = {
        "Allemagne": data_dir / "Allemagne.xlsx",
        "Canada": data_dir / "Canada.xlsx",
        "Espagne": data_dir / "Espagne.json",
        "France": data_dir / "France.xlsx",
        "Maroc": data_dir / "Maroc.xlsx",
    }
    return {country: load_dataset(country, path) for country, path in files.items()}


def profile_dataset(country: str, df: pd.DataFrame) -> dict[str, Any]:
    """Summarize structure, duplicates, and missing values for one dataset."""
    return {
        "country": country,
        "rows": len(df),
        "columns": len(df.columns),
        "numeric_columns": int(df.select_dtypes(include=np.number).shape[1]),
        "categorical_columns": int(df.select_dtypes(exclude=np.number).shape[1]),
        "duplicate_rows": int(df.duplicated().sum()),
        "total_missing": int(df.isna().sum().sum()),
        "missing_rate_global_pct": round(df.isna().mean().mean() * 100, 2),
        "target_column": find_target_column(df),
    }


def build_structure_report(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build a comparative structure report."""
    rows = []
    for country, df in datasets.items():
        row = profile_dataset(country, df)
        row["dtypes"] = "; ".join(f"{column}: {dtype}" for column, dtype in df.dtypes.items())
        rows.append(row)
    return pd.DataFrame(rows)


def build_missing_report(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Report missing counts and rates for every country and column."""
    rows = []
    for country, df in datasets.items():
        for column in df.columns:
            missing_count = int(df[column].isna().sum())
            rows.append(
                {
                    "country": country,
                    "column": column,
                    "dtype": str(df[column].dtype),
                    "missing_count": missing_count,
                    "row_count": len(df),
                    "missing_rate_pct": round(df[column].isna().mean() * 100, 2),
                }
            )
    return pd.DataFrame(rows)


def calculate_correlations(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Calculate Pearson correlations for numeric variables and the target."""
    rows = []
    for country, df in datasets.items():
        target = find_target_column(df)
        numeric_df = df.select_dtypes(include=np.number)
        if target is None or target not in numeric_df.columns:
            continue

        for column in numeric_df.columns:
            if column == target:
                continue
            valid = numeric_df[[column, target]].dropna()
            correlation = valid[column].corr(valid[target]) if len(valid) >= 2 else np.nan
            rows.append(
                {
                    "country": country,
                    "target": target,
                    "variable": column,
                    "pearson_r": correlation,
                    "abs_r": abs(correlation) if pd.notna(correlation) else np.nan,
                    "n_valid": len(valid),
                }
            )
    return pd.DataFrame(
        rows,
        columns=["country", "target", "variable", "pearson_r", "abs_r", "n_valid"],
    )


def filter_low_correlation(
    datasets: dict[str, pd.DataFrame],
    correlations: pd.DataFrame,
    threshold: float = 0.2,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Remove numeric variables whose absolute correlation is below a threshold."""
    filtered_datasets = {}
    removed_rows = correlations[
        (correlations["abs_r"] < threshold)
        & ~correlations["variable"].isin(FINAL_DATABASE_COLUMNS)
    ].copy()
    if not removed_rows.empty:
        removed_rows["threshold"] = threshold
        removed_rows["justification"] = f"Pearson |r| < {threshold}: faible correlation avec le target."

    for country, df in datasets.items():
        country_rows = removed_rows[removed_rows["country"] == country]
        columns_to_remove = country_rows["variable"].tolist()
        filtered_datasets[country] = df.drop(columns=columns_to_remove, errors="ignore").copy()

    return filtered_datasets, removed_rows


def impute_numeric_missing(
    datasets: dict[str, pd.DataFrame],
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Impute numeric missing values: median above 5%, mean at or below 5%."""
    imputed_datasets = {}
    log_rows = []

    for country, df in datasets.items():
        clean = df.copy()
        for column in clean.select_dtypes(include=np.number).columns:
            missing_rate = clean[column].isna().mean()
            missing_before = int(clean[column].isna().sum())
            method = "no_missing"
            value = np.nan

            if missing_before and missing_rate > 0.05:
                method = "median"
                value = clean[column].median()
            elif missing_before:
                method = "mean"
                value = clean[column].mean()

            if method in {"median", "mean"}:
                clean[column] = clean[column].fillna(value)

            log_rows.append(
                {
                    "country": country,
                    "column": column,
                    "missing_rate_before_pct": round(missing_rate * 100, 2),
                    "missing_before": missing_before,
                    "method": method,
                    "imputation_value": float(value) if pd.notna(value) else np.nan,
                    "missing_after": int(clean[column].isna().sum()),
                }
            )
        imputed_datasets[country] = clean

    return imputed_datasets, pd.DataFrame(log_rows)


def compare_missing_values(
    before: dict[str, pd.DataFrame], after: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """Compare total missing values before and after treatment."""
    return pd.DataFrame(
        [
            {
                "country": country,
                "missing_before": int(before[country].isna().sum().sum()),
                "missing_after": int(after[country].isna().sum().sum()),
                "missing_removed": int(before[country].isna().sum().sum())
                - int(after[country].isna().sum().sum()),
            }
            for country in before
        ]
    )


def calculate_outlier_rates(
    datasets: dict[str, pd.DataFrame], multiplier: float = 1.5
) -> pd.DataFrame:
    """Calculate IQR outlier counts and rates for numeric columns."""
    rows = []
    for country, df in datasets.items():
        for column in df.select_dtypes(include=np.number).columns:
            values = df[column].dropna()
            if values.empty:
                continue

            first_quartile = values.quantile(0.25)
            third_quartile = values.quantile(0.75)
            interquartile_range = third_quartile - first_quartile
            lower_bound = first_quartile - multiplier * interquartile_range
            upper_bound = third_quartile + multiplier * interquartile_range
            outlier_count = int(
                ((values < lower_bound) | (values > upper_bound)).sum()
            )

            rows.append(
                {
                    "country": country,
                    "column": column,
                    "valid_count": len(values),
                    "outlier_count": outlier_count,
                    "outlier_rate_pct": round(outlier_count / len(values) * 100, 2),
                    "q1": first_quartile,
                    "q3": third_quartile,
                    "iqr": interquartile_range,
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                }
            )

    return pd.DataFrame(
        rows,
        columns=[
            "country",
            "column",
            "valid_count",
            "outlier_count",
            "outlier_rate_pct",
            "q1",
            "q3",
            "iqr",
            "lower_bound",
            "upper_bound",
        ],
    )


def correct_data_quality(
    datasets: dict[str, pd.DataFrame], outlier_report: pd.DataFrame
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Fill categorical gaps and cap numeric outliers using the IQR bounds."""
    corrected_datasets = {}
    correction_rows = []

    for country, df in datasets.items():
        corrected = df.copy()

        for column in corrected.select_dtypes(include=["object", "string"]).columns:
            missing_before = int(corrected[column].isna().sum())
            if missing_before:
                modes = corrected[column].mode(dropna=True)
                replacement = modes.iloc[0] if not modes.empty else "Non renseigne"
                corrected[column] = corrected[column].fillna(replacement)
                correction_rows.append(
                    {
                        "country": country,
                        "column": column,
                        "issue": "missing_categorical",
                        "count_before": missing_before,
                        "count_corrected": missing_before,
                        "method": "mode",
                        "value": replacement,
                    }
                )

        country_outliers = outlier_report[outlier_report["country"] == country]
        for row in country_outliers.itertuples(index=False):
            column = row.column
            values = corrected[column]
            outlier_mask = (values < row.lower_bound) | (values > row.upper_bound)
            outlier_count = int(outlier_mask.fillna(False).sum())
            if outlier_count:
                corrected[column] = values.clip(row.lower_bound, row.upper_bound)
                correction_rows.append(
                    {
                        "country": country,
                        "column": column,
                        "issue": "numeric_outlier",
                        "count_before": outlier_count,
                        "count_corrected": outlier_count,
                        "method": "clip_iqr_bounds",
                        "value": f"[{row.lower_bound}, {row.upper_bound}]",
                    }
                )

        corrected_datasets[country] = corrected

    return corrected_datasets, pd.DataFrame(
        correction_rows,
        columns=[
            "country",
            "column",
            "issue",
            "count_before",
            "count_corrected",
            "method",
            "value",
        ],
    )


