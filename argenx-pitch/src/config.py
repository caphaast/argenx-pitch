"""Config loading. All paths are resolved relative to the repo root."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    path = Path(path) if path else ROOT / "config" / "settings.yaml"
    with open(path) as f:
        cfg = yaml.safe_load(f)
    return cfg


def resolve(rel: str | Path) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else ROOT / p
