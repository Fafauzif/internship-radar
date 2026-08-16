from __future__ import annotations

import logging
import os
from typing import Any

from ..http_utils import request_json

log = logging.getLogger(__name__)


LANGUAGE_BY_COUNTRY = {
    "id": "id",
    "sg": "en",
    "my": "en",
    "th": "th",
    "vn": "vi",
    "us": "en",
    "gb": "en",
}


class JSearchClient:
    def __init__(
        self,
        api_key: str,
        backend: str | None = None,
    ) -> None:
        self.api_key = api_key.strip()

        self.backend = (
            backend
            or os.getenv("JSEARCH_BACKEND")
            or "rapidapi"
        ).strip().lower()

        if self.backend not in {
            "rapidapi",
            "openwebninja",
        }:
            raise ValueError(
                "JSEARCH_BACKEND must be "
                "'rapidapi' or 'openwebninja'"
            )

    def search(
        self,
        query: str,
        *,
        country: str = "id",
        date_posted: str = "month",
    ) -> list[dict[str, Any]]:

        country = country.lower()

        # -----------------------------------------------------
        # OPENWEBNINJA
        # -----------------------------------------------------

        if self.backend == "openwebninja":
            language = LANGUAGE_BY_COUNTRY.get(
                country,
                "en",
            )

            log.info(
                "JSearch request | backend=openwebninja | "
                "country=%s | language=%s | "
                "date_posted=%s | query=%r",
                country,
                language,
                date_posted,
                query,
            )

            data = request_json(
                "GET",
                "https://api.openwebninja.com/jsearch/search-v2",
                headers={
                    "x-api-key": self.api_key,
                },
                params={
                    "query": query,
                    "num_pages": 1,
                    "country": country,
                    "language": language,
                    "date_posted": date_posted,
                },
                attempts=1,
            )

        # -----------------------------------------------------
        # RAPIDAPI
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # RESPONSE DIAGNOSTICS
        # -----------------------------------------------------

        log.info(
            "JSearch raw response | "
            "status=%r | request_id=%r | "
            "top_level_keys=%s",
            data.get("status"),
            data.get("request_id"),
            list(data.keys()),
        )

        raw_data = data.get("data")

        # OpenWebNinja:
        #
        # {
        #   "data": {
        #       "jobs": [...],
        #       "cursor": "..."
        #   }
        # }
        if isinstance(raw_data, dict):
            jobs = raw_data.get("jobs", [])

        # RapidAPI / other compatible shape:
        #
        # {
        #   "data": [...]
        # }
        elif isinstance(raw_data, list):
            jobs = raw_data

        else:
            jobs = []

        if not isinstance(jobs, list):
            log.warning(
                "JSearch jobs field had unexpected type=%s",
                type(jobs).__name__,
            )
            return []

        log.info(
            "JSearch parsed response | "
            "backend=%s | jobs=%d",
            self.backend,
            len(jobs),
        )

        if jobs:
            first = jobs[0]

            log.info(
                "JSearch first result | "
                "title=%r | employer=%r | location=%r",
                first.get("job_title"),
                first.get("employer_name"),
                first.get("job_location"),
            )

        else:
            log.warning(
                "JSearch returned ZERO jobs | "
                "status=%r | request_id=%r",
                data.get("status"),
                data.get("request_id"),
            )

        return jobs
