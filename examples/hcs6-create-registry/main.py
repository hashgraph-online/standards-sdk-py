"""HCS-6 typed payload example."""

from __future__ import annotations

from standards_sdk_py.hcs6 import (
    HCS6Client,
    Hcs6CreateRegistryOptions,
    Hcs6RegisterEntryOptions,
    build_hcs6_hrl,
)

_TEST_OPERATOR_ID = "0.0.1001"
_TEST_OPERATOR_KEY = (
    "302e020100300506032b657004220420fb77695921a5c79474d57c42006f03ff"
    "178688514d797fb30f60fd0fc9e82716"
)


def main() -> None:
    create_options = Hcs6CreateRegistryOptions(ttl=3600, useOperatorAsSubmit=True)
    register_options = Hcs6RegisterEntryOptions(
        targetTopicId="0.0.700020",
        memo="hcs6 register example",
    )

    client = HCS6Client(
        operator_id=_TEST_OPERATOR_ID,
        operator_key=_TEST_OPERATOR_KEY,
        network="testnet",
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
