import httpx
import pytest

from standards_sdk_py.mirror import AsyncMirrorNodeClient, MirrorNodeClient
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/topics/0.0.100/messages":
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
    return httpx.Response(404, json={"error": "not-found"})


def test_mirror_sync() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = MirrorNodeClient(transport=transport)
    response = client.get_topic_messages("0.0.100", limit=1)
    assert response.messages[0].sequence_number == 1


@pytest.mark.asyncio
async def test_mirror_async() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)),
    )
    client = AsyncMirrorNodeClient(transport=transport)
    response = await client.get_topic_messages("0.0.100", limit=1)
    assert response.messages[0].sequence_number == 1
    await client.close()
