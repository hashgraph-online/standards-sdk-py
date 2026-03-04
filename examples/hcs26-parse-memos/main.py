"""HCS-26 memo build/parse example with mocked transport."""

from __future__ import annotations

import httpx

from standards_sdk_py.hcs26 import HCS26Client
from standards_sdk_py.shared.http import SyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/hcs26/buildTopicMemo":
        return httpx.Response(200, json={"memo": "hcs-26:1:3600:0"})
    if request.url.path == "/hcs26/parseTopicMemo":
        return httpx.Response(200, json={"indexed": True, "ttl": 3600, "topicType": 0})
    if request.url.path == "/hcs26/buildTransactionMemo":
        return httpx.Response(200, json={"memo": "hcs-26:op:0:0"})
    if request.url.path == "/hcs26/parseTransactionMemo":
        return httpx.Response(200, json={"op": "register", "topicType": 0})
    return httpx.Response(200, json={"ok": True, "path": request.url.path})


def main() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = HCS26Client(transport=transport)
    try:
        topic_memo = client.build_topic_memo({"indexed": True, "ttl": 3600, "topicType": 0})
        parsed_topic_memo = client.parse_topic_memo({"memo": "hcs-26:1:3600:0"})
        tx_memo = client.build_transaction_memo({"op": "register", "topicType": 0})
        parsed_tx_memo = client.parse_transaction_memo({"memo": "hcs-26:op:0:0"})
        print(
            {
                "topic_memo": topic_memo,
                "parsed_topic_memo": parsed_topic_memo,
                "tx_memo": tx_memo,
                "parsed_tx_memo": parsed_tx_memo,
            }
        )
    finally:
        transport.close()


if __name__ == "__main__":
    main()
