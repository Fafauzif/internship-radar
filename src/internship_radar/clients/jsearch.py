from __future__ import annotations

import os
from typing import Any

from ..http_utils import request_json


class JSearchClient:
    """JSearch client supporting RapidAPI or OpenWebNinja direct auth.

    Backend is selected with JSEARCH_BACKEND=rapidapi|openwebninja.
    The default is rapidapi because that is the common JSearch signup path.
    """

    def __init__(self, api_key: str, backend: str | None = None) -> None:
        self.api_key = api_key
        self.backend = (backend or os.getenv("JSEARCH_BACKEND") or "rapidapi").lower()
        if self.backend not in {"rapidapi", "openwebninja"}:
            raise ValueError("JSEARCH_BACKEND must be 'rapidapi' or 'openwebninja'")

    def search(self, query: str, *, country: str = "id", date_posted: str = "month") -> list[dict[str, Any]]:
        if self.backend == "openwebninja":
            data = request_json(
                "GET",
                "https://api.openwebninja.com/jsearch/search-v2",
                headers={"x-api-key": self.api_key},
                params={"query": query, "country": country, "language": "en"},
                attempts=1,
            )
        else:
            data = request_json(
                "GET",
                "https://jsearch.p.rapidapi.com/search",
                headers={
                    "x-rapidapi-key": self.api_key,
                    "x-rapidapi-host": "jsearch.p.rapidapi.com",
                },
                params={
                    "query": query,
                    "page": "1",
                    "num_pages": "1",
                    "country": country,
                    "date_posted": date_posted,
                },
                attempts=1,
            )

        payload = data.get("data", [])
        if isinstance(payload, dict):
            payload = payload.get("jobs", payload.get("results", []))
        return payload if isinstance(payload, list) else []
