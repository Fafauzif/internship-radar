from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def rotating_slice(items: list[dict[str, Any]], count: int, seed: int | None = None) -> list[dict[str, Any]]:
    if not items or count <= 0:
        return []
    count = min(count, len(items))
    if seed is None:
        seed = datetime.now(timezone.utc).timetuple().tm_yday
    start = (seed * count) % len(items)
    return [items[(start + i) % len(items)] for i in range(count)]


def plan_queries(searches: dict[str, Any], settings: dict[str, Any], mode: str = "scheduled") -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    budgets = settings["budgets"]
    j_count = int(budgets["jsearch_max_per_run"])
    e_count = int(budgets["exa_max_per_run"])
    if mode == "manual":
        manual_multiplier = float(settings.get("pipeline", {}).get("manual_budget_multiplier", 1.0))
        j_count = max(1, int(j_count * manual_multiplier))
        e_count = max(1, int(e_count * manual_multiplier))
    return (
        rotating_slice(searches.get("jsearch", []), j_count),
        rotating_slice(searches.get("exa", []), e_count, seed=datetime.now(timezone.utc).timetuple().tm_yday + 11),
    )
