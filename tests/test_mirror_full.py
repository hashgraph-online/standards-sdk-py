"""Comprehensive tests for mirror client covering all uncovered paths."""

import httpx
import pytest

from standards_sdk_py.exceptions import ParseError
from standards_sdk_py.mirror import AsyncMirrorNodeClient, MirrorNodeClient
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/topics/0.0.100/messages":
        return httpx.Response(
            200,
            json={
                "messages": [
                    {
                        "consensus_timestamp": "1.1",
                        "message": "aGVsbG8=",
                        "running_hash": "hash",
                        "sequence_number": 1,
                    },
                ],
                "links": {"next": None},
            },
        )
    if path == "/topics/0.0.200/messages":
        return httpx.Response(200, json={"not": "valid"})
    return httpx.Response(404, json={"error": "not-found"})


# ── Sync tests ────────────────────────────────────────────────────────


def test_sync_mirror_basic() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = MirrorNodeClient(transport=transport)
    response = client.get_topic_messages("0.0.100", limit=1)
    assert response.messages[0].sequence_number == 1


def test_sync_mirror_with_order() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = MirrorNodeClient(transport=transport)
    response = client.get_topic_messages("0.0.100", order="asc")
    assert len(response.messages) == 1


def test_sync_mirror_with_sequence_number() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = MirrorNodeClient(transport=transport)
    response = client.get_topic_messages("0.0.100", sequence_number=0)
    assert len(response.messages) == 1


def test_sync_mirror_all_query_params() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = MirrorNodeClient(transport=transport)
    response = client.get_topic_messages("0.0.100", limit=5, order="desc", sequence_number=10)
    assert len(response.messages) == 1


def test_sync_mirror_no_query_params() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = MirrorNodeClient(transport=transport)
    response = client.get_topic_messages("0.0.100")
    assert len(response.messages) == 1


def test_sync_mirror_parse_error() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = MirrorNodeClient(transport=transport)
    with pytest.raises(ParseError, match="Failed to validate"):
        client.get_topic_messages("0.0.200")


def test_sync_mirror_close() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = MirrorNodeClient(transport=transport)
    client.close()


def test_sync_mirror_default_config() -> None:
    """MirrorNodeClient creates transport from SdkConfig if none provided."""
    client = MirrorNodeClient()
    assert client._transport is not None
    assert client._config is not None


# ── Async tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_mirror_basic() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)),
    )
    client = AsyncMirrorNodeClient(transport=transport)
    response = await client.get_topic_messages("0.0.100", limit=1)
    assert response.messages[0].sequence_number == 1
    await client.close()


@pytest.mark.asyncio
async def test_async_mirror_with_order() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)),
    )
    client = AsyncMirrorNodeClient(transport=transport)
    response = await client.get_topic_messages("0.0.100", order="asc")
    assert len(response.messages) == 1


@pytest.mark.asyncio
async def test_async_mirror_with_sequence_number() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)),
    )
    client = AsyncMirrorNodeClient(transport=transport)
    response = await client.get_topic_messages("0.0.100", sequence_number=0)
    assert len(response.messages) == 1


@pytest.mark.asyncio
async def test_async_mirror_all_query_params() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)),
    )
    client = AsyncMirrorNodeClient(transport=transport)
    response = await client.get_topic_messages("0.0.100", limit=5, order="desc", sequence_number=10)
    assert len(response.messages) == 1


@pytest.mark.asyncio
async def test_async_mirror_no_query_params() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)),
    )
    client = AsyncMirrorNodeClient(transport=transport)
    response = await client.get_topic_messages("0.0.100")
    assert len(response.messages) == 1


@pytest.mark.asyncio
async def test_async_mirror_parse_error() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)),
    )
    client = AsyncMirrorNodeClient(transport=transport)
    with pytest.raises(ParseError, match="Failed to validate"):
        await client.get_topic_messages("0.0.200")


@pytest.mark.asyncio
async def test_async_mirror_close() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)),
    )
    client = AsyncMirrorNodeClient(transport=transport)
    await client.close()


@pytest.mark.asyncio
async def test_async_mirror_default_config() -> None:
    """AsyncMirrorNodeClient creates transport from SdkConfig if none provided."""
    client = AsyncMirrorNodeClient()
    assert client._transport is not None
    assert client._config is not None
