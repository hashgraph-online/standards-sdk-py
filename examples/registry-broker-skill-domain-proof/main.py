"""Registry Broker skill domain proof example with mocked transport."""

from __future__ import annotations

import httpx

from standards_sdk_py.registry_broker import RegistryBrokerClient
from standards_sdk_py.shared.http import SyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/skills/verification/status":
        return httpx.Response(
            200,
            json={
                "name": "demo-skill",
                "version": "1.0.0",
                "domainProof": {"verified": False},
            },
        )
    if request.url.path == "/skills/verification/domain/challenge":
        return httpx.Response(
            200,
            json={
                "domain": "example.com",
                "txtRecordName": "_hol-proof.example.com",
                "txtRecordValue": "hol-skill-verification=demo-token",
            },
        )
    if request.url.path == "/skills/verification/domain/verify":
        return httpx.Response(
            200,
            json={"verified": True, "domain": "example.com", "trustDelta": 10},
        )
    return httpx.Response(200, json={"ok": True, "path": request.url.path})


def main() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = RegistryBrokerClient(transport=transport)
    try:
        status = client.call_operation(
            "get_skill_verification_status",
            query={"name": "demo-skill", "version": "1.0.0"},
        )
        challenge = client.call_operation(
            "create_skill_domain_proof_challenge",
            body={"name": "demo-skill", "version": "1.0.0", "domain": "example.com"},
        )
        verify = client.call_operation(
            "verify_skill_domain_proof",
            body={
                "name": "demo-skill",
                "version": "1.0.0",
                "domain": "example.com",
                "challengeToken": "demo-token",
            },
        )
        print({"status": status, "challenge": challenge, "verify": verify})
    finally:
        client.close()


if __name__ == "__main__":
    main()
