from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Paths:
    root: Path
    settings: Path
    profile: Path
    searches: Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_paths() -> Paths:
    root = project_root()
    return Paths(
        root=root,
        settings=root / "config" / "settings.json",
        profile=root / "config" / "profile.json",
        searches=root / "config" / "searches.json",
    )


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Missing config file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc


def load_all(paths: Paths | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    paths = paths or default_paths()
    settings = load_json(paths.settings)
    profile = load_json(paths.profile)
    searches = load_json(paths.searches)
    validate_config(settings, profile, searches)
    return settings, profile, searches


def validate_config(settings: dict[str, Any], profile: dict[str, Any], searches: dict[str, Any]) -> None:
    required_settings = ["timezone", "gemini_model", "budgets", "pipeline"]
    for key in required_settings:
        if key not in settings:
            raise ConfigError(f"settings.json missing '{key}'")

    if not profile.get("education", {}).get("expected_graduation"):
        raise ConfigError("profile.json must include education.expected_graduation")
    if not profile.get("career_tracks"):
        raise ConfigError("profile.json must include career_tracks")
    if not searches.get("exa") or not searches.get("jsearch"):
        raise ConfigError("searches.json must include both 'exa' and 'jsearch' query lists")

    budgets = settings["budgets"]
    for key in ("jsearch_monthly_cap", "exa_monthly_budget_usd", "jsearch_max_per_run", "exa_max_per_run", "gemini_max_per_run"):
        if key not in budgets:
            raise ConfigError(f"settings.json budgets missing '{key}'")


def require_env(*names: str) -> dict[str, str]:
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise ConfigError("Missing required environment variables: " + ", ".join(missing))
    return {name: os.environ[name] for name in names}
