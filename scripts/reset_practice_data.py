"""Reset local community data before or after an AI-generated test batch."""

from __future__ import annotations

import argparse

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    response = httpx.post(f"{args.base_url.rstrip('/')}/api/reset", timeout=5)
    response.raise_for_status()
    print("community data reset")


if __name__ == "__main__":
    main()
