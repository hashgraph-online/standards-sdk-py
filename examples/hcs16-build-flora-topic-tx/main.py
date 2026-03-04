"""HCS-16 flora topic payload example."""

from __future__ import annotations

from standards_sdk_py.hcs16 import (
    FloraTopicType,
    HCS16Client,
    Hcs16CreateFloraTopicOptions,
    Hcs16KeyList,
)

_TEST_OPERATOR_ID = "0.0.1001"
_TEST_OPERATOR_KEY = (
    "302e020100300506032b657004220420fb77695921a5c79474d57c42006f03ff"
    "178688514d797fb30f60fd0fc9e82716"
)


def main() -> None:
    create_topic_options = Hcs16CreateFloraTopicOptions(
        floraAccountId="0.0.700070",
        topicType=FloraTopicType.COMMUNICATION,
        submitKey=Hcs16KeyList(keys=["302a300506032b6570032100b4f2d8e4"], threshold=1),
        transactionMemo="hcs16 topic example",
    )
    client = HCS16Client(
        operator_id=_TEST_OPERATOR_ID,
        operator_key=_TEST_OPERATOR_KEY,
        network="testnet",
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
