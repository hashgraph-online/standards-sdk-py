"""HCS-10 message workflow example with mocked transport."""

from __future__ import annotations

import httpx

from standards_sdk_py.hcs10 import HCS10Client
from standards_sdk_py.shared.http import SyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/hcs10/sendMessage":
        return httpx.Response(
            200,
            json={
                "success": True,
                "topicId": "0.0.700040",
                "sequenceNumber": 42,
            },
        )
    return httpx.Response(200, json={"ok": True, "path": request.url.path})


def main() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = HCS10Client(transport=transport)
    try:
        response = client.send_message(
            {
                "topicId": "0.0.700040",
                "message": "hello from hcs10",
                "memo": "hcs10 example message",
            }
        )
        print(response)
    finally:
        transport.close()


if __name__ == "__main__":
    main()
