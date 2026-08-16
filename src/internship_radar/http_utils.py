from __future__ import annotations

import random
import time
from typing import Any

import requests


class APIError(RuntimeError):
    pass


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: int = 35,
    attempts: int = 3,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_body,
                timeout=timeout,
            )
            if response.status_code == 429 or 500 <= response.status_code < 600:
                retry_after = response.headers.get("Retry-After", "").strip()
                if retry_after and retry_after.replace(".", "", 1).isdigit():
                    # Preserve the server's backoff hint for the retry loop below.
                    setattr(response, "_radar_retry_after", float(retry_after))
                error = APIError(f"HTTP {response.status_code}: {response.text[:500]}")
                setattr(error, "retry_after", getattr(response, "_radar_retry_after", None))
                raise error
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise APIError(f"Expected JSON object from {url}")
            return data
        except (requests.RequestException, ValueError, APIError) as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                break
            retry_after = getattr(exc, "retry_after", None)
            sleep_for = max(float(retry_after or 0), (2 ** attempt) + random.random())
            time.sleep(sleep_for)
    raise APIError(f"Request failed after {attempts} attempts: {last_error}")
