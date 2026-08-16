from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any

import requests

from ..http_utils import APIError


@dataclass
class UsageSnapshot:
    jsearch_requests: int = 0
    exa_requests: int = 0
    exa_cost_usd: float = 0.0
    gemini_calls: int = 0


class AppsScriptWebhookClient:
    def __init__(self, url: str, secret: str) -> None:
        self.url = url
        self.secret = secret.encode("utf-8")

    def _envelope(self, payload: dict[str, Any]) -> dict[str, str]:
        payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("ascii").rstrip("=")
        timestamp = str(int(time.time()))
        nonce = secrets.token_urlsafe(16)
        message = f"{timestamp}.{nonce}.{payload_b64}".encode("utf-8")
        signature = base64.urlsafe_b64encode(hmac.new(self.secret, message, hashlib.sha256).digest()).decode("ascii").rstrip("=")
        return {"timestamp": timestamp, "nonce": nonce, "payload_b64": payload_b64, "signature": signature}

    def post(self, payload: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
        try:
            response = requests.post(self.url, json=self._envelope(payload), timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise APIError(f"Apps Script webhook request failed: {exc}") from exc
        if not isinstance(data, dict) or not data.get("ok"):
            raise APIError(f"Apps Script webhook rejected request: {data}")
        return data

    def ping(self) -> dict[str, Any]:
        return self.post({"action": "ping"})

    def usage_snapshot(self) -> UsageSnapshot:
        data = self.post({"action": "usage_snapshot"})
        usage = data.get("usage", {})
        return UsageSnapshot(
            jsearch_requests=int(usage.get("jsearch_requests", 0) or 0),
            exa_requests=int(usage.get("exa_requests", 0) or 0),
            exa_cost_usd=float(usage.get("exa_cost_usd", 0.0) or 0.0),
            gemini_calls=int(usage.get("gemini_calls", 0) or 0),
        )
