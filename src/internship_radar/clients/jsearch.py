from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)

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

        raw_data = data.get("data", [])

if isinstance(raw_data, dict):
    payload = raw_data.get("jobs", raw_data.get("results", []))
    data_shape = f"dict keys={list(raw_data.keys())}"
else:
    payload = raw_data
    data_shape = type(raw_data).__name__

if not isinstance(payload, list):
    log.warning(
        "JSearch unexpected response | backend=%s | status=%r | request_id=%r | data_shape=%s",
        self.backend,
        data.get("status"),
        data.get("request_id"),
        data_shape,
    )
    return []

log.info(
    "JSearch API response | backend=%s | status=%r | request_id=%r | jobs=%d | data_shape=%s",
    self.backend,
    data.get("status"),
    data.get("request_id"),
    len(payload),
    data_shape,
)

return payload
