"""HCS-14 UAID parsing example with mocked transport."""

from __future__ import annotations

import httpx

from standards_sdk_py.hcs14 import HCS14Client
from standards_sdk_py.shared.http import SyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/hcs14/parseHcs14Did":
        return httpx.Response(
            200,
            json={
                "method": "aid",
                "id": "ans-demo",
                "params": {"uid": "ans://v1.0.0.demo.agent", "registry": "ans"},
            },
        )
    if request.url.path == "/hcs14/createUaid":
        return httpx.Response(
            200,
            json={
                "uaid": "uaid:aid:ans-demo;uid=ans://v1.0.0.demo.agent;registry=ans;proto=a2a",
            },
        )
    return httpx.Response(200, json={"ok": True, "path": request.url.path})


def main() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = HCS14Client(transport=transport)
    try:
        did = client.parse_hcs14_did(
            {
                "did": "did:hcs14:aid:ans-demo;uid=ans://v1.0.0.demo.agent;registry=ans",
            }
        )
        uaid = client.create_uaid(
            {
                "method": "aid",
                "id": "ans-demo",
                "params": {"uid": "ans://v1.0.0.demo.agent", "registry": "ans", "proto": "a2a"},
            }
        )
        print({"did": did, "uaid": uaid})
    finally:
        transport.close()


if __name__ == "__main__":
    main()
