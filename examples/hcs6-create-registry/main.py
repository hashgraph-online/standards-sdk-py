"""HCS-6 typed payload example."""

from __future__ import annotations

import os

from standards_sdk_py.hcs6 import (
    HCS6Client,
    Hcs6CreateRegistryOptions,
    Hcs6RegisterEntryOptions,
    build_hcs6_hrl,
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

    create_options = Hcs6CreateRegistryOptions(ttl=3600, useOperatorAsSubmit=True)
    register_options = Hcs6RegisterEntryOptions(
        targetTopicId="0.0.700020",
        memo="hcs6 register example",
    )

    client = HCS6Client(
        operator_id=operator_id,
        operator_key=operator_key,
        network=network,
    )
    try:
        print(
            {
                "key_type": client.get_key_type(),
                "hcs6_hrl": build_hcs6_hrl("0.0.700020"),
                "create_registry_options": create_options.model_dump(
                    by_alias=True,
                    exclude_none=True,
                ),
                "register_options": register_options.model_dump(by_alias=True, exclude_none=True),
            }
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
