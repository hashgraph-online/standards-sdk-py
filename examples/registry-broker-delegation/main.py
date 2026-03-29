"""Registry Broker delegation demo."""

from __future__ import annotations

import os

from standards_sdk_py import (
    RegistryBrokerAuthConfig,
    RegistryBrokerClient,
    SdkConfig,
    SdkNetworkConfig,
)

DEFAULT_REGISTRY_BASE_URL = "https://hol.org/registry/api/v1"
DEFAULT_TASK = "Review an SDK PR and split out docs and verification subtasks."


def _build_client() -> RegistryBrokerClient:
    base_url = os.getenv("REGISTRY_BROKER_BASE_URL", DEFAULT_REGISTRY_BASE_URL).strip()
    api_key = os.getenv("REGISTRY_BROKER_API_KEY", "").strip() or None
    account_id = os.getenv("REGISTRY_BROKER_ACCOUNT_ID", "").strip() or None
    config = SdkConfig(
        network=SdkNetworkConfig(registry_broker_base_url=base_url),
        registry_auth=RegistryBrokerAuthConfig(api_key=api_key, account_id=account_id),
    )
    return RegistryBrokerClient(config=config)


def main() -> None:
    client = _build_client()
    try:
        limit_raw = os.getenv("REGISTRY_BROKER_DELEGATION_LIMIT", "3").strip()
        try:
            limit = int(limit_raw)
        except ValueError:
            print(
                "error: REGISTRY_BROKER_DELEGATION_LIMIT must be a positive integer, "
                f"got {limit_raw!r}"
            )
            return
        if limit <= 0:
            print("error: REGISTRY_BROKER_DELEGATION_LIMIT must be greater than zero")
            return
        response = client.delegate(
            task=os.getenv("REGISTRY_BROKER_DELEGATION_TASK", DEFAULT_TASK).strip(),
            context=os.getenv("REGISTRY_BROKER_DELEGATION_CONTEXT", "").strip() or None,
            limit=limit,
        )
        print(f"task={response.task}")
        print(f"shouldDelegate={response.should_delegate}")
        if response.local_first_reason:
            print(f"localFirstReason={response.local_first_reason}")
        for opportunity in response.opportunities:
            print(f"\nopportunity={opportunity.id} title={opportunity.title}")
            print(f"reason={opportunity.reason}")
            if not opportunity.candidates:
                print("topCandidate=<none>")
                continue
            candidate = opportunity.candidates[0]
            print(f"topCandidate={candidate.uaid} label={candidate.label or '<unknown>'}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
