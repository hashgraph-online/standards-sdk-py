"""Registry Broker UAID DNS verification example with mocked transport."""

from __future__ import annotations

import httpx

from standards_sdk_py.registry_broker import RegistryBrokerClient
from standards_sdk_py.shared.http import SyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/verification/dns/verify":
        return httpx.Response(
            200,
            json={
                "verified": True,
                "uaid": "uaid:aid:ans-demo;uid=ans://v1.0.0.demo.agent",
                "domain": "example.com",
            },
        )
    if request.url.path.startswith("/verification/dns/status/"):
        return httpx.Response(
            200,
            json={
                "verified": True,
                "method": "dns-txt",
                "domain": "example.com",
            },
        )
    return httpx.Response(200, json={"ok": True, "path": request.url.path})


def main() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = RegistryBrokerClient(transport=transport)
    try:
        verify = client.call_operation(
            "verify_uaid_dns_txt",
            body={
                "uaid": "uaid:aid:ans-demo;uid=ans://v1.0.0.demo.agent",
                "domain": "example.com",
                "challengeToken": "demo-token",
            },
        )
        status = client.call_operation(
            "get_verification_dns_status",
            path_params={"uaid": "uaid:aid:ans-demo"},
        )
        print({"verify": verify, "status": status})
    finally:
        client.close()


if __name__ == "__main__":
    main()
