"""HCS-17 state hash payload example."""

from __future__ import annotations

import os

from standards_sdk_py.hcs17 import (
    HCS17Client,
    Hcs17ComputeAndPublishOptions,
    Hcs17StateHashMessage,
    Hcs17SubmitMessageOptions,
)


def _required_env(primary: str, secondary: str | None = None) -> str:
    for name in (primary, secondary):
        if not name:
            continue
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    if secondary:
        raise RuntimeError(f"Missing required environment variable: {primary} (or {secondary})")
    raise RuntimeError(f"Missing required environment variable: {primary}")


def main() -> None:
    operator_id = _required_env("TESTNET_HEDERA_ACCOUNT_ID", "HEDERA_ACCOUNT_ID")
    operator_key = _required_env("TESTNET_HEDERA_PRIVATE_KEY", "HEDERA_PRIVATE_KEY")
    network = os.getenv("HEDERA_NETWORK", "testnet").strip() or "testnet"

    state_message = Hcs17StateHashMessage(
        state_hash="6d2f4b7308b3d7bd74a85f5d9f54f6f1278cc5fd1fe9c1c911f66fce2e112ebf",
        topics=["0.0.700080", "0.0.700081"],
        account_id="0.0.700082",
        epoch=12,
        m="hcs17 state hash",
    )
    submit_options = Hcs17SubmitMessageOptions(topicId="0.0.700080", message=state_message)
    compute_options = Hcs17ComputeAndPublishOptions(
        accountId="0.0.700082",
        accountPublicKey="302a300506032b6570032100b4f2d8e4",
        topics=["0.0.700080", "0.0.700081"],
        publishTopicId="0.0.700080",
    )
    client = HCS17Client(
        operator_id=operator_id,
        operator_key=operator_key,
        network=network,
    )
    print(
        {
            "key_type": client.get_key_type(),
            "submit_options": submit_options.model_dump(by_alias=True, exclude_none=True),
            "compute_options": compute_options.model_dump(by_alias=True, exclude_none=True),
        }
    )


if __name__ == "__main__":
    main()
