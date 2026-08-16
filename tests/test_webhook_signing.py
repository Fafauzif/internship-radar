import base64
import hashlib
import hmac
import json

from internship_radar.clients.webhook import AppsScriptWebhookClient


def test_envelope_signature_verifies():
    secret = "x" * 48
    client = AppsScriptWebhookClient("https://example.invalid", secret)
    envelope = client._envelope({"action": "ping", "x": 1})
    message = f"{envelope['timestamp']}.{envelope['nonce']}.{envelope['payload_b64']}".encode()
    expected = base64.urlsafe_b64encode(hmac.new(secret.encode(), message, hashlib.sha256).digest()).decode().rstrip("=")
    assert hmac.compare_digest(expected, envelope["signature"])
    raw = envelope["payload_b64"] + "=" * ((4 - len(envelope["payload_b64"]) % 4) % 4)
    assert json.loads(base64.urlsafe_b64decode(raw).decode()) == {"action": "ping", "x": 1}
