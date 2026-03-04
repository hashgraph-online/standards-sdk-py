"""Mirror topic message example with mocked transport."""

from __future__ import annotations

import base64

import httpx

from standards_sdk_py.mirror import MirrorNodeClient
from standards_sdk_py.shared.http import SyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/messages"):
        encoded = base64.b64encode(b"hello mirror").decode("utf-8")
        return httpx.Response(
            200,
            json={
                "messages": [
                    {
                        "consensus_timestamp": "1700000000.000000001",
                        "message": encoded,
                        "payer_account_id": "0.0.700200",
                        "running_hash": "abc",
                        "running_hash_version": 3,
                        "sequence_number": 1,
                        "topic_id": "0.0.700201",
                    }
                ],
                "links": {"next": None},
            },
        )
    return httpx.Response(200, json={"ok": True})


def main() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = MirrorNodeClient(transport=transport)
    messages = client.get_topic_messages("0.0.700201", limit=1, order="asc")
    filtered = client.get_topic_messages_by_filter("0.0.700201", {"limit": 1, "order": "asc"})
    print(
        {
            "count": len(messages.messages),
            "first_sequence": messages.messages[0].sequence_number if messages.messages else None,
            "decoded_messages": filtered,
        }
    )


if __name__ == "__main__":
    main()
