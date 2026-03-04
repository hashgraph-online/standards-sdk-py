import httpx
import pytest

from standards_sdk_py.exceptions import ApiError, AuthError
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/ok":
        return httpx.Response(200, json={"ok": True, "path": request.url.path})
    if request.url.path == "/unauthorized":
        return httpx.Response(401, json={"error": "unauthorized"})
    if request.url.path == "/failure":
        return httpx.Response(500, json={"error": "boom"})
    return httpx.Response(404, json={"error": "not-found"})


def test_sync_transport_success() -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    transport = SyncHttpTransport("https://example.test", client=client)
    payload = transport.request_json("GET", "/ok")
    assert payload == {"ok": True, "path": "/ok"}


def test_sync_transport_auth_error() -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    transport = SyncHttpTransport("https://example.test", client=client)
    with pytest.raises(AuthError):
        transport.request_json("GET", "/unauthorized")


def test_sync_transport_api_error() -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    transport = SyncHttpTransport("https://example.test", client=client)
    with pytest.raises(ApiError):
        transport.request_json("GET", "/failure")


@pytest.mark.asyncio
async def test_async_transport_success() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    transport = AsyncHttpTransport("https://example.test", client=client)
    payload = await transport.request_json("GET", "/ok")
    assert payload == {"ok": True, "path": "/ok"}
    await transport.close()
