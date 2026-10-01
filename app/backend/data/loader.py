"""Load and cache the six application datasets. Does not rerun the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import pandas as pd

from app.backend.data.catalog import SOURCE_BY_ID, SOURCE_CATALOG, SourceSpec


CLAIMS_PRODUCT_MAP = {
    "COLIS_STANDARD": "STANDARD",
    "COLIS_EXPRESS": "EXPRESS",
    "COLIS_PREMIUM": "PREMIUM",
    "STANDARD": "STANDARD",
    "EXPRESS": "EXPRESS",
    "PREMIUM": "PREMIUM",
}


def _to_frame(path, *args, **kwargs) -> pd.DataFrame:
    return pd.read_excel(path, *args, **kwargs)


def _enrich_satisfaction(df: pd.DataFrame, spec: SourceSpec) -> pd.DataFrame:
    result = df.copy()
    result["_source_id"] = spec.id
    result["_source_label"] = spec.label
    result["_kind"] = spec.kind
    if "date_enquete" in result.columns:
        result["date_enquete"] = pd.to_datetime(result["date_enquete"], errors="coerce")
    if "satisfaction_normalisee" in result.columns:
        result["satisfaction_normalisee"] = pd.to_numeric(
            result["satisfaction_normalisee"], errors="coerce"
        )
    return result


def _enrich_claims(df: pd.DataFrame, spec: SourceSpec) -> pd.DataFrame:
    result = df.copy()
    result["_source_id"] = spec.id
    result["_source_label"] = spec.label
    result["_kind"] = spec.kind
    if "date_reclamation" in result.columns:
        result["date_reclamation"] = pd.to_datetime(result["date_reclamation"], errors="coerce")
    if "code_produit_global" in result.columns:
        result["produit_global"] = (
            result["code_produit_global"].astype("string").str.upper().map(CLAIMS_PRODUCT_MAP)
        )
        result["produit_global"] = result["produit_global"].fillna(
            result["code_produit_global"].astype("string").str.extract(
                r"(STANDARD|EXPRESS|PREMIUM)", expand=False
            )
        )
    return result


def load_source_frame(spec: SourceSpec) -> tuple[pd.DataFrame | None, str | None]:
    path = spec.absolute_path()
    if not path.exists():
        return None, f"Fichier introuvable: {path.name}"
    try:
        frame = _to_frame(path)
    except Exception as error:  # noqa: BLE001 - surface any read failure to the UI
        return None, f"Impossible de lire {path.name}: {error}"
    if frame.empty:
        return None, f"Le fichier {path.name} est vide."
    if spec.kind == "reclamations":
        return _enrich_claims(frame, spec), None
    return _enrich_satisfaction(frame, spec), None


@dataclass
class LoadedSource:
    spec: SourceSpec
    frame: pd.DataFrame | None
    error: str | None

    @property
    def available(self) -> bool:
        return self.frame is not None and self.error is None


class DatasetStore:
    """In-memory cache of the six Excel sources."""

    def __init__(self) -> None:
        self._loaded: dict[str, LoadedSource] = {}
        for spec in SOURCE_CATALOG:
            frame, error = load_source_frame(spec)
            self._loaded[spec.id] = LoadedSource(spec=spec, frame=frame, error=error)

    def list_sources(self) -> list[dict[str, Any]]:
        rows = []
        for source_id, loaded in self._loaded.items():
            rows.append(
                {
                    "id": source_id,
                    "label": loaded.spec.label,
                    "kind": loaded.spec.kind,
                    "available": loaded.available,
                    "error": loaded.error,
                    "rows": 0 if loaded.frame is None else int(len(loaded.frame)),
                    "columns": [] if loaded.frame is None else [str(c) for c in loaded.frame.columns],
                }
            )
        return rows

    def get(self, source_id: str) -> LoadedSource:
        if source_id not in self._loaded:
            raise KeyError(f"Source inconnue: {source_id}")
        return self._loaded[source_id]

    def frames(self, source_ids: list[str]) -> dict[str, pd.DataFrame]:
        result = {}
        for source_id in source_ids:
            loaded = self.get(source_id)
            if loaded.available and loaded.frame is not None:
                result[source_id] = loaded.frame.copy()
        return result

    def missing(self, source_ids: list[str]) -> list[str]:
        messages = []
        for source_id in source_ids:
            if source_id not in SOURCE_BY_ID:
                messages.append(f"Source inconnue: {source_id}")
                continue
            loaded = self.get(source_id)
            if not loaded.available:
                messages.append(loaded.error or f"Source indisponible: {source_id}")
        return messages


@lru_cache(maxsize=1)
def get_store() -> DatasetStore:
    return DatasetStore()
