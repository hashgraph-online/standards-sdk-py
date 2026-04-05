"""HCS-16 flora topic payload example."""

from __future__ import annotations

import os

from standards_sdk_py.hcs16 import (
    FloraTopicType,
    HCS16Client,
    Hcs16CreateFloraTopicOptions,
    Hcs16KeyList,
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

    create_topic_options = Hcs16CreateFloraTopicOptions(
        floraAccountId="0.0.700070",
        topicType=FloraTopicType.COMMUNICATION,
        submitKey=Hcs16KeyList(keys=["302a300506032b6570032100b4f2d8e4"], threshold=1),
        transactionMemo="hcs16 topic example",
    )
    client = HCS16Client(
        operator_id=operator_id,
        operator_key=operator_key,
        network=network,
    )
    parsed = client.parseTopicMemo("hcs-16:0.0.700070:0")
    print(
        {
            "parsed_topic_memo": parsed,
            "create_topic_options": create_topic_options.model_dump(
                by_alias=True, exclude_none=True
            ),
        }
    )


if __name__ == "__main__":
    main()
