"""HCS-27 checkpoint helper example with mocked transport."""

from __future__ import annotations

import httpx

from standards_sdk_py.hcs27 import HCS27Client
from standards_sdk_py.shared.http import SyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/hcs27/buildTopicMemo":
        return httpx.Response(200, json={"memo": "hcs-27:checkpoint:3600"})
    if request.url.path == "/hcs27/hashLeaf":
        return httpx.Response(200, json={"leafHashHex": "ab12cd34"})
    if request.url.path == "/hcs27/merkleRootFromEntries":
        return httpx.Response(200, json={"rootHashHex": "ff001122"})
    if request.url.path == "/hcs27/validateCheckpointMessage":
        return httpx.Response(200, json={"valid": True})
    return httpx.Response(200, json={"ok": True, "path": request.url.path})


def main() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = HCS27Client(transport=transport)
    try:
        topic_memo = client.build_topic_memo({"ttl": 3600})
        leaf = client.hash_leaf({"entry": {"key": "a", "value": "1"}})
        root = client.merkle_root_from_entries(
            {"entries": [{"key": "a", "value": "1"}, {"key": "b", "value": "2"}]}
        )
        valid = client.validate_checkpoint_message(
            {
                "message": {
                    "type": "ans-checkpoint-v1",
                    "root": {"treeSize": 2, "rootHashB64": "abc"},
                },
                "strict": False,
            }
        )
        print(
            {
                "topic_memo": topic_memo,
                "leaf": leaf,
                "root": root,
                "valid": valid,
            }
        )
    finally:
        transport.close()


if __name__ == "__main__":
    main()
