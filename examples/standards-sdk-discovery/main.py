"""Registry Broker discovery example with mocked transport."""

from __future__ import annotations

import httpx

from standards_sdk_py.registry_broker import RegistryBrokerClient
from standards_sdk_py.shared.http import SyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/search":
        return httpx.Response(
            200,
            json={
                "hits": [{"uaid": "uaid:example:agent-a", "score": 0.99}],
                "total": 1,
                "page": 1,
                "limit": 20,
            },
        )
    if request.url.path == "/stats":
        return httpx.Response(
            200,
            json={
                "total_agents": 1280,
                "active_agents": 412,
            },
        )
    if request.url.path == "/protocols":
        return httpx.Response(200, json={"protocols": [{"name": "hcs10"}, {"name": "a2a"}]})
    return httpx.Response(200, json={"ok": True})


def main() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = RegistryBrokerClient(transport=transport)
    try:
        search = client.search(query="hcs")
        stats = client.stats()
        protocols = client.list_protocols()
        top_hit = None
        if search.hits:
            first_hit = search.hits[0]
            if isinstance(first_hit, dict):
                top_hit = first_hit.get("uaid")
            else:
                top_hit = getattr(first_hit, "uaid", None)
        print(
            {
                "search_total": search.total,
                "top_hit": top_hit,
                "agents_indexed": stats.total_agents,
                "active_agents": stats.active_agents,
                "protocols": [item["name"] for item in protocols.protocols],
            }
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
