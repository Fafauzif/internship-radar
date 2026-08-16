from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..http_utils import request_json


@dataclass
class ExaSearchResult:
    results: list[dict[str, Any]]
    cost_usd: float


class ExaClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def search(self, query: str, *, num_results: int = 10, user_location: str = "ID") -> ExaSearchResult:
        data = request_json(
            "POST",
            "https://api.exa.ai/search",
            headers={"x-api-key": self.api_key, "Content-Type": "application/json"},
            json_body={
                "query": query,
                "type": "auto",
                "numResults": max(1, min(int(num_results), 10)),
                "userLocation": user_location,
                # Highlights are token-efficient and enough for cheap filtering. Full job
                # descriptions are commonly available on the result page and can still be
                # returned as `text` by Exa when available.
                "contents": {"highlights": True},
            },
            attempts=1,
        )
        cost = data.get("costDollars", {}).get("total", 0.0)
        try:
            cost_f = float(cost or 0.0)
        except (TypeError, ValueError):
            cost_f = 0.0
        return ExaSearchResult(results=data.get("results", []) or [], cost_usd=cost_f)
