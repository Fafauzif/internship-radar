from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from .clients.webhook import AppsScriptWebhookClient
from .config import ConfigError, load_all, require_env
from .pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Internship Radar")
    parser.add_argument("--mode", choices=["scheduled", "manual"], default="scheduled")
    parser.add_argument("--validate-only", action="store_true", help="Validate JSON config without calling external services")
    parser.add_argument("--ping-webhook", action="store_true", help="Verify Apps Script HMAC/webhook setup only")
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args()
    try:
        settings, profile, searches = load_all()
        if args.validate_only:
            print("Configuration valid.")
            return 0

        if args.ping_webhook:
            require_env("APPS_SCRIPT_WEBHOOK_URL", "WEBHOOK_SECRET")
            client = AppsScriptWebhookClient(os.environ["APPS_SCRIPT_WEBHOOK_URL"], os.environ["WEBHOOK_SECRET"])
            print(json.dumps(client.ping(), indent=2))
            return 0

        require_env("JSEARCH_API_KEY", "EXA_API_KEY", "GEMINI_API_KEY", "APPS_SCRIPT_WEBHOOK_URL", "WEBHOOK_SECRET")
        run = run_pipeline(settings, profile, searches, mode=args.mode)
        print(json.dumps(run.to_dict(), indent=2))
        return 0 if run.status in {"SUCCESS", "PARTIAL_SUCCESS"} else 2
    except (ConfigError, RuntimeError, KeyError, ValueError) as exc:
        logging.exception("Radar run failed")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
