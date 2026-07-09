"""Load base, search_space, and benchmarks configs. Paths relative to repo root."""

import yaml
from pathlib import Path
from typing import Any

# Repo root: research_evolver/src/utils -> research_evolver -> repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_CONFIG_DIR = _REPO_ROOT / "research_evolver" / "configs"


def _load_yaml(name: str) -> dict[str, Any]:
    path = _CONFIG_DIR / name
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_base() -> dict[str, Any]:
    return _load_yaml("base.yaml")


def load_search_space() -> dict[str, Any]:
    return _load_yaml("search_space.yaml")


def load_benchmarks() -> dict[str, Any]:
    return _load_yaml("benchmarks.yaml")


def get_db_path() -> Path:
    base = load_base()
    return _REPO_ROOT / base.get("storage", {}).get("db_path", "research_evolver/data/evolver.db")


def get_artifacts_root() -> Path:
    base = load_base()
    return _REPO_ROOT / base.get("storage", {}).get("artifacts_root", "research_evolver/artifacts")
