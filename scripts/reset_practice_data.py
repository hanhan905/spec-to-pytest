"""Reset local community data before or after an AI-generated test batch."""

from __future__ import annotations

import argparse

from framework.api.practice_client import PracticeApiClient
from framework.config.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    settings = Settings()
    if not settings.control_token.get_secret_value() or not settings.instance_id:
        raise SystemExit(
            "Reset requires an authorized test instance; "
            "owned-run fixtures handle this automatically."
        )
    with PracticeApiClient(settings.api_url, control_token=settings.control_token) as client:
        if client.health().json().get("instance_id") != settings.instance_id:
            raise SystemExit("Instance identity mismatch; refusing to reset.")
        response = client.reset()
        response.raise_for_status()
    print("community data reset")


if __name__ == "__main__":
    main()
