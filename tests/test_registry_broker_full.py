"""Comprehensive tests for Registry Broker sync and async clients."""

import httpx
import pytest

from standards_sdk_py.exceptions import ParseError, ValidationError
from standards_sdk_py.registry_broker import AsyncRegistryBrokerClient, RegistryBrokerClient
from standards_sdk_py.registry_broker.async_client import _fill_path, _query_from_values
from standards_sdk_py.registry_broker.operations import REGISTRY_BROKER_OPERATIONS, operation_names
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport

# ── Helper functions tests ────────────────────────────────────────────


def test_fill_path_no_params() -> None:
    assert _fill_path("/search", None) == "/search"


def test_fill_path_with_params() -> None:
    assert _fill_path("/resolve/{uaid}", {"uaid": "test-1"}) == "/resolve/test-1"


def test_fill_path_missing_param_raises() -> None:
    with pytest.raises(ValidationError, match="Missing required path parameter"):
        _fill_path("/resolve/{uaid}", {"other": "val"})


def test_query_from_values_none() -> None:
    assert _query_from_values(None) is None


def test_query_from_values_empty() -> None:
    assert _query_from_values({}) is None


def test_query_from_values_skips_none() -> None:
    result = _query_from_values({"a": "hello", "b": None})
    assert result == {"a": "hello"}


def test_query_from_values_converts_types() -> None:
    result = _query_from_values({"a": True, "b": 42, "c": 3.14, "d": "str"})
    assert result is not None
    assert result["a"] is True
    assert result["b"] == 42
    assert result["c"] == 3.14
    assert result["d"] == "str"


def test_query_from_values_non_primitive_to_str() -> None:
    result = _query_from_values({"a": [1, 2, 3]})
    assert result is not None
    assert result["a"] == "[1, 2, 3]"


def test_query_from_values_all_none() -> None:
    assert _query_from_values({"a": None, "b": None}) is None


# ── operation_names tests ─────────────────────────────────────────────


def test_operation_names_sorted() -> None:
    names = operation_names()
    assert names == sorted(names)
    assert len(names) == len(REGISTRY_BROKER_OPERATIONS)
    assert "delegate" in names
    assert "search" in names
    assert "stats" in names


# ── Mock handler ──────────────────────────────────────────────────────


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/search":
        return httpx.Response(200, json={"hits": [], "total": 0, "page": 1, "limit": 20})
    if path == "/delegate":
        return httpx.Response(
            200,
            json={
                "task": "Review SDK PR feedback",
                "summary": "Delegate documentation follow-up.",
                "shouldDelegate": True,
                "localFirstReason": "Main agent owns the implementation work.",
                "recommendation": {"summary": "Delegate docs only", "mode": "parallel"},
                "opportunities": [
                    {
                        "id": "docs",
                        "title": "Docs follow-up",
                        "reason": "Bounded copy update",
                        "role": "docs",
                        "type": "sidecar",
                        "suggestedMode": "parallel",
                        "searchQueries": ["docs markdown docusaurus"],
                        "candidates": [
                            {
                                "uaid": "uaid-1",
                                "label": "Docs Agent",
                                "agent": {"name": "Docs Agent", "verified": True},
                                "score": 0.98,
                                "matchedRoles": ["docs"],
                                "reasons": ["Strong docs match"],
                                "suggestedMessage": "Update the docs tab set.",
                            }
                        ],
                    }
                ],
            },
        )
    if path == "/stats":
        return httpx.Response(200, json={"total_agents": 100, "active_agents": 42})
    if path == "/registries":
        return httpx.Response(200, json={"registries": [{"name": "default"}]})
    if path == "/protocols":
        return httpx.Response(200, json={"protocols": [{"name": "hcs10"}]})
    if path == "/chat/session":
        return httpx.Response(200, json={"sessionId": "s-1", "encryption": None})
    if path == "/chat/message":
        return httpx.Response(200, json={"sessionId": "s-1", "messageId": "m-1"})
    if path == "/skills/publish":
        return httpx.Response(200, json={"jobId": "job-1", "accepted": True})
    if path == "/verification/status/test-uaid":
        return httpx.Response(200, json={"verified": True, "method": "dns"})
    if path.startswith("/register/progress/"):
        return httpx.Response(
            200,
            json={"progress": {"status": "completed", "attemptId": "a-1", "uaid": "u-1"}},
        )
    if path.startswith("/skills/") and path.endswith("/SKILL.md"):
        return httpx.Response(
            200, text="# Skill Markdown\n\nHello.", headers={"content-type": "text/plain"}
        )
    return httpx.Response(200, json={"ok": True})


# ── Sync client tests ────────────────────────────────────────────────


def _make_sync_client() -> RegistryBrokerClient:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    return RegistryBrokerClient(transport=transport)


def test_sync_search() -> None:
    client = _make_sync_client()
    result = client.search(query="test")
    assert result.total == 0
    assert result.hits == []


def test_sync_delegate() -> None:
    client = _make_sync_client()
    result = client.delegate(task="Review SDK PR feedback")
    assert result.should_delegate is True
    assert result.opportunities[0].candidates[0].matched_roles == ["docs"]


def test_sync_search_no_query() -> None:
    client = _make_sync_client()
    result = client.search()
    assert result.total == 0


def test_sync_stats() -> None:
    client = _make_sync_client()
    result = client.stats()
    assert result.total_agents == 100
    assert result.active_agents == 42


def test_sync_registries() -> None:
    client = _make_sync_client()
    result = client.registries()
    assert len(result.registries) == 1


def test_sync_list_protocols() -> None:
    client = _make_sync_client()
    result = client.list_protocols()
    assert result.protocols[0]["name"] == "hcs10"


def test_sync_create_session() -> None:
    client = _make_sync_client()
    result = client.create_session({"uaid": "u-1"})
    assert result.session_id == "s-1"


def test_sync_send_message() -> None:
    client = _make_sync_client()
    result = client.send_message({"content": "hello"})
    assert result.session_id == "s-1"
    assert result.message_id == "m-1"


def test_sync_publish_skill() -> None:
    client = _make_sync_client()
    result = client.publish_skill({"name": "s"})
    assert result.job_id == "job-1"


def test_sync_get_verification_status() -> None:
    client = _make_sync_client()
    result = client.get_verification_status("test-uaid")
    assert result.verified is True


def test_sync_get_registration_progress() -> None:
    client = _make_sync_client()
    result = client.get_registration_progress("attempt-1")
    assert result.status == "completed"


def test_sync_unknown_operation_raises() -> None:
    client = _make_sync_client()
    with pytest.raises(ValidationError, match="Unknown Registry Broker operation"):
        client.call_operation("nonexistent_op")


def test_sync_dynamic_getattr() -> None:
    client = _make_sync_client()
    result = client.adapter_registry_categories()
    assert isinstance(result, dict)


def test_sync_dynamic_getattr_unknown_raises() -> None:
    client = _make_sync_client()
    with pytest.raises(AttributeError):
        client.totally_fake_method()


def test_sync_close() -> None:
    client = _make_sync_client()
    client.close()


def test_sync_parse_model_text_raises() -> None:
    from standards_sdk_py.registry_broker.sync_client import RegistryBrokerClient

    with pytest.raises(ParseError, match="Expected JSON response but got text"):
        RegistryBrokerClient._parse_model(
            "plain text", type("M", (object,), {"model_validate": lambda x: x})
        )


def test_sync_text_response_operation() -> None:
    """Test operations with text_response=True (e.g. resolve_skill_markdown)."""
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = RegistryBrokerClient(transport=transport)
    result = client.call_operation(
        "resolve_skill_markdown",
        path_params={"skill_ref": "my-skill"},
    )
    assert isinstance(result, str)
    assert "Skill Markdown" in result


def test_sync_wait_for_registration_completion() -> None:
    client = _make_sync_client()
    result = client.wait_for_registration_completion(
        "attempt-1", timeout_seconds=5, interval_seconds=0
    )
    assert result.status == "completed"


def _pending_reg_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.startswith("/register/progress/"):
        return httpx.Response(200, json={"status": "in_progress"})
    return httpx.Response(200, json={"ok": True})


def test_sync_wait_for_registration_timeout() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_pending_reg_handler)),
    )
    client = RegistryBrokerClient(transport=transport)
    with pytest.raises(ValidationError, match="Timed out"):
        client.wait_for_registration_completion("a-1", timeout_seconds=0.05, interval_seconds=0.01)


def test_sync_search_with_extra_params() -> None:
    client = _make_sync_client()
    result = client.search(query="test", limit=10, offset=5)
    assert result.total == 0


def test_sync_registration_progress_without_nested_progress() -> None:
    def _handler_no_nested(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/register/progress/"):
            return httpx.Response(200, json={"status": "completed", "attemptId": "a-1"})
        return httpx.Response(200, json={"ok": True})

    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler_no_nested)),
    )
    client = RegistryBrokerClient(transport=transport)
    result = client.get_registration_progress("a-1")
    assert result.status == "completed"


# ── Async client tests ───────────────────────────────────────────────


def _make_async_client() -> AsyncRegistryBrokerClient:
    transport = AsyncHttpTransport(
        "https://example.test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)),
    )
    return AsyncRegistryBrokerClient(transport=transport)


@pytest.mark.asyncio
async def test_async_search() -> None:
    client = _make_async_client()
    result = await client.search(query="test")
    assert result.total == 0


@pytest.mark.asyncio
async def test_async_delegate() -> None:
    client = _make_async_client()
    result = await client.delegate(task="Review SDK PR feedback")
    assert result.should_delegate is True
    assert result.opportunities[0].candidates[0].matched_roles == ["docs"]


@pytest.mark.asyncio
async def test_async_search_no_query() -> None:
    client = _make_async_client()
    result = await client.search()
    assert result.total == 0


@pytest.mark.asyncio
async def test_async_stats() -> None:
    client = _make_async_client()
    result = await client.stats()
    assert result.total_agents == 100


@pytest.mark.asyncio
async def test_async_registries() -> None:
    client = _make_async_client()
    result = await client.registries()
    assert len(result.registries) == 1


@pytest.mark.asyncio
async def test_async_list_protocols() -> None:
    client = _make_async_client()
    result = await client.list_protocols()
    assert result.protocols[0]["name"] == "hcs10"


@pytest.mark.asyncio
async def test_async_create_session() -> None:
    client = _make_async_client()
    result = await client.create_session({"uaid": "u-1"})
    assert result.session_id == "s-1"


@pytest.mark.asyncio
async def test_async_send_message() -> None:
    client = _make_async_client()
    result = await client.send_message({"content": "hello"})
    assert result.message_id == "m-1"


@pytest.mark.asyncio
async def test_async_publish_skill() -> None:
    client = _make_async_client()
    result = await client.publish_skill({"name": "s"})
    assert result.job_id == "job-1"


@pytest.mark.asyncio
async def test_async_get_verification_status() -> None:
    client = _make_async_client()
    result = await client.get_verification_status("test-uaid")
    assert result.verified is True


@pytest.mark.asyncio
async def test_async_get_registration_progress() -> None:
    client = _make_async_client()
    result = await client.get_registration_progress("attempt-1")
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_async_unknown_operation_raises() -> None:
    client = _make_async_client()
    with pytest.raises(ValidationError, match="Unknown Registry Broker operation"):
        await client.call_operation("nonexistent_op")


@pytest.mark.asyncio
async def test_async_dynamic_getattr() -> None:
    client = _make_async_client()
    result = await client.adapter_registry_categories()
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_async_dynamic_getattr_unknown_raises() -> None:
    client = _make_async_client()
    with pytest.raises(AttributeError):
        await client.totally_fake_method()


@pytest.mark.asyncio
async def test_async_close() -> None:
    client = _make_async_client()
    await client.close()


@pytest.mark.asyncio
async def test_async_text_response_operation() -> None:
    client = _make_async_client()
    result = await client.call_operation(
        "resolve_skill_markdown",
        path_params={"skill_ref": "my-skill"},
    )
    assert isinstance(result, str)
    assert "Skill Markdown" in result


@pytest.mark.asyncio
async def test_async_wait_for_registration_completion() -> None:
    client = _make_async_client()
    result = await client.wait_for_registration_completion(
        "attempt-1", timeout_seconds=5, interval_seconds=0
    )
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_async_wait_for_registration_timeout() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_pending_reg_handler)),
    )
    client = AsyncRegistryBrokerClient(transport=transport)
    with pytest.raises(ValidationError, match="Timed out"):
        await client.wait_for_registration_completion(
            "a-1", timeout_seconds=0.05, interval_seconds=0.01
        )


@pytest.mark.asyncio
async def test_async_parse_model_text_raises() -> None:
    with pytest.raises(ParseError, match="Expected JSON response but got text"):
        AsyncRegistryBrokerClient._parse_model(
            "plain text", type("M", (object,), {"model_validate": lambda x: x})
        )


@pytest.mark.asyncio
async def test_async_registration_progress_without_nested() -> None:
    async def _handler_no_nested(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/register/progress/"):
            return httpx.Response(200, json={"status": "completed", "attemptId": "a-1"})
        return httpx.Response(200, json={"ok": True})

    # Use sync handler wrapped for async mock transport
    def _sync_handler_no_nested(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/register/progress/"):
            return httpx.Response(200, json={"status": "completed", "attemptId": "a-1"})
        return httpx.Response(200, json={"ok": True})

    transport = AsyncHttpTransport(
        "https://example.test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_sync_handler_no_nested)),
    )
    client = AsyncRegistryBrokerClient(transport=transport)
    result = await client.get_registration_progress("a-1")
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_async_call_operation_with_all_params() -> None:
    client = _make_async_client()
    result = await client.call_operation(
        "search",
        query={"q": "test"},
        headers={"x-custom": "val"},
    )
    assert isinstance(result, dict)
