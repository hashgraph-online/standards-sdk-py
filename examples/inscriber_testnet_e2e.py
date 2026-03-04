"""Run Registry Broker-backed inscriber flow on testnet."""

from __future__ import annotations

import os

from standards_sdk_py.inscriber import (
    InscriberClient,
    InscribeViaRegistryBrokerOptions,
    InscriptionInput,
)


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    network = (os.getenv("INSCRIBER_HEDERA_NETWORK") or "testnet").strip().lower()
    if network != "testnet":
        raise RuntimeError("Set INSCRIBER_HEDERA_NETWORK=testnet for this E2E script.")

    api_key = (
        os.getenv("REGISTRY_BROKER_LEDGER_API_KEY") or os.getenv("REGISTRY_BROKER_API_KEY") or ""
    ).strip()
    if not api_key:
        api_key = _required("REGISTRY_BROKER_API_KEY")

    base_url = (os.getenv("REGISTRY_BROKER_BASE_URL") or "https://hol.org/registry/api/v1").strip()

    client = InscriberClient()
    result = client.inscribe_via_registry_broker(
        InscriptionInput(
            type="buffer",
            buffer=b"standards-sdk-py testnet e2e inscription",
            fileName="standards-sdk-py-testnet-e2e.txt",
            mimeType="text/plain",
        ),
        InscribeViaRegistryBrokerOptions(
            base_url=base_url,
            api_key=api_key,
            mode="file",
            metadata={"source": "standards-sdk-py-e2e"},
            tags=["python", "sdk", "inscriber", "testnet"],
            wait_for_confirmation=True,
            wait_timeout_ms=180000,
            poll_interval_ms=2000,
        ),
    )
    print(
        {
            "confirmed": result.confirmed,
            "status": result.status,
            "topicId": result.topic_id,
            "network": result.network,
            "hrl": result.hrl,
            "jobId": result.job_id,
        },
    )


if __name__ == "__main__":
    main()
