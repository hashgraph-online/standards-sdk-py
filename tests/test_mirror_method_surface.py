"""Mirror method-surface parity and behavior checks."""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
import pytest

from standards_sdk_py.mirror import AsyncMirrorNodeClient, HederaMirrorNode
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport

_FIRST_CAP_RE = re.compile("(.)([A-Z][a-z]+)")
_ALL_CAP_RE = re.compile("([a-z0-9])([A-Z])")


def _camel_to_snake(name: str) -> str:
    first_pass = _FIRST_CAP_RE.sub(r"\1_\2", name)
    return _ALL_CAP_RE.sub(r"\1_\2", first_pass).lower()


def _load_ts_mirror_methods() -> list[str]:
    inventory_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "standards_sdk_py"
        / "parity"
        / "generated"
        / "ts-core-client-methods.json"
    )
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    classes = payload.get("classes", {})
    methods = classes.get("HederaMirrorNode", [])
    return [method for method in methods if isinstance(method, str)]


def test_mirror_method_surface_presence() -> None:
    for method in _load_ts_mirror_methods():
        snake = _camel_to_snake(method)
        assert hasattr(HederaMirrorNode, method) or hasattr(HederaMirrorNode, snake)
        assert hasattr(AsyncMirrorNodeClient, method) or hasattr(AsyncMirrorNodeClient, snake)


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/accounts/0.0.10":
        return httpx.Response(200, json={"key": {"key": "pub-key"}, "balance": {"balance": 123}})
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
    if path == "/tokens/0.0.55":
        return httpx.Response(200, json={"token_id": "0.0.55"})
    return httpx.Response(200, json={})


def test_mirror_sync_parity_methods_work() -> None:
    client = HederaMirrorNode(
        transport=SyncHttpTransport(
            "https://example.test",
            client=httpx.Client(transport=httpx.MockTransport(_handler)),
        )
    )
    assert client.requestAccount("0.0.10")["balance"]["balance"] == 123
    assert client.getPublicKey("0.0.10") == "pub-key"
    assert client.getAccountBalance("0.0.10") == 123.0
    assert client.getTokenInfo("0.0.55")["token_id"] == "0.0.55"
    decoded = client.getTopicMessagesByFilter("0.0.100")
    assert isinstance(decoded, list)
    assert decoded[0]["message"] == "hello"


@pytest.mark.asyncio
async def test_mirror_async_parity_methods_work() -> None:
    client = AsyncMirrorNodeClient(
        transport=AsyncHttpTransport(
            "https://example.test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)),
        )
    )
    response = await client.getTopicMessages("0.0.100")
    assert response.messages[0].sequence_number == 1
