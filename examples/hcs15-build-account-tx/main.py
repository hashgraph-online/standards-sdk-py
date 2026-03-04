"""HCS-15 typed account options example."""

from __future__ import annotations

from standards_sdk_py.hcs15 import (
    HCS15Client,
    Hcs15CreateBaseAccountOptions,
    Hcs15CreatePetalAccountOptions,
)

_TEST_OPERATOR_ID = "0.0.1001"
_TEST_OPERATOR_KEY = (
    "302e020100300506032b657004220420fb77695921a5c79474d57c42006f03ff"
    "178688514d797fb30f60fd0fc9e82716"
)
_TEST_BASE_PRIVATE_KEY = (
    "302e020100300506032b657004220420c3f8c7d1a0ca5d4bb5561a7b7d8895f0"
    "773f64e2f802305c6d7a5cab6f0172f3"
)


def main() -> None:
    base_options = Hcs15CreateBaseAccountOptions(
        initialBalance=2.0,
        accountMemo="hcs15 base account example",
    )
    petal_options = Hcs15CreatePetalAccountOptions(
        basePrivateKey=_TEST_BASE_PRIVATE_KEY,
        initialBalance=1.0,
        accountMemo="hcs15 petal account example",
    )
    client = HCS15Client(
        operator_id=_TEST_OPERATOR_ID,
        operator_key=_TEST_OPERATOR_KEY,
        network="testnet",
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
