import httpx

from standards_sdk_py.registry_broker import RegistryBrokerClient
from standards_sdk_py.shared.http import SyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/search":
        return httpx.Response(200, json={"hits": [], "total": 0, "page": 1, "limit": 20})
    if request.url.path == "/protocols":
        return httpx.Response(200, json={"protocols": [{"name": "hcs10"}]})
    if request.url.path == "/chat/session":
        return httpx.Response(200, json={"sessionId": "s-1", "encryption": None})
    if request.url.path == "/skills/publish":
        return httpx.Response(200, json={"jobId": "job-1", "accepted": True})
    if request.url.path == "/verification/status/test-uaid":
        return httpx.Response(200, json={"verified": True, "method": "dns"})
    return httpx.Response(200, json={"ok": True})


def test_registry_broker_core_flows_sync() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = RegistryBrokerClient(transport=transport)

    search = client.search(query="hcs")
    assert search.total == 0

    protocols = client.list_protocols()
    assert protocols.protocols[0]["name"] == "hcs10"

    session = client.create_session({"uaid": "test-uaid"})
    assert session.session_id == "s-1"

    publish = client.publish_skill({"name": "skill-a", "version": "1.0.0"})
    assert publish.job_id == "job-1"

    verification = client.get_verification_status("test-uaid")
    assert verification.verified is True

    dynamic = client.adapter_registry_categories()
    assert isinstance(dynamic, dict)
