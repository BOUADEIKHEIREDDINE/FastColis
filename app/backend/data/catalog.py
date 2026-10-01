"""Catalog of datasets the dashboard is allowed to load."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.backend.paths import normalized_dir, raw_dir


@dataclass(frozen=True)
class SourceSpec:
    id: str
    label: str
    kind: str
    relative_path: Path
    country_label: str | None = None

    def absolute_path(self) -> Path:
        return project_file(self.relative_path)


def project_file(relative_path: Path) -> Path:
    if relative_path.parts[0] == "BDD_normalized_format":
        return normalized_dir() / Path(*relative_path.parts[1:])
    if relative_path.parts[0] == "BDD_raw":
        return raw_dir() / Path(*relative_path.parts[1:])
    raise ValueError(f"Chemin de source non autorise: {relative_path}")


SOURCE_CATALOG: tuple[SourceSpec, ...] = (
    SourceSpec(
        "france",
        "France",
        "satisfaction",
        Path("BDD_normalized_format/france_normalisee.xlsx"),
        "France",
    ),
    SourceSpec(
        "espagne",
        "Espagne",
        "satisfaction",
        Path("BDD_normalized_format/espagne_normalisee.xlsx"),
        "Espagne",
    ),
    SourceSpec(
        "maroc",
        "Maroc",
        "satisfaction",
        Path("BDD_normalized_format/maroc_normalisee.xlsx"),
        "Maroc",
    ),
    SourceSpec(
        "allemagne",
        "Allemagne",
        "satisfaction",
        Path("BDD_normalized_format/allemagne_normalisee.xlsx"),
        "Allemagne",
    ),
    SourceSpec(
        "canada",
        "Canada",
        "satisfaction",
        Path("BDD_normalized_format/canada_normalisee.xlsx"),
        "Canada",
    ),
    SourceSpec(
        "reclamations",
        "Réclamations",
        "reclamations",
        Path("BDD_raw/reclamations_curated.xlsx"),
    ),
)

SOURCE_BY_ID = {source.id: source for source in SOURCE_CATALOG}
SATISFACTION_SOURCE_IDS = [source.id for source in SOURCE_CATALOG if source.kind == "satisfaction"]
LABEL_TO_ID = {source.label.lower(): source.id for source in SOURCE_CATALOG}
COUNTRY_TO_ID = {
    source.country_label.lower(): source.id
    for source in SOURCE_CATALOG
    if source.country_label
}
