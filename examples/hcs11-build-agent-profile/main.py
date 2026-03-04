"""HCS-11 agent profile example with mocked transport."""

from __future__ import annotations

import httpx

from standards_sdk_py.hcs11 import HCS11Client
from standards_sdk_py.shared.http import SyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/hcs11/createAIAgentProfile":
        return httpx.Response(
            200,
            json={
                "name": "demo-agent",
                "bio": "Example profile",
                "type": "ai-agent",
                "inboundTopicId": "0.0.700050",
            },
        )
    if request.url.path == "/hcs11/validateProfile":
        return httpx.Response(200, json={"valid": True})
    return httpx.Response(200, json={"ok": True})


def main() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = HCS11Client(transport=transport)
    try:
        profile = client.createAIAgentProfile(
            {
                "name": "demo-agent",
                "bio": "Example profile",
                "model": "gpt-4.1",
                "capabilities": ["hcs10", "registry-broker"],
            }
        )
        validation = client.validateProfile(profile)
        print({"profile": profile, "validation": validation})
    finally:
        transport.close()


if __name__ == "__main__":
    main()
