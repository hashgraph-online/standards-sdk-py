"""Tests for all HCS module client scaffolds (hcs2 through hcs27)."""

import httpx
import pytest

from standards_sdk_py.hcs2 import AsyncHcs2Client, Hcs2Client
from standards_sdk_py.hcs3 import AsyncHcs3Client, Hcs3Client
from standards_sdk_py.hcs5 import AsyncHcs5Client, Hcs5Client
from standards_sdk_py.hcs6 import AsyncHcs6Client, Hcs6Client
from standards_sdk_py.hcs7 import AsyncHcs7Client, Hcs7Client
from standards_sdk_py.hcs10 import AsyncHcs10Client, Hcs10Client
from standards_sdk_py.hcs11 import AsyncHcs11Client, Hcs11Client
from standards_sdk_py.hcs12 import AsyncHcs12Client, Hcs12Client
from standards_sdk_py.hcs14 import AsyncHcs14Client, Hcs14Client
from standards_sdk_py.hcs15 import AsyncHcs15Client, Hcs15Client
from standards_sdk_py.hcs16 import AsyncHcs16Client, Hcs16Client
from standards_sdk_py.hcs17 import AsyncHcs17Client, Hcs17Client
from standards_sdk_py.hcs18 import AsyncHcs18Client, Hcs18Client
from standards_sdk_py.hcs20 import AsyncHcs20Client, Hcs20Client
from standards_sdk_py.hcs21 import AsyncHcs21Client, Hcs21Client
from standards_sdk_py.hcs26 import AsyncHcs26Client, Hcs26Client
from standards_sdk_py.hcs27 import AsyncHcs27Client, Hcs27Client
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport

_STRICT_HCS_CLIENTS = {
    "hcs2",
    "hcs5",
    "hcs6",
    "hcs7",
    "hcs15",
    "hcs16",
    "hcs17",
    "hcs18",
    "hcs20",
    "hcs21",
}
_TEST_OPERATOR_ID = "0.0.1001"
_TEST_OPERATOR_KEY = (
    "302e020100300506032b657004220420fb77695921a5c79474d57c42006f03ff"
    "178688514d797fb30f60fd0fc9e82716"
)


def _handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"status": "ok", "path": request.url.path})


def _sync_transport() -> SyncHttpTransport:
    return SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )


def _async_transport() -> AsyncHttpTransport:
    return AsyncHttpTransport(
        "https://example.test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)),
    )


def _client_kwargs(
    standard: str, transport: SyncHttpTransport | AsyncHttpTransport
) -> dict[str, object]:
    kwargs: dict[str, object] = {"transport": transport}
    if standard in _STRICT_HCS_CLIENTS:
        kwargs["operator_id"] = _TEST_OPERATOR_ID
        kwargs["operator_key"] = _TEST_OPERATOR_KEY
    return kwargs


# Parametrize all sync HCS module clients
_SYNC_CLIENTS = [
    ("hcs2", Hcs2Client),
    ("hcs3", Hcs3Client),
    ("hcs5", Hcs5Client),
    ("hcs6", Hcs6Client),
    ("hcs7", Hcs7Client),
    ("hcs10", Hcs10Client),
    ("hcs11", Hcs11Client),
    ("hcs12", Hcs12Client),
    ("hcs14", Hcs14Client),
    ("hcs15", Hcs15Client),
    ("hcs16", Hcs16Client),
    ("hcs17", Hcs17Client),
    ("hcs18", Hcs18Client),
    ("hcs20", Hcs20Client),
    ("hcs21", Hcs21Client),
    ("hcs26", Hcs26Client),
    ("hcs27", Hcs27Client),
]

_ASYNC_CLIENTS = [
    ("hcs2", AsyncHcs2Client),
    ("hcs3", AsyncHcs3Client),
    ("hcs5", AsyncHcs5Client),
    ("hcs6", AsyncHcs6Client),
    ("hcs7", AsyncHcs7Client),
    ("hcs10", AsyncHcs10Client),
    ("hcs11", AsyncHcs11Client),
    ("hcs12", AsyncHcs12Client),
    ("hcs14", AsyncHcs14Client),
    ("hcs15", AsyncHcs15Client),
    ("hcs16", AsyncHcs16Client),
    ("hcs17", AsyncHcs17Client),
    ("hcs18", AsyncHcs18Client),
    ("hcs20", AsyncHcs20Client),
    ("hcs21", AsyncHcs21Client),
    ("hcs26", AsyncHcs26Client),
    ("hcs27", AsyncHcs27Client),
]


@pytest.mark.parametrize("standard,cls", _SYNC_CLIENTS, ids=[s for s, _ in _SYNC_CLIENTS])
def test_sync_hcs_client_call(standard: str, cls: type) -> None:
    transport = _sync_transport()
    client = cls(**_client_kwargs(standard, transport))
    assert client.standard == standard
    result = client.call("/test")
    assert isinstance(result, dict)
    assert result["path"] == f"/{standard}/test"


@pytest.mark.asyncio
@pytest.mark.parametrize("standard,cls", _ASYNC_CLIENTS, ids=[s for s, _ in _ASYNC_CLIENTS])
async def test_async_hcs_client_call(standard: str, cls: type) -> None:
    transport = _async_transport()
    client = cls(**_client_kwargs(standard, transport))
    assert client.standard == standard
    result = await client.call("/test")
    assert isinstance(result, dict)
    assert result["path"] == f"/{standard}/test"


def test_hcs_module_call_with_body() -> None:
    transport = _sync_transport()
    client = Hcs2Client(
        transport=transport,
        operator_id=_TEST_OPERATOR_ID,
        operator_key=_TEST_OPERATOR_KEY,
    )
    result = client.call("/data", method="POST", body={"key": "val"})
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_async_hcs_module_call_with_body() -> None:
    transport = _async_transport()
    client = AsyncHcs2Client(
        transport=transport,
        operator_id=_TEST_OPERATOR_ID,
        operator_key=_TEST_OPERATOR_KEY,
    )
    result = await client.call("/data", method="POST", body={"key": "val"})
    assert isinstance(result, dict)
