"""Project-root path helpers. Never hardcode user-specific absolute paths."""

from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def modules_dir() -> Path:
    return project_root() / "modules"


def normalized_dir() -> Path:
    return project_root() / "BDD_normalized_format"


def raw_dir() -> Path:
    return project_root() / "BDD_raw"


def frontend_dist() -> Path:
    return project_root() / "app" / "frontend" / "dist"
