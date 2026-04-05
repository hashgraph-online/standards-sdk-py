"""HCS-15 typed account options example."""

from __future__ import annotations

import os

from standards_sdk_py.hcs15 import (
    HCS15Client,
    Hcs15CreateBaseAccountOptions,
    Hcs15CreatePetalAccountOptions,
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
    base_private_key = os.getenv("HCS15_BASE_PRIVATE_KEY")
    if not base_private_key or not base_private_key.strip():
        base_private_key = operator_key
    base_private_key = base_private_key.strip()

    base_options = Hcs15CreateBaseAccountOptions(
        initialBalance=2.0,
        accountMemo="hcs15 base account example",
    )
    petal_options = Hcs15CreatePetalAccountOptions(
        basePrivateKey=base_private_key,
        initialBalance=1.0,
        accountMemo="hcs15 petal account example",
    )
    client = HCS15Client(
        operator_id=operator_id,
        operator_key=operator_key,
        network=network,
    )
    try:
        print(
            {
                "key_type": client.get_key_type(),
                "base_options": base_options.model_dump(by_alias=True, exclude_none=True),
                "petal_options": petal_options.model_dump(by_alias=True, exclude_none=True),
            }
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
