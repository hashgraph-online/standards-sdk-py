"""HCS-12 register payload example with mocked transport."""

from __future__ import annotations

import httpx

from standards_sdk_py.hcs12 import HCS12Client
from standards_sdk_py.shared.http import SyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/hcs12/registerAction":
        return httpx.Response(
            200,
            json={
                "success": True,
                "topicId": "0.0.700060",
                "sequenceNumber": 7,
            },
        )
    return httpx.Response(200, json={"ok": True, "path": request.url.path})


def main() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = HCS12Client(transport=transport)
    try:
        response = client.register_action(
            {
                "registryTopicId": "0.0.700060",
                "action": "publish",
                "payload": {"name": "demo-action"},
            }
        )
        print(response)
    finally:
        transport.close()


if __name__ == "__main__":
    main()
