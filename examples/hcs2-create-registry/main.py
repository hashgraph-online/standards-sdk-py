"""HCS-2 typed payload example."""

from __future__ import annotations

import os

from standards_sdk_py.hcs2 import (
    CreateRegistryOptions,
    HCS2Client,
    Hcs2RegisterMessage,
    Hcs2RegistryType,
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

    create_options = CreateRegistryOptions(
        registryType=Hcs2RegistryType.INDEXED,
        ttl=3600,
        useOperatorAsAdmin=True,
        useOperatorAsSubmit=True,
    )
    register_message = Hcs2RegisterMessage(
        p="hcs-2",
        t_id="0.0.700001",
        metadata="hcs://1/0.0.700001",
        m="hcs2 example register",
    )

    client = HCS2Client(
        operator_id=operator_id,
        operator_key=operator_key,
        network=network,
    )
    try:
        print(
            {
                "key_type": client.get_key_type(),
                "create_registry_options": create_options.model_dump(
                    by_alias=True,
                    exclude_none=True,
                ),
                "register_message": register_message.model_dump(by_alias=True, exclude_none=True),
            }
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
