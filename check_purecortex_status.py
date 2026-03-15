import json
import os
import sys

import requests


def check_purecortex_status(base_url: str = "https://purecortex.ai"):
    """Check the live PURECORTEX health endpoint and basic public API surfaces."""
    health_url = f"{base_url.rstrip('/')}/health"
    agents_url = f"{base_url.rstrip('/')}/api/agents/registry"
    governance_url = f"{base_url.rstrip('/')}/api/governance/overview"

    print("--- Checking PURECORTEX Status ---")
    print(f"Health URL: {health_url}")

    try:
        health_response = requests.get(health_url, timeout=15)
        health_response.raise_for_status()
        health_data = health_response.json()

        print("\n✅ Health OK")
        print("-" * 40)
        print(json.dumps(health_data, indent=2))
        print("-" * 40)

        for label, url in (
            ("Agent registry", agents_url),
            ("Governance overview", governance_url),
        ):
            response = requests.get(url, timeout=15)
            print(f"{label}: {response.status_code} {url}")

        return health_data
    except Exception as exc:
        print(f"\n❌ Error checking PURECORTEX: {exc}")
        return None


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv("PURECORTEX_API_URL", "https://purecortex.ai")
    check_purecortex_status(base_url)
