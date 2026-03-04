"""Comprehensive tests for HTTP transports and JSON parsing helpers."""

import httpx
import pytest
from pydantic import BaseModel

from standards_sdk_py.exceptions import (
    ApiError,
    AuthError,
    ParseError,
    TransportError,
)
from standards_sdk_py.shared.http import (
    AsyncHttpTransport,
    SyncHttpTransport,
    _context_from_response,
    _encode_query,
    _merge_headers,
    _normalize_path,
    parse_as_model,
    parse_json_body,
)

# ── Helper functions ──────────────────────────────────────────────────


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/ok":
        return httpx.Response(200, json={"ok": True, "path": request.url.path})
    if request.url.path == "/unauthorized":
        return httpx.Response(401, json={"error": "unauthorized"})
    if request.url.path == "/forbidden":
        return httpx.Response(403, json={"error": "forbidden"})
    if request.url.path == "/failure":
        return httpx.Response(500, json={"error": "boom"})
    if request.url.path == "/bad-json":
        return httpx.Response(200, content=b"not json", headers={"content-type": "text/plain"})
    if request.url.path == "/null-json":
        return httpx.Response(200, json=None)
    if request.url.path == "/list-json":
        return httpx.Response(200, json=[1, 2, 3])
    if request.url.path == "/bool-json":
        return httpx.Response(200, json=True)
    if request.url.path == "/int-json":
        return httpx.Response(200, json=42)
    if request.url.path == "/string-json":
        return httpx.Response(200, json="hello")
    if request.url.path == "/with-query" and "q=hello" in str(request.url):
        return httpx.Response(200, json={"found": True})
    return httpx.Response(404, json={"error": "not-found"})


def _raise_handler(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused")


# ── _normalize_path tests ─────────────────────────────────────────────


def test_normalize_path_already_rooted() -> None:
    assert _normalize_path("/foo") == "/foo"


def test_normalize_path_no_leading_slash() -> None:
    assert _normalize_path("foo") == "/foo"


def test_normalize_path_full_url() -> None:
    assert _normalize_path("https://example.com/bar") == "https://example.com/bar"
    assert _normalize_path("http://example.com/bar") == "http://example.com/bar"


# ── _merge_headers tests ──────────────────────────────────────────────


def test_merge_headers_both_none() -> None:
    assert _merge_headers(None, None) == {}


def test_merge_headers_base_only() -> None:
    assert _merge_headers({"X-Base": "a"}, None) == {"x-base": "a"}


def test_merge_headers_extra_only() -> None:
    assert _merge_headers(None, {"X-Extra": "b"}) == {"x-extra": "b"}


def test_merge_headers_extra_overrides() -> None:
    merged = _merge_headers({"X-Key": "old"}, {"X-Key": "new"})
    assert merged["x-key"] == "new"


# ── _encode_query tests ──────────────────────────────────────────────


def test_encode_query_none() -> None:
    assert _encode_query(None) == ""


def test_encode_query_empty() -> None:
    assert _encode_query({}) == ""


def test_encode_query_with_none_values() -> None:
    assert _encode_query({"a": None}) == ""


def test_encode_query_with_values() -> None:
    result = _encode_query({"q": "hello", "page": 1})
    assert "q=hello" in result
    assert "page=1" in result
    assert result.startswith("?")


# ── _context_from_response tests ──────────────────────────────────────


def test_context_from_response() -> None:
    req = httpx.Request("GET", "https://api.test/data")
    resp = httpx.Response(200, request=req)
    ctx = _context_from_response(resp, body={"ok": True}, details={"extra": "info"})
    assert ctx.status_code == 200
    assert ctx.method == "GET"
    assert ctx.url == "https://api.test/data"
    assert ctx.body == {"ok": True}
    assert ctx.details == {"extra": "info"}


# ── parse_json_body tests ─────────────────────────────────────────────


def test_parse_json_body_dict() -> None:
    req = httpx.Request("GET", "https://api.test")
    resp = httpx.Response(200, json={"key": "val"}, request=req)
    result = parse_json_body(resp)
    assert result == {"key": "val"}


def test_parse_json_body_list() -> None:
    req = httpx.Request("GET", "https://api.test")
    resp = httpx.Response(200, json=[1, 2], request=req)
    assert parse_json_body(resp) == [1, 2]


def test_parse_json_body_null() -> None:
    req = httpx.Request("GET", "https://api.test")
    resp = httpx.Response(200, json=None, request=req)
    assert parse_json_body(resp) is None


def test_parse_json_body_bool() -> None:
    req = httpx.Request("GET", "https://api.test")
    resp = httpx.Response(200, json=True, request=req)
    assert parse_json_body(resp) is True


def test_parse_json_body_int() -> None:
    req = httpx.Request("GET", "https://api.test")
    resp = httpx.Response(200, json=42, request=req)
    assert parse_json_body(resp) == 42


def test_parse_json_body_float() -> None:
    req = httpx.Request("GET", "https://api.test")
    resp = httpx.Response(200, json=3.14, request=req)
    assert parse_json_body(resp) == 3.14


def test_parse_json_body_string() -> None:
    req = httpx.Request("GET", "https://api.test")
    resp = httpx.Response(200, json="hello", request=req)
    assert parse_json_body(resp) == "hello"


def test_parse_json_body_invalid() -> None:
    req = httpx.Request("GET", "https://api.test")
    resp = httpx.Response(200, content=b"not-json", request=req)
    with pytest.raises(ParseError):
        parse_json_body(resp)


def test_parse_json_body_empty_content() -> None:
    """Empty response body returns None instead of raising."""
    req = httpx.Request("GET", "https://api.test")
    resp = httpx.Response(200, content=b"", request=req)
    result = parse_json_body(resp)
    assert result is None


def test_parse_json_body_whitespace_only() -> None:
    """Whitespace-only response body returns None."""
    req = httpx.Request("GET", "https://api.test")
    resp = httpx.Response(200, content=b"   ", request=req)
    result = parse_json_body(resp)
    assert result is None


def test_parse_json_body_unsupported_type() -> None:
    """Cover the unreachable 'Unsupported JSON value type' branch (line 83).

    In practice json.loads only returns dict/list/str/int/float/bool/None,
    but we mock response.json() to return a set to exercise the guard.
    """

    req = httpx.Request("GET", "https://api.test")
    resp = httpx.Response(200, content=b"[1,2,3]", request=req)
    # Monkey-patch .json() to return a set (impossible from real JSON parse)
    resp.json = lambda: {1, 2, 3}  # type: ignore[assignment]
    with pytest.raises(ParseError, match="Unsupported JSON value type"):
        parse_json_body(resp)


# ── parse_as_model tests ──────────────────────────────────────────────


class _SampleModel(BaseModel):
    name: str
    count: int


def test_parse_as_model_success() -> None:
    result = parse_as_model({"name": "x", "count": 1}, _SampleModel)
    assert isinstance(result, _SampleModel)
    assert result.name == "x"


def test_parse_as_model_invalid() -> None:
    with pytest.raises(ParseError):
        parse_as_model({"name": 123}, _SampleModel)


# ── Sync transport tests ──────────────────────────────────────────────


def test_sync_transport_success() -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    transport = SyncHttpTransport("https://example.test", client=client)
    payload = transport.request_json("GET", "/ok")
    assert payload == {"ok": True, "path": "/ok"}


def test_sync_transport_with_query() -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    transport = SyncHttpTransport("https://example.test", client=client)
    payload = transport.request_json("GET", "/with-query", query={"q": "hello"})
    assert payload == {"found": True}


def test_sync_transport_with_headers() -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    transport = SyncHttpTransport(
        "https://example.test",
        headers={"X-Base": "base"},
        client=client,
    )
    payload = transport.request_json("GET", "/ok", headers={"X-Extra": "extra"})
    assert payload == {"ok": True, "path": "/ok"}


def test_sync_transport_with_body() -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    transport = SyncHttpTransport("https://example.test", client=client)
    payload = transport.request_json("POST", "/ok", body={"data": "test"})
    assert payload == {"ok": True, "path": "/ok"}


def test_sync_transport_auth_error_401() -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    transport = SyncHttpTransport("https://example.test", client=client)
    with pytest.raises(AuthError):
        transport.request("GET", "/unauthorized")


def test_sync_transport_auth_error_403() -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    transport = SyncHttpTransport("https://example.test", client=client)
    with pytest.raises(AuthError):
        transport.request("GET", "/forbidden")


def test_sync_transport_api_error() -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    transport = SyncHttpTransport("https://example.test", client=client)
    with pytest.raises(ApiError):
        transport.request("GET", "/failure")


def test_sync_transport_network_error() -> None:
    client = httpx.Client(transport=httpx.MockTransport(_raise_handler))
    transport = SyncHttpTransport("https://example.test", client=client)
    with pytest.raises(TransportError):
        transport.request("GET", "/anything")


def test_sync_transport_close_owned() -> None:
    transport = SyncHttpTransport("https://example.test")
    transport.close()  # Should not raise


def test_sync_transport_close_not_owned() -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    transport = SyncHttpTransport("https://example.test", client=client)
    assert not transport._owns_client
    transport.close()


def test_sync_transport_request_raw_response() -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    transport = SyncHttpTransport("https://example.test", client=client)
    response = transport.request("GET", "/ok")
    assert response.status_code == 200


# ── Async transport tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_transport_success() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    transport = AsyncHttpTransport("https://example.test", client=client)
    payload = await transport.request_json("GET", "/ok")
    assert payload == {"ok": True, "path": "/ok"}
    await transport.close()


@pytest.mark.asyncio
async def test_async_transport_with_query() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    transport = AsyncHttpTransport("https://example.test", client=client)
    payload = await transport.request_json("GET", "/with-query", query={"q": "hello"})
    assert payload == {"found": True}


@pytest.mark.asyncio
async def test_async_transport_auth_error() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    transport = AsyncHttpTransport("https://example.test", client=client)
    with pytest.raises(AuthError):
        await transport.request("GET", "/unauthorized")


@pytest.mark.asyncio
async def test_async_transport_auth_error_403() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    transport = AsyncHttpTransport("https://example.test", client=client)
    with pytest.raises(AuthError):
        await transport.request("GET", "/forbidden")


@pytest.mark.asyncio
async def test_async_transport_api_error() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    transport = AsyncHttpTransport("https://example.test", client=client)
    with pytest.raises(ApiError):
        await transport.request("GET", "/failure")


@pytest.mark.asyncio
async def test_async_transport_network_error() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(_raise_handler))
    transport = AsyncHttpTransport("https://example.test", client=client)
    with pytest.raises(TransportError):
        await transport.request("GET", "/anything")


@pytest.mark.asyncio
async def test_async_transport_close_owned() -> None:
    transport = AsyncHttpTransport("https://example.test")
    await transport.close()  # Should not raise


@pytest.mark.asyncio
async def test_async_transport_close_not_owned() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    transport = AsyncHttpTransport("https://example.test", client=client)
    assert not transport._owns_client
    await transport.close()


@pytest.mark.asyncio
async def test_async_transport_request_raw_response() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    transport = AsyncHttpTransport("https://example.test", client=client)
    response = await transport.request("GET", "/ok")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_async_transport_with_headers_and_body() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    transport = AsyncHttpTransport(
        "https://example.test",
        headers={"X-Base": "base"},
        client=client,
    )
    payload = await transport.request_json(
        "POST",
        "/ok",
        headers={"X-Extra": "extra"},
        body={"key": "val"},
    )
    assert payload == {"ok": True, "path": "/ok"}
