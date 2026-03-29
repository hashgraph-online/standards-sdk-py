"""Comprehensive tests for new async_client.py features."""

from __future__ import annotations

import base64
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from standards_sdk_py.exceptions import (
    ParseError,
    ValidationError,
)
from standards_sdk_py.registry_broker.async_client import (
    AsyncRegistryBrokerClient,
    _AsyncChatApi,
    _AsyncEncryptionApi,
    _normalize_headers,
)
from standards_sdk_py.registry_broker.models import (
    CreateSessionResponse,
    DelegationPlanResponse,
    ProtocolsResponse,
    RegistrationProgressResponse,
    RegistriesResponse,
    SearchResponse,
    SendMessageResponse,
    SkillPublishResponse,
    StatsResponse,
    VerificationStatusResponse,
)
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.http import AsyncHttpTransport

# ── Helpers ──────────────────────────────────────────────────────────

_MOCK_SEARCH = {
    "hits": [
        {
            "uaid": "uaid-1",
            "label": "Docs Agent",
            "score": 0.98,
            "metadata": {
                "delegationRoles": ["docs"],
                "delegationTaskTags": ["documentation"],
                "delegationProtocols": ["mcp"],
                "delegationSummary": "Specialized in docs.",
                "delegationSignals": {"verified": True},
            },
        }
    ],
    "total": 1,
    "page": 1,
    "limit": 20,
}
_MOCK_DELEGATION = {
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
                    "matchedQueries": ["docs markdown docusaurus"],
                    "matchedRoles": ["docs"],
                    "matchedProtocols": ["mcp"],
                    "matchedSurfaces": ["docs"],
                    "matchedLanguages": ["typescript"],
                    "matchedArtifacts": ["markdown"],
                    "matchedTaskTags": ["documentation"],
                    "reasons": ["Strong docs match"],
                    "suggestedMessage": "Update the docs tab set.",
                    "extraCandidateField": "preserved",
                }
            ],
            "extraOpportunityField": "preserved",
        }
    ],
    "extraRootField": "preserved",
}
_MOCK_STATS = {"totalAgents": 42, "totalSkills": 10}
_MOCK_SESSION = {"sessionId": "sess-1"}
_MOCK_MESSAGE = {"messageId": "msg-1"}
_MOCK_PROGRESS = {"status": "completed", "attemptId": "att-1"}
_MOCK_VERIFICATION = {"uaid": "u-1", "verified": True}
_MOCK_SKILL = {"topicId": "0.0.1", "hrl": "hrl://topic"}


def _make_async_client(mock_transport: MagicMock | None = None) -> AsyncRegistryBrokerClient:
    config = SdkConfig.from_mapping({})
    transport = mock_transport or MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    return AsyncRegistryBrokerClient(config=config, transport=transport)


# ── Init / properties ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_client_init() -> None:
    client = _make_async_client()
    assert client.base_url == "https://example.test"


@pytest.mark.asyncio
async def test_async_client_chat_property() -> None:
    client = _make_async_client()
    chat = client.chat
    assert isinstance(chat, _AsyncChatApi)
    assert client.chat is chat


@pytest.mark.asyncio
async def test_async_client_encryption_property() -> None:
    client = _make_async_client()
    enc = client.encryption
    assert isinstance(enc, _AsyncEncryptionApi)
    assert client.encryption is enc


# ── set_api_key / set_ledger_api_key / headers ───────────────────────


def test_async_set_api_key() -> None:
    client = _make_async_client()
    client.set_api_key("key")
    assert client.get_default_headers()["x-api-key"] == "key"


def test_async_set_ledger_api_key() -> None:
    client = _make_async_client()
    client.set_default_header("x-ledger-api-key", "old")
    client.set_ledger_api_key("new")
    headers = client.get_default_headers()
    assert headers["x-api-key"] == "new"
    assert "x-ledger-api-key" not in headers


def test_async_set_default_header_empty_name() -> None:
    client = _make_async_client()
    client.set_default_header("", "val")
    assert client.get_default_headers() == {}


# ── encryption_ready / build_url ─────────────────────────────────────


@pytest.mark.asyncio
async def test_async_encryption_ready() -> None:
    client = _make_async_client()
    assert await client.encryption_ready() is None


def test_async_build_url() -> None:
    client = _make_async_client()
    assert client.build_url("/foo") == "https://example.test/foo"
    assert client.build_url("bar") == "https://example.test/bar"


# ── request / request_json ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_request() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    mock_resp = MagicMock(spec=httpx.Response)
    transport.request = AsyncMock(return_value=mock_resp)
    client = _make_async_client(transport)
    result = await client.request("/path")
    assert result is mock_resp


@pytest.mark.asyncio
async def test_async_request_json_non_json() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.status_code = 200
    mock_resp.request = MagicMock()
    transport.request = AsyncMock(return_value=mock_resp)
    client = _make_async_client(transport)
    with pytest.raises(ParseError, match="Expected JSON response but got non-JSON"):
        await client.request_json("/path")


@pytest.mark.asyncio
async def test_async_request_json_success() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {"ok": True}
    transport.request = AsyncMock(return_value=mock_resp)
    client = _make_async_client(transport)
    result = await client.request_json("/path")
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_async_delegate() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=_MOCK_DELEGATION)
    client = _make_async_client(transport)
    result = await client.delegate(
        task="Review SDK PR feedback",
        context="We need a docs-focused pass.",
        limit=2,
        filter={"protocols": ["mcp"]},
        workspace={"repo": "hashgraph-online/standards-sdk"},
    )
    assert isinstance(result, DelegationPlanResponse)
    assert result.should_delegate is True
    assert result.opportunities[0].candidates[0].matched_roles == ["docs"]
    assert result.extraRootField == "preserved"
    assert result.opportunities[0].extraOpportunityField == "preserved"
    assert result.opportunities[0].candidates[0].extraCandidateField == "preserved"
    transport.request_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_search_parses_typed_delegation_metadata() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=_MOCK_SEARCH)
    client = _make_async_client(transport)
    result = await client.search(query="docs")
    assert isinstance(result, SearchResponse)
    assert result.hits[0].metadata is not None
    assert result.hits[0].metadata.delegation_roles == ["docs"]
    assert result.hits[0].metadata.delegation_signals["verified"] is True


# ── call_operation ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_call_operation_unknown() -> None:
    client = _make_async_client()
    with pytest.raises(ValidationError, match="Unknown Registry Broker operation"):
        await client.call_operation("nonexistent_op")


@pytest.mark.asyncio
async def test_async_call_operation_text_response() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.text = "ok"
    transport.request = AsyncMock(return_value=mock_resp)
    client = _make_async_client(transport)
    result = await client.call_operation(
        "resolve_skill_markdown",
        path_params={"skill_ref": "skill-a"},
    )
    assert result == "ok"


@pytest.mark.asyncio
async def test_async_call_operation_json_response() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"status": "ok"})
    client = _make_async_client(transport)
    result = await client.call_operation("stats")
    assert result == {"status": "ok"}


# ── _call_operation_alias ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_alias_kwarg_path_param() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=_MOCK_PROGRESS)
    client = _make_async_client(transport)
    result = await client._call_operation_alias("get_registration_progress", attempt_id="att-1")
    assert result == _MOCK_PROGRESS


@pytest.mark.asyncio
async def test_async_alias_positional_path_param() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=_MOCK_PROGRESS)
    client = _make_async_client(transport)
    result = await client._call_operation_alias("get_registration_progress", "att-1")
    assert result == _MOCK_PROGRESS


@pytest.mark.asyncio
async def test_async_alias_missing_path_param() -> None:
    client = _make_async_client()
    with pytest.raises(ValidationError, match="Missing required path parameter"):
        await client._call_operation_alias("get_registration_progress")


@pytest.mark.asyncio
async def test_async_alias_positional_dict_for_get() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=_MOCK_SEARCH)
    client = _make_async_client(transport)
    result = await client._call_operation_alias("search", {"q": "test"})
    assert result == _MOCK_SEARCH


@pytest.mark.asyncio
async def test_async_alias_positional_str_for_get() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=_MOCK_SEARCH)
    client = _make_async_client(transport)
    result = await client._call_operation_alias("search", "test-query")
    assert result == _MOCK_SEARCH


@pytest.mark.asyncio
async def test_async_alias_positional_for_post_dict() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"ok": True})
    client = _make_async_client(transport)
    result = await client._call_operation_alias("send_message", {"content": "hi"})
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_async_alias_positional_for_post_non_dict() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"ok": True})
    client = _make_async_client(transport)
    result = await client._call_operation_alias("send_message", "hello")
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_async_alias_remaining_kwargs_get() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=_MOCK_SEARCH)
    client = _make_async_client(transport)
    result = await client._call_operation_alias("search", q="test", limit=10)
    assert result == _MOCK_SEARCH


@pytest.mark.asyncio
async def test_async_alias_remaining_kwargs_post() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"ok": True})
    client = _make_async_client(transport)
    result = await client._call_operation_alias("send_message", content="hi", topicId="t-1")
    assert result == {"ok": True}


# ── search / search_erc8004 / stats / registries / protocols ─────────


@pytest.mark.asyncio
async def test_async_search() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=_MOCK_SEARCH)
    client = _make_async_client(transport)
    result = await client.search(query="hello")
    assert isinstance(result, SearchResponse)


@pytest.mark.asyncio
async def test_async_search_erc8004() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=_MOCK_SEARCH)
    client = _make_async_client(transport)
    result = await client.search_erc8004_by_agent_id(chain_id=1, agent_id=42, limit=5)
    assert isinstance(result, SearchResponse)


@pytest.mark.asyncio
async def test_async_stats() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=_MOCK_STATS)
    client = _make_async_client(transport)
    assert isinstance(await client.stats(), StatsResponse)


@pytest.mark.asyncio
async def test_async_registries() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"registries": []})
    client = _make_async_client(transport)
    assert isinstance(await client.registries(), RegistriesResponse)


@pytest.mark.asyncio
async def test_async_list_protocols() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"protocols": []})
    client = _make_async_client(transport)
    assert isinstance(await client.list_protocols(), ProtocolsResponse)


@pytest.mark.asyncio
async def test_async_detect_protocol() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"protocol": "hcs-10"})
    client = _make_async_client(transport)
    result = await client.detect_protocol("hello")
    assert result == {"protocol": "hcs-10"}


# ── session / message / registration / verification ──────────────────


@pytest.mark.asyncio
async def test_async_create_session() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=_MOCK_SESSION)
    client = _make_async_client(transport)
    result = await client.create_session({"uaid": "u-1"})
    assert isinstance(result, CreateSessionResponse)


@pytest.mark.asyncio
async def test_async_send_message() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=_MOCK_MESSAGE)
    client = _make_async_client(transport)
    result = await client.send_message({"content": "hi"})
    assert isinstance(result, SendMessageResponse)


@pytest.mark.asyncio
async def test_async_get_registration_progress_with_key() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"progress": _MOCK_PROGRESS})
    client = _make_async_client(transport)
    result = await client.get_registration_progress("att-1")
    assert isinstance(result, RegistrationProgressResponse)


@pytest.mark.asyncio
async def test_async_get_registration_progress_flat() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=_MOCK_PROGRESS)
    client = _make_async_client(transport)
    result = await client.get_registration_progress("att-1")
    assert isinstance(result, RegistrationProgressResponse)


@pytest.mark.asyncio
async def test_async_wait_for_registration_completion() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=_MOCK_PROGRESS)
    client = _make_async_client(transport)
    result = await client.wait_for_registration_completion("att-1", timeout_seconds=5)
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_async_wait_for_registration_timeout() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"status": "pending", "attemptId": "att-1"})
    client = _make_async_client(transport)
    with patch(
        "standards_sdk_py.registry_broker.async_client.monotonic",
        side_effect=[0.0, 100.0],
    ):
        with pytest.raises(ValidationError, match="Timed out"):
            await client.wait_for_registration_completion("att-1", timeout_seconds=0.001)


@pytest.mark.asyncio
async def test_async_get_verification_status() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=_MOCK_VERIFICATION)
    client = _make_async_client(transport)
    result = await client.get_verification_status("u-1")
    assert isinstance(result, VerificationStatusResponse)


@pytest.mark.asyncio
async def test_async_publish_skill() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=_MOCK_SKILL)
    client = _make_async_client(transport)
    result = await client.publish_skill({"name": "test"})
    assert isinstance(result, SkillPublishResponse)


# ── ledger auth ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_verify_ledger_sets_key() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"key": "api-key", "accountId": "0.0.1"})
    client = _make_async_client(transport)
    await client.verify_ledger_challenge({"challengeId": "ch-1"})
    assert client.get_default_headers()["x-api-key"] == "api-key"


@pytest.mark.asyncio
async def test_async_authenticate_with_ledger_sign_callback() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(
        side_effect=[
            {"challengeId": "ch-1", "message": "sign me"},
            {"key": "api-key", "accountId": "0.0.1"},
        ]
    )
    client = _make_async_client(transport)

    def signer(msg: str) -> dict[str, str]:
        del msg
        return {"signature": "sig123"}

    result = await client.authenticate_with_ledger(
        {
            "accountId": "0.0.1",
            "network": "testnet",
            "sign": signer,
        }
    )
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_async_authenticate_with_ledger_async_sign() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(
        side_effect=[
            {"challengeId": "ch-1", "message": "sign me"},
            {"key": "api-key", "accountId": "0.0.1"},
        ]
    )
    client = _make_async_client(transport)

    async def async_signer(msg: str) -> dict:
        return {"signature": "sig-async"}

    result = await client.authenticate_with_ledger(
        {
            "accountId": "0.0.1",
            "network": "testnet",
            "sign": async_signer,
        }
    )
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_async_authenticate_with_ledger_private_key() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(
        side_effect=[
            {"challengeId": "ch-1", "message": "sign me"},
            {"key": "api-key", "accountId": "0.0.1"},
        ]
    )
    client = _make_async_client(transport)
    with patch(
        "standards_sdk_py.registry_broker.async_client._sign_ledger_challenge",
        return_value=("sig", "pubkey"),
    ):
        result = await client.authenticate_with_ledger(
            {
                "accountId": "0.0.1",
                "network": "testnet",
                "privateKey": "pk-123",
            }
        )
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_async_authenticate_no_signer_no_key() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"challengeId": "ch-1", "message": "sign"})
    client = _make_async_client(transport)
    with pytest.raises(ValidationError, match="requires sign callback or privateKey"):
        await client.authenticate_with_ledger(
            {
                "accountId": "0.0.1",
                "network": "testnet",
            }
        )


@pytest.mark.asyncio
async def test_async_authenticate_non_dict_challenge() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.text = "not-json"
    transport.request = AsyncMock(return_value=mock_resp)
    client = _make_async_client(transport)
    with pytest.raises(ValidationError, match="must be an object"):
        await client.authenticate_with_ledger({"accountId": "0.0.1", "network": "testnet"})


@pytest.mark.asyncio
async def test_async_authenticate_credentials_sets_header() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(
        side_effect=[
            {"challengeId": "ch-1", "message": "sign me"},
            {"key": "api-key", "accountId": "0.0.1"},
        ]
    )
    client = _make_async_client(transport)

    def signer(msg: str) -> dict[str, str]:
        del msg
        return {"signature": "sig"}

    await client.authenticate_with_ledger_credentials(
        {
            "accountId": "0.0.1",
            "network": "testnet",
            "sign": signer,
        }
    )
    assert client.get_default_headers().get("x-account-id") == "0.0.1"


# ── History / decryption / crypto ────────────────────────────────────


@pytest.mark.asyncio
async def test_async_fetch_history_text_response() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value="not-json")
    client = _make_async_client(transport)
    with pytest.raises(ParseError, match="Expected JSON response but got text"):
        await client.fetch_history_snapshot("sess-1")


def test_async_attach_decrypted_non_dict() -> None:
    client = _make_async_client()
    assert client.attach_decrypted_history("s", [1, 2]) == [1, 2]


def test_async_attach_decrypted_no_decrypt() -> None:
    client = _make_async_client()
    snapshot = {"history": [{"content": "hi"}]}
    assert client.attach_decrypted_history("s", snapshot) == snapshot


def test_async_attach_decrypted_with_decrypt() -> None:
    client = _make_async_client()
    shared = os.urandom(32)
    env = client.build_cipher_envelope(
        {
            "sharedSecret": shared,
            "plaintext": "secret",
            "sessionId": "s",
        }
    )
    client.register_conversation_context_for_encryption(
        {
            "sessionId": "s",
            "sharedSecret": shared,
        }
    )
    result = client.attach_decrypted_history(
        "s",
        {"history": [{"cipherEnvelope": env}]},
        {"decrypt": True},
    )
    assert result["decryptedHistory"][0]["plaintext"] == "secret"


def test_async_attach_decrypted_auto() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    client = AsyncRegistryBrokerClient(
        config=SdkConfig.from_mapping({}),
        transport=transport,
        encryption_options={"autoDecryptHistory": True},
    )
    client.register_conversation_context_for_encryption(
        {
            "sessionId": "s",
            "sharedSecret": b"x" * 32,
        }
    )
    result = client.attach_decrypted_history("s", {"history": [{"content": "hi"}]})
    assert "decryptedHistory" in result


def test_async_resolve_decryption_from_options() -> None:
    client = _make_async_client()
    ctx = client.resolve_decryption_context("s", {"sharedSecret": b"abc"})
    assert ctx is not None


def test_async_resolve_decryption_none() -> None:
    client = _make_async_client()
    assert client.resolve_decryption_context("s") is None


def test_async_decrypt_entry_no_cipher() -> None:
    client = _make_async_client()
    assert client.decrypt_history_entry_from_context("s", {"content": "p"}, {}) == "p"


def test_async_decrypt_entry_non_dict_envelope() -> None:
    client = _make_async_client()
    assert client.decrypt_history_entry_from_context("s", {"cipherEnvelope": "x"}, {}) is None


def test_async_decrypt_entry_bad_secret() -> None:
    client = _make_async_client()
    assert (
        client.decrypt_history_entry_from_context(
            "s", {"cipherEnvelope": {"nonce": "x", "ciphertext": "y"}}, {"sharedSecret": 123}
        )
        is None
    )


# ── Crypto methods ───────────────────────────────────────────────────


def test_async_ephemeral_key_pair() -> None:
    client = _make_async_client()
    pair = client.create_ephemeral_key_pair()
    assert "publicKey" in pair


def test_async_derive_shared_secret() -> None:
    client = _make_async_client()
    secret = client.derive_shared_secret({"privateKey": "p", "peerPublicKey": "q"})
    assert isinstance(secret, bytes)


def test_async_normalize_shared_secret_types() -> None:
    client = _make_async_client()
    assert client.normalize_shared_secret(b"hello") == b"hello"
    assert client.normalize_shared_secret(bytearray(b"hi")) == b"hi"
    assert client.normalize_shared_secret("deadbeef") == bytes.fromhex("deadbeef")
    with pytest.raises(ValidationError):
        client.normalize_shared_secret(42)


def test_async_buffer_from_string_empty() -> None:
    client = _make_async_client()
    with pytest.raises(ValidationError, match="cannot be empty"):
        client.buffer_from_string("")


def test_async_hex_to_buffer() -> None:
    client = _make_async_client()
    assert client.hex_to_buffer("aabb") == bytes.fromhex("aabb")
    with pytest.raises(ValidationError, match="Expected hex"):
        client.hex_to_buffer("zzz")


def test_async_build_and_open_cipher() -> None:
    client = _make_async_client()
    shared = os.urandom(32)
    env = client.build_cipher_envelope(
        {
            "sharedSecret": shared,
            "plaintext": "msg",
            "sessionId": "s",
        }
    )
    assert client.open_cipher_envelope({"envelope": env, "sharedSecret": shared}) == "msg"


def test_async_generate_key_pair() -> None:
    client = _make_async_client()
    pair = client.generate_encryption_key_pair()
    assert pair["envVar"] == "RB_ENCRYPTION_PRIVATE_KEY"


# ── Chat / conversation ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_start_chat() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"sessionId": "sess-1"})
    client = _make_async_client(transport)
    result = await client.start_chat(
        {
            "uaid": "u-1",
            "agentUrl": "https://agent",
            "auth": {"k": "v"},
            "historyTtlSeconds": 300,
            "senderUaid": "s-1",
        }
    )
    assert result["mode"] == "plaintext"


@pytest.mark.asyncio
async def test_async_start_conversation() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"sessionId": "sess-1"})
    client = _make_async_client(transport)
    result = await client.start_conversation({"uaid": "u-1"})
    assert result["mode"] == "plaintext"


@pytest.mark.asyncio
async def test_async_accept_conversation() -> None:
    client = _make_async_client()
    result = await client.accept_conversation({"sessionId": "s-1", "responderUaid": "r-1"})
    assert result["mode"] == "plaintext"


@pytest.mark.asyncio
async def test_async_compact_history() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"ok": True})
    client = _make_async_client(transport)
    result = await client.compact_history({"sessionId": "s-1", "preserveEntries": 5})
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_async_end_session() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value=None)
    client = _make_async_client(transport)
    await client.end_session("s-1")


# ── _AsyncChatApi ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_chat_api_methods() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"sessionId": "sess-1"})
    client = _make_async_client(transport)
    chat = client.chat

    result = await chat.start({"uaid": "u-1"})
    assert result["mode"] == "plaintext"

    transport.request_json = AsyncMock(return_value=_MOCK_SESSION)
    result = await chat.create_session({"uaid": "u-1"})
    assert isinstance(result, CreateSessionResponse)

    transport.request_json = AsyncMock(return_value=_MOCK_MESSAGE)
    result = await chat.send_message({"content": "hi"})

    transport.request_json = AsyncMock(return_value=None)
    await chat.end_session("s-1")

    transport.request_json = AsyncMock(return_value={"ok": True})
    await chat.compact_history({"sessionId": "s-1"})
    await chat.get_encryption_status("s-1")
    await chat.submit_encryption_handshake("s-1", {"k": "v"})

    transport.request_json = AsyncMock(return_value={"sessionId": "s-2"})
    await chat.start_conversation({"uaid": "u-1"})
    result = await chat.accept_conversation({"sessionId": "s-2"})
    await chat.create_encrypted_session({"uaid": "u-1"})
    result = await chat.accept_encrypted_session({"sessionId": "s-3"})


# ── _AsyncEncryptionApi ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_encryption_api_methods() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"ok": True})
    client = _make_async_client(transport)
    enc = client.encryption

    await enc.register_key({"publicKey": "pk"})
    pair = enc.generate_ephemeral_key_pair()
    assert "publicKey" in pair

    secret = enc.derive_shared_secret({"privateKey": "p", "peerPublicKey": "q"})
    assert isinstance(secret, bytes)

    shared = os.urandom(32)
    envelope = enc.encrypt_cipher_envelope(
        {
            "sharedSecret": shared,
            "plaintext": "hi",
            "sessionId": "s",
        }
    )
    assert "ciphertext" in envelope

    plaintext = enc.decrypt_cipher_envelope({"envelope": envelope, "sharedSecret": shared})
    assert plaintext == "hi"


@pytest.mark.asyncio
async def test_async_encryption_api_ensure_agent_key() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"ok": True})
    client = _make_async_client(transport)
    result = await client.encryption.ensure_agent_key({"uaid": "u-1"})
    assert "publicKey" in result


# ── buy_credits_with_x402 ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_buy_credits_x402() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"ok": True})
    client = _make_async_client(transport)
    result = await client.buy_credits_with_x402(
        {
            "amount": 10,
            "evmPrivateKey": "x",
            "network": "y",
            "rpcUrl": "z",
        }
    )
    assert result == {"ok": True}


# ── close / __getattr__ / _parse_model ───────────────────────────────


@pytest.mark.asyncio
async def test_async_close() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.close = AsyncMock()
    client = _make_async_client(transport)
    await client.close()
    transport.close.assert_awaited_once()


def test_async_getattr_camel_alias() -> None:
    client = _make_async_client()
    fn = client.setApiKey
    assert callable(fn)


def test_async_getattr_operation() -> None:
    client = _make_async_client()
    fn = client.stats
    assert callable(fn)


def test_async_getattr_unknown() -> None:
    client = _make_async_client()
    with pytest.raises(AttributeError):
        _ = client.totally_nonexistent_xyz


def test_async_parse_model_text() -> None:
    with pytest.raises(ParseError, match="Expected JSON"):
        AsyncRegistryBrokerClient._parse_model("text", SearchResponse)


def test_async_parse_model_invalid() -> None:
    with pytest.raises(ParseError, match="Failed to validate"):
        AsyncRegistryBrokerClient._parse_model({"bad_field": True}, CreateSessionResponse)


def test_async_assert_node_runtime() -> None:
    client = _make_async_client()
    assert client.assert_node_runtime("any") is None


# ── _sign_ledger_challenge wrapper (L122-125) ────────────────────────


def test_async_sign_ledger_challenge_wrapper() -> None:
    from standards_sdk_py.registry_broker.async_client import (
        _sign_ledger_challenge as _async_sign_ledger_challenge,
    )

    with patch(
        "standards_sdk_py.inscriber.client._sign_ledger_challenge",
        return_value=("sig-val", "pub-val"),
    ):
        sig, pub = _async_sign_ledger_challenge("msg", "pk")
    assert sig == "sig-val"
    assert pub == "pub-val"


# ── _normalize_headers with empty key strip (L119) ──────────────────


def test_async_normalize_headers_empty_strip() -> None:
    result = _normalize_headers({"  X-Key  ": "val", "": "skip", "  ": "skip2"})
    assert result == {"x-key": "val"}


# ── _AsyncChatApi.get_history (L145) ────────────────────────────────


@pytest.mark.asyncio
async def test_async_chat_api_get_history() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"history": []})
    client = _make_async_client(transport)
    result = await client.chat.get_history("sess-1", {"decrypt": False})
    assert "history" in result


# ── create_verification_challenge / verify_sender_ownership (L457, 460)


@pytest.mark.asyncio
async def test_async_create_verification_challenge() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"challengeId": "ch-1"})
    client = _make_async_client(transport)
    result = await client.create_verification_challenge("u-1")
    assert result == {"challengeId": "ch-1"}


@pytest.mark.asyncio
async def test_async_verify_sender_ownership() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"verified": True})
    client = _make_async_client(transport)
    result = await client.verify_sender_ownership("u-1")
    assert result == {"verified": True}


# ── authenticate_with_ledger missing fields (L484) ──────────────────


@pytest.mark.asyncio
async def test_async_authenticate_missing_fields() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"challengeId": "ch-1"})
    client = _make_async_client(transport)
    with pytest.raises(ValidationError, match="missing required fields"):
        await client.authenticate_with_ledger({"accountId": "0.0.1", "network": "testnet"})


# ── fetch_history_snapshot JSON success (L529) ──────────────────────


@pytest.mark.asyncio
async def test_async_fetch_history_json() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json = AsyncMock(return_value={"history": [{"content": "hi"}]})
    client = _make_async_client(transport)
    result = await client.fetch_history_snapshot("sess-1")
    assert "history" in result


# ── decrypt exception (L615-616) ────────────────────────────────────


def test_async_decrypt_exception() -> None:
    client = _make_async_client()
    bad_envelope = {"nonce": "invalid!!!", "ciphertext": "invalid!!!"}
    ctx = {"sharedSecret": base64.b64encode(b"x" * 32).decode()}
    result = client.decrypt_history_entry_from_context("s", {"cipherEnvelope": bad_envelope}, ctx)
    assert result is None


# ── non-dict entries in history (L553-557) ──────────────────────────


def test_async_attach_decrypted_non_dict_entries() -> None:
    client = _make_async_client()
    client.register_conversation_context_for_encryption(
        {
            "sessionId": "s",
            "sharedSecret": b"x" * 32,
        }
    )
    snapshot = {"history": ["not-a-dict", {"content": "hi"}, 42]}
    result = client.attach_decrypted_history("s", snapshot, {"decrypt": True})
    assert len(result["decryptedHistory"]) == 1


# ── register context with identity (L576) ───────────────────────────


def test_async_register_context_identity() -> None:
    client = _make_async_client()
    client.register_conversation_context_for_encryption(
        {
            "sessionId": "s",
            "sharedSecret": b"x" * 32,
            "identity": {"name": "alice"},
        }
    )
    ctx = client.resolve_decryption_context("s")
    assert ctx is not None
    assert ctx["identity"] == {"name": "alice"}


# ── attach_decrypted_history: non-list history (L550) ───────────────


def test_async_attach_decrypted_non_list_history() -> None:
    client = _make_async_client()
    snapshot = {"history": "not-a-list"}
    result = client.attach_decrypted_history("sess-1", snapshot, {"decrypt": True})
    assert result == snapshot


# ── attach_decrypted_history: no context (L553) ─────────────────────


def test_async_attach_decrypted_no_context() -> None:
    client = _make_async_client()
    snapshot = {"history": [{"content": "hi"}]}
    result = client.attach_decrypted_history("sess-1", snapshot, {"decrypt": True})
    assert result == snapshot


# ── buffer_from_string base64 fallback (L728) ───────────────────────


def test_async_buffer_from_string_base64() -> None:
    client = _make_async_client()
    b64 = base64.b64encode(b"hello").decode()
    result = client.buffer_from_string(b64)
    assert result == b"hello"


# ── __getattr__ camelCase snake_name conversion (L786-788) ──────────


def test_async_getattr_camel_snake() -> None:
    client = _make_async_client()
    fn = client.createSession
    assert callable(fn)
