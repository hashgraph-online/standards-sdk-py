import httpx
import pytest

from standards_sdk_py.registry_broker import AsyncRegistryBrokerClient
from standards_sdk_py.shared.http import AsyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/search":
        return httpx.Response(200, json={"hits": [], "total": 1, "page": 1, "limit": 20})
    if request.url.path == "/chat/session":
        return httpx.Response(200, json={"sessionId": "s-2", "encryption": None})
    if request.url.path == "/skills/publish":
        return httpx.Response(200, json={"jobId": "job-2", "accepted": True})
    return httpx.Response(200, json={"ok": True})


@pytest.mark.asyncio
async def test_registry_broker_core_flows_async() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)),
    )
    client = AsyncRegistryBrokerClient(transport=transport)

    search = await client.search(query="hcs")
    assert search.total == 1

    session = await client.create_session({"uaid": "test-uaid"})
    assert session.session_id == "s-2"

    publish = await client.publish_skill({"name": "skill-b", "version": "1.0.0"})
    assert publish.job_id == "job-2"

    dynamic = await client.adapter_registry_categories()
    assert isinstance(dynamic, dict)

    await client.close()
