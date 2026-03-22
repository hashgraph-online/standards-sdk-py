"""Registry Broker free-tier registration demo.

This demo defaults to the production Registry API URL and can be pointed to a local
Registry Broker instance by overriding environment variables at runtime.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from standards_sdk_py import (
    ApiError,
    RegistryBrokerAuthConfig,
    RegistryBrokerClient,
    SdkConfig,
    SdkNetworkConfig,
)


DEFAULT_REGISTRY_BASE_URL = "https://hol.org/registry/api/v1"
DEFAULT_REGISTRY_NAMESPACE = "hashgraph-online"
DEFAULT_COMMUNICATION_PROTOCOL = "a2a"
DEFAULT_ATTEMPTS_PER_KEY = 6


def _parse_positive_int(value: str | None, fallback: int) -> int:
    if value is None:
        return fallback
    trimmed = value.strip()
    if not trimmed:
        return fallback
    parsed = int(trimmed)
    if parsed <= 0:
        raise ValueError("Expected a positive integer")
    return parsed


def _extract_api_keys() -> list[str]:
    raw = os.getenv("REGISTRY_BROKER_FREE_TIER_API_KEYS", "").strip()
    if not raw:
        raise RuntimeError(
            "Set REGISTRY_BROKER_FREE_TIER_API_KEYS to one or more comma-separated API keys."
        )
    values = [value.strip() for value in raw.split(",")]
    api_keys = [value for value in values if value]
    if not api_keys:
        raise RuntimeError("REGISTRY_BROKER_FREE_TIER_API_KEYS did not include any usable keys.")
    return api_keys


def _build_registration_payload(attempt_index: int) -> dict[str, Any]:
    endpoint = os.getenv("REGISTRY_BROKER_DEMO_ENDPOINT", "").strip()
    if not endpoint:
        raise RuntimeError(
            "Set REGISTRY_BROKER_DEMO_ENDPOINT to a reachable A2A/ERC-8004 endpoint before running this demo."
        )
    suffix = uuid.uuid4().hex[:10]
    return {
        "profile": {
            "version": "1.0.0",
            "type": 1,
            "display_name": f"Free Tier Demo {attempt_index + 1} {suffix}",
            "bio": "Python SDK free-tier registration validation flow.",
            "aiAgent": {
                "type": 1,
                "model": "gpt-4o-mini",
                "capabilities": [4],
            },
        },
        "registry": DEFAULT_REGISTRY_NAMESPACE,
        "communicationProtocol": DEFAULT_COMMUNICATION_PROTOCOL,
        "endpoint": endpoint,
        "additionalRegistries": [],
    }


def _create_client(api_key: str) -> RegistryBrokerClient:
    base_url = os.getenv("REGISTRY_BROKER_BASE_URL", DEFAULT_REGISTRY_BASE_URL).strip()
    account_id = os.getenv("REGISTRY_BROKER_ACCOUNT_ID", "").strip() or None
    config = SdkConfig(
        network=SdkNetworkConfig(registry_broker_base_url=base_url),
        registry_auth=RegistryBrokerAuthConfig(api_key=api_key, account_id=account_id),
    )
    return RegistryBrokerClient(config=config)


def _register_with_key(api_key: str, attempts: int, key_index: int) -> None:
    print(f"\nTesting API key #{key_index + 1} attempts={attempts}")
    client = _create_client(api_key)
    try:
        for attempt_index in range(attempts):
            payload = _build_registration_payload(attempt_index)
            quote = client.call_operation("get_registration_quote", body=payload)
            if not isinstance(quote, dict):
                raise RuntimeError("Quote response was not a JSON object")
            required_credits = quote.get("requiredCredits")
            shortfall_credits = quote.get("shortfallCredits")
            available_credits = quote.get("availableCredits")
            print(
                f"attempt={attempt_index + 1} quote required={required_credits} "
                f"shortfall={shortfall_credits} available={available_credits}"
            )

            try:
                result = client.register_agent(payload)
            except ApiError as error:
                if error.context.status_code == 402:
                    print(f"attempt={attempt_index + 1} register status=402 body={error.context.body}")
                    continue
                raise

            if isinstance(result, dict):
                status = result.get("status", "created")
                uaid = result.get("uaid")
                attempt_id = result.get("attemptId")
                if status in {"pending", "partial"} and isinstance(attempt_id, str) and attempt_id.strip():
                    final = client.wait_for_registration_completion(
                        attempt_id.strip(),
                        timeout_seconds=5 * 60,
                        interval_seconds=2,
                    )
                    print(
                        f"attempt={attempt_index + 1} register status={status} "
                        f"attemptId={attempt_id} finalStatus={final.status} finalUaid={final.uaid}"
                    )
                    continue
                print(f"attempt={attempt_index + 1} register status={status} uaid={uaid}")
            else:
                print(f"attempt={attempt_index + 1} register response={result}")
    finally:
        client.close()


def main() -> None:
    attempts = _parse_positive_int(
        os.getenv("REGISTRY_BROKER_FREE_TIER_ATTEMPTS"),
        DEFAULT_ATTEMPTS_PER_KEY,
    )
    api_keys = _extract_api_keys()
    for key_index, key in enumerate(api_keys):
        _register_with_key(key, attempts, key_index)


if __name__ == "__main__":
    main()
