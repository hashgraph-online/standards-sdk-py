"""Tests for the async mirror node client (mirror/async_client.py)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from standards_sdk_py.exceptions import ApiError, ErrorContext, ParseError, TransportError
from standards_sdk_py.mirror.async_client import (
    AsyncHederaMirrorNode,
    AsyncMirrorNodeClient,
)
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.http import AsyncHttpTransport

# ── Helper ───────────────────────────────────────────────────────────


def _make_async_mirror(mock_transport: MagicMock | None = None) -> AsyncMirrorNodeClient:
    transport = mock_transport or MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://mirror.test/api/v1"
    transport.headers = {}
    return AsyncMirrorNodeClient(config=SdkConfig.from_mapping({}), transport=transport)


# ── Init ─────────────────────────────────────────────────────────────


def test_async_mirror_init() -> None:
    client = _make_async_mirror()
    assert isinstance(client, AsyncMirrorNodeClient)
    assert AsyncHederaMirrorNode is AsyncMirrorNodeClient


# ── configure_retry ──────────────────────────────────────────────────


def test_async_configure_retry() -> None:
    client = _make_async_mirror()
    client.configure_retry(
        {
            "maxRetries": 10,
            "initialDelayMs": 500,
            "maxDelayMs": 60000,
            "backoffFactor": 1.5,
        }
    )
    assert client._max_retries == 10
    assert client._initial_delay_ms == 500
    assert client._max_delay_ms == 60000
    assert client._backoff_factor == 1.5


# ── configure_mirror_node ────────────────────────────────────────────


def test_async_configure_mirror_node_url() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://old.test"
    transport.headers = {}
    client = AsyncMirrorNodeClient(config=SdkConfig.from_mapping({}), transport=transport)
    client.configure_mirror_node({"customUrl": "https://new.test/"})
    assert transport.base_url == "https://new.test"


def test_async_configure_mirror_node_no_url() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://original.test"
    transport.headers = {}
    client = AsyncMirrorNodeClient(config=SdkConfig.from_mapping({}), transport=transport)
    client.configure_mirror_node({"headers": {"x-key": "val"}})
    assert transport.base_url == "https://original.test"


# ── get_base_url ─────────────────────────────────────────────────────


def test_async_get_base_url() -> None:
    client = _make_async_mirror()
    assert client.get_base_url() == "https://mirror.test/api/v1"


# ── _request_json ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_request_json_success() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://mirror.test/api/v1"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"data": True})
    client = _make_async_mirror(transport)
    result = await client._request_json("/test")
    assert result == {"data": True}


@pytest.mark.asyncio
async def test_async_request_json_retry_on_transport_error() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://mirror.test/api/v1"
    transport.headers = {}
    transport.request_json = AsyncMock(
        side_effect=[TransportError("timeout", ErrorContext()), {"data": True}]
    )
    client = _make_async_mirror(transport)
    with patch("standards_sdk_py.mirror.async_client.asyncio.sleep", new_callable=AsyncMock):
        result = await client._request_json("/test")
    assert result == {"data": True}


@pytest.mark.asyncio
async def test_async_request_json_retry_on_429() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://mirror.test/api/v1"
    transport.headers = {}
    transport.request_json = AsyncMock(
        side_effect=[ApiError("rate limit", ErrorContext(status_code=429)), {"data": True}]
    )
    client = _make_async_mirror(transport)
    with patch("standards_sdk_py.mirror.async_client.asyncio.sleep", new_callable=AsyncMock):
        result = await client._request_json("/test")
    assert result == {"data": True}


@pytest.mark.asyncio
async def test_async_request_json_no_retry_on_404() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://mirror.test/api/v1"
    transport.headers = {}
    transport.request_json = AsyncMock(
        side_effect=ApiError("not found", ErrorContext(status_code=404))
    )
    client = _make_async_mirror(transport)
    with pytest.raises(ApiError, match="not found"):
        await client._request_json("/test")
    assert transport.request_json.call_count == 1


@pytest.mark.asyncio
async def test_async_request_json_retries_exhausted() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://mirror.test/api/v1"
    transport.headers = {}
    transport.request_json = AsyncMock(side_effect=TransportError("timeout", ErrorContext()))
    client = _make_async_mirror(transport)
    client._max_retries = 2
    with patch("standards_sdk_py.mirror.async_client.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(TransportError, match="timeout"):
            await client._request_json("/test")


# ── get_topic_messages ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_get_topic_messages() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://mirror.test/api/v1"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"messages": []})
    client = _make_async_mirror(transport)
    result = await client.get_topic_messages("0.0.100", limit=10)
    assert result.messages == []


@pytest.mark.asyncio
async def test_async_get_topic_messages_validation_error() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://mirror.test/api/v1"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value="not-a-dict")
    client = _make_async_mirror(transport)
    with pytest.raises(ParseError, match="Failed to validate"):
        await client.get_topic_messages("0.0.100")


# ── close ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_close() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://mirror.test/api/v1"
    transport.headers = {}
    transport.close = AsyncMock()
    client = _make_async_mirror(transport)
    await client.close()
    transport.close.assert_called_once()


# ── Passthrough methods ──────────────────────────────────────────────


def test_install_async_passthroughs_creates_methods() -> None:
    """Verify that passthrough methods exist on AsyncMirrorNodeClient."""
    assert hasattr(AsyncMirrorNodeClient, "request_account")
    assert hasattr(AsyncMirrorNodeClient, "get_public_key")
    assert hasattr(AsyncMirrorNodeClient, "get_account_balance")
    assert hasattr(AsyncMirrorNodeClient, "get_hbar_price")


# ── CamelCase aliases ────────────────────────────────────────────────


def test_install_mirror_aliases() -> None:
    """Verify that camelCase aliases exist on AsyncMirrorNodeClient."""
    assert hasattr(AsyncMirrorNodeClient, "getAccountBalance")
    assert hasattr(AsyncMirrorNodeClient, "getTopicInfo")
    assert hasattr(AsyncMirrorNodeClient, "getPublicKey")
