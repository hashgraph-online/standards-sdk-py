"""HCS-7 config + metadata payload example."""

from __future__ import annotations

import os

from standards_sdk_py.hcs7 import (
    AbiDefinition,
    AbiIo,
    EvmConfigPayload,
    HCS7Client,
    Hcs7ConfigType,
    Hcs7RegisterConfigOptions,
    Hcs7RegisterMetadataOptions,
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

    config_options = Hcs7RegisterConfigOptions(
        registryTopicId="0.0.700030",
        type=Hcs7ConfigType.EVM,
        evm=EvmConfigPayload(
            contractAddress="0x1111111111111111111111111111111111111111",
            abi=AbiDefinition(
                name="resolve",
                inputs=[AbiIo(name="name", type="string")],
                outputs=[AbiIo(type="string")],
                stateMutability="view",
                type="function",
            ),
        ),
        memo="hcs7 config example",
    )
    metadata_options = Hcs7RegisterMetadataOptions(
        registryTopicId="0.0.700030",
        metadataTopicId="0.0.700031",
        weight=1,
        tags=["python", "hcs7"],
        data={"source": "standards-sdk-py-example"},
        memo="hcs7 metadata example",
    )

    client = HCS7Client(
        operator_id=operator_id,
        operator_key=operator_key,
        network=network,
    )
    try:
        print(
            {
                "key_type": client.get_key_type(),
                "register_config": config_options.model_dump(by_alias=True, exclude_none=True),
                "register_metadata": metadata_options.model_dump(by_alias=True, exclude_none=True),
            }
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
