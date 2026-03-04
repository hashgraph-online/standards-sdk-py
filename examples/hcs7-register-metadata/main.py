"""HCS-7 config + metadata payload example."""

from __future__ import annotations

from standards_sdk_py.hcs7 import (
    AbiDefinition,
    AbiIo,
    EvmConfigPayload,
    HCS7Client,
    Hcs7ConfigType,
    Hcs7RegisterConfigOptions,
    Hcs7RegisterMetadataOptions,
)

_TEST_OPERATOR_ID = "0.0.1001"
_TEST_OPERATOR_KEY = (
    "302e020100300506032b657004220420fb77695921a5c79474d57c42006f03ff"
    "178688514d797fb30f60fd0fc9e82716"
)


def main() -> None:
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
        operator_id=_TEST_OPERATOR_ID,
        operator_key=_TEST_OPERATOR_KEY,
        network="testnet",
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
