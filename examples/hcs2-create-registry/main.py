"""HCS-2 typed payload example."""

from __future__ import annotations

from standards_sdk_py.hcs2 import (
    CreateRegistryOptions,
    HCS2Client,
    Hcs2RegisterMessage,
    Hcs2RegistryType,
)

_TEST_OPERATOR_ID = "0.0.1001"
_TEST_OPERATOR_KEY = (
    "302e020100300506032b657004220420fb77695921a5c79474d57c42006f03ff"
    "178688514d797fb30f60fd0fc9e82716"
)


def main() -> None:
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
        operator_id=_TEST_OPERATOR_ID,
        operator_key=_TEST_OPERATOR_KEY,
        network="testnet",
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
