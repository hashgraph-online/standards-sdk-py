"""Tests for standards_sdk_py.shared.hcs_module and HCS module client classes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from standards_sdk_py.shared.hcs_module import (
    AsyncHcsModuleClient,
    HcsModuleClient,
    _build_body,
    _build_query,
    _camel_to_snake,
    _infer_method,
    _make_async_operation,
    _make_sync_operation,
    _to_json_value,
    register_hcs_methods,
)
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport

_TEST_OPERATOR_ID = "0.0.1001"
_TEST_OPERATOR_KEY = (
    "302e020100300506032b657004220420fb77695921a5c79474d57c42006f03ff"
    "178688514d797fb30f60fd0fc9e82716"
)

# ── _camel_to_snake ──────────────────────────────────────────────────


def test_camel_to_snake() -> None:
    assert _camel_to_snake("sendMessage") == "send_message"
    assert _camel_to_snake("HTMLParser") == "h_t_m_l_parser"
    assert _camel_to_snake("simple") == "simple"
    assert _camel_to_snake("getX") == "get_x"


# ── _to_json_value ──────────────────────────────────────────────────


def test_to_json_value_primitives() -> None:
    assert _to_json_value(None) is None
    assert _to_json_value(True) is True
    assert _to_json_value(42) == 42
    assert _to_json_value(3.14) == 3.14
    assert _to_json_value("hello") == "hello"


def test_to_json_value_bytes() -> None:
    assert _to_json_value(b"\xde\xad") == "dead"
    assert _to_json_value(bytearray(b"\xbe\xef")) == "beef"


def test_to_json_value_dict() -> None:
    result = _to_json_value({"key": 1, "nested": {"a": 2}})
    assert result == {"key": 1, "nested": {"a": 2}}


def test_to_json_value_list_tuple_set() -> None:
    assert _to_json_value([1, "a"]) == [1, "a"]
    assert _to_json_value((1, 2)) == [1, 2]
    # sets are unordered; just check it's a list
    result = _to_json_value({42})
    assert isinstance(result, list)
    assert 42 in result


def test_to_json_value_fallback() -> None:
    class Custom:
        def __str__(self) -> str:
            return "custom_str"

    assert _to_json_value(Custom()) == "custom_str"


# ── _infer_method ────────────────────────────────────────────────────


def test_infer_method_get_prefixes() -> None:
    for prefix in ("get", "list", "fetch", "resolve", "validate", "check", "search", "is", "has"):
        assert _infer_method(f"{prefix}Something") == "GET", f"failed for {prefix}"


def test_infer_method_post() -> None:
    assert _infer_method("createRegistry") == "POST"
    assert _infer_method("submitMessage") == "POST"


# ── _build_query ─────────────────────────────────────────────────────


def test_build_query_empty() -> None:
    assert _build_query((), {}) is None


def test_build_query_dict_args() -> None:
    result = _build_query(({"q": "hello", "limit": 10},), {})
    assert result == {"q": "hello", "limit": 10}


def test_build_query_positional_args() -> None:
    result = _build_query(("hello", 42), {})
    assert result == {"arg0": "hello", "arg1": 42}


def test_build_query_kwargs() -> None:
    result = _build_query((), {"q": "test", "limit": 5})
    assert result == {"q": "test", "limit": 5}


def test_build_query_args_and_kwargs() -> None:
    result = _build_query(("val",), {"extra": "data"})
    assert result is not None
    assert result["arg0"] == "val"
    assert result["extra"] == "data"


# ── _build_body ──────────────────────────────────────────────────────


def test_build_body_empty() -> None:
    assert _build_body((), {}) is None


def test_build_body_single_dict() -> None:
    result = _build_body(({"key": "val"},), {})
    assert result == {"key": "val"}


def test_build_body_positional_args() -> None:
    result = _build_body(("a", "b"), {})
    assert result == {"args": ["a", "b"]}


def test_build_body_kwargs_only() -> None:
    result = _build_body((), {"key": "val"})
    assert result == {"key": "val"}


def test_build_body_args_and_kwargs() -> None:
    result = _build_body(("a",), {"b": "c"})
    assert result is not None
    assert result["args"] == ["a"]
    assert result["b"] == "c"


def test_build_body_dict_with_kwargs() -> None:
    """When kwargs present, single dict arg isn't treated as direct body."""
    result = _build_body(({"a": 1},), {"b": 2})
    assert result is not None
    assert "args" in result


# ── HcsModuleClient ─────────────────────────────────────────────────


def test_sync_client_call() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.request_json.return_value = {"ok": True}
    client = HcsModuleClient("hcs2", transport)
    result = client.call("/getRegistry", method="GET", query={"id": "1"})
    assert result == {"ok": True}
    transport.request_json.assert_called_once_with(
        "GET", "/hcs2/getRegistry", query={"id": "1"}, body=None
    )


def test_sync_client_invoke_operation_get() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.request_json.return_value = {"data": "x"}
    client = HcsModuleClient("hcs2", transport)
    result = client.invoke_operation("getRegistry", id="1")
    assert result == {"data": "x"}


def test_sync_client_invoke_operation_post() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.request_json.return_value = {"created": True}
    client = HcsModuleClient("hcs2", transport)
    result = client.invoke_operation("createRegistry", {"name": "test"})
    assert result == {"created": True}


# ── AsyncHcsModuleClient ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_client_call() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.request_json = AsyncMock(return_value={"ok": True})
    client = AsyncHcsModuleClient("hcs3", transport)
    result = await client.call("/loadImage", method="GET", query={"url": "https://x"})
    assert result == {"ok": True}
    transport.request_json.assert_called_once_with(
        "GET", "/hcs3/loadImage", query={"url": "https://x"}, body=None
    )


@pytest.mark.asyncio
async def test_async_client_invoke_operation_get() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.request_json = AsyncMock(return_value={"data": "x"})
    client = AsyncHcsModuleClient("hcs3", transport)
    result = await client.invoke_operation("fetchWithRetry", url="https://test")
    assert result == {"data": "x"}


@pytest.mark.asyncio
async def test_async_client_invoke_operation_post() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.request_json = AsyncMock(return_value={"created": True})
    client = AsyncHcsModuleClient("hcs3", transport)
    result = await client.invoke_operation("submitMessage", {"data": "test"})
    assert result == {"created": True}


# ── _make_sync_operation / _make_async_operation ─────────────────────


def test_make_sync_operation() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.request_json.return_value = {"value": 1}
    client = HcsModuleClient("hcs2", transport)
    op = _make_sync_operation("getRegistry")
    assert op.__name__ == "getRegistry"
    result = op(client, id="1")
    assert result == {"value": 1}


@pytest.mark.asyncio
async def test_make_async_operation() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.request_json = AsyncMock(return_value={"value": 1})
    client = AsyncHcsModuleClient("hcs2", transport)
    op = _make_async_operation("getRegistry")
    assert op.__name__ == "getRegistry"
    result = await op(client, id="1")
    assert result == {"value": 1}


# ── register_hcs_methods ────────────────────────────────────────────


def test_register_hcs_methods() -> None:
    """register_hcs_methods adds camelCase and snake_case methods."""

    class TestSync(HcsModuleClient):
        pass

    class TestAsync(AsyncHcsModuleClient):
        pass

    register_hcs_methods(TestSync, TestAsync, ("createRegistry", "getTopicInfo"))

    # camelCase methods
    assert hasattr(TestSync, "createRegistry")
    assert hasattr(TestSync, "getTopicInfo")
    assert hasattr(TestAsync, "createRegistry")
    assert hasattr(TestAsync, "getTopicInfo")

    # snake_case aliases
    assert hasattr(TestSync, "create_registry")
    assert hasattr(TestSync, "get_topic_info")
    assert hasattr(TestAsync, "create_registry")
    assert hasattr(TestAsync, "get_topic_info")


def test_register_hcs_methods_no_duplicate() -> None:
    """register_hcs_methods does not overwrite existing methods."""

    class TestSync(HcsModuleClient):
        def already(self) -> str:
            return "sync"

    class TestAsync(AsyncHcsModuleClient):
        async def already(self) -> str:
            return "async"

    register_hcs_methods(TestSync, TestAsync, ("already",))

    # Existing methods should be preserved
    transport = MagicMock(spec=SyncHttpTransport)
    client = TestSync("test", transport)
    assert client.already() == "sync"


# ── Actual HCS module client classes ─────────────────────────────────


def test_hcs2_client() -> None:
    from standards_sdk_py.hcs2 import Hcs2Client

    transport = MagicMock(spec=SyncHttpTransport)
    transport.request_json.return_value = {"registry": {}}
    client = Hcs2Client(
        transport,
        operator_id=_TEST_OPERATOR_ID,
        operator_key=_TEST_OPERATOR_KEY,
    )
    assert hasattr(client, "createRegistry")
    assert hasattr(client, "create_registry")
    assert isinstance(client.getKeyType(), str)


def test_hcs10_client() -> None:
    from standards_sdk_py.hcs10 import Hcs10Client

    transport = MagicMock(spec=SyncHttpTransport)
    transport.request_json.return_value = {"agent": {}}
    client = Hcs10Client(transport)
    assert hasattr(client, "createAgent")
    assert hasattr(client, "create_agent")


@pytest.mark.asyncio
async def test_async_hcs2_client() -> None:
    from standards_sdk_py.hcs2 import AsyncHcs2Client

    transport = MagicMock(spec=AsyncHttpTransport)
    transport.request_json = AsyncMock(return_value={"registry": {}})
    client = AsyncHcs2Client(
        transport,
        operator_id=_TEST_OPERATOR_ID,
        operator_key=_TEST_OPERATOR_KEY,
    )
    result = await client.getKeyType()
    assert isinstance(result, str)
