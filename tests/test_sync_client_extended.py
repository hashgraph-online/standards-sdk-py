"""Comprehensive tests for new sync_client.py features."""

from __future__ import annotations

import base64
import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from standards_sdk_py.exceptions import (
    ApiError,
    ErrorContext,
    ParseError,
    ValidationError,
)
from standards_sdk_py.registry_broker.models import (
    CreateSessionResponse,
    DelegationPlanResponse,
    ProtocolsResponse,
    RegistrationProgressResponse,
    RegistriesResponse,
    SearchHit,
    SearchResponse,
    SendMessageResponse,
    SkillPublishResponse,
    StatsResponse,
    VerificationStatusResponse,
)
from standards_sdk_py.registry_broker.sync_client import (
    RegistryBrokerClient,
    RequestConfig,
    _camel_to_snake,
    _ChatApi,
    _EncryptionApi,
    _fill_path,
    _normalize_header_name,
    _normalize_headers,
    _query_from_values,
    _snake_to_camel,
)
from standards_sdk_py.registry_broker.sync_client import (
    _sign_ledger_challenge as _sync_sign_ledger_challenge,
)
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.http import SyncHttpTransport

# ── Helper: create a client backed by a mock transport ────────────────

_MOCK_SEARCH_RESPONSE = {
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
_MOCK_DELEGATION_RESPONSE = {
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
_MOCK_STATS_RESPONSE = {"totalAgents": 42, "totalSkills": 10}
_MOCK_REGISTRIES_RESPONSE = {"registries": []}
_MOCK_PROTOCOLS_RESPONSE = {"protocols": []}
_MOCK_SESSION_RESPONSE = {"sessionId": "sess-1"}
_MOCK_MESSAGE_RESPONSE = {"messageId": "msg-1"}
_MOCK_PROGRESS_RESPONSE = {"status": "completed", "attemptId": "att-1"}
_MOCK_VERIFICATION_RESPONSE = {"uaid": "u-1", "verified": True}
_MOCK_SKILL_PUBLISH_RESPONSE = {"topicId": "0.0.1", "hrl": "hrl://topic"}


def _make_client(mock_transport: MagicMock | None = None) -> RegistryBrokerClient:
    """Build a RegistryBrokerClient with a mock transport."""
    config = SdkConfig.from_mapping({})
    transport = mock_transport or MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    return RegistryBrokerClient(config=config, transport=transport)


# ── Helper util tests ────────────────────────────────────────────────


def test_camel_to_snake() -> None:
    assert _camel_to_snake("sendMessage") == "send_message"
    assert _camel_to_snake("HTMLParser") == "h_t_m_l_parser"
    assert _camel_to_snake("simple") == "simple"


def test_snake_to_camel() -> None:
    assert _snake_to_camel("send_message") == "sendMessage"
    assert _snake_to_camel("single") == "single"
    assert _snake_to_camel("a_b_c") == "aBC"


def test_normalize_header_name() -> None:
    assert _normalize_header_name("  X-Api-Key  ") == "x-api-key"


def test_normalize_headers_empty() -> None:
    assert _normalize_headers(None) == {}
    assert _normalize_headers({}) == {}


def test_normalize_headers_strips() -> None:
    result = _normalize_headers({"  X-Api-Key ": "val", "": "ignored"})
    assert result == {"x-api-key": "val"}


# ── RegistryBrokerClient init / properties ───────────────────────────


def test_client_init_defaults() -> None:
    with patch.dict(os.environ, {}, clear=False):
        client = _make_client()
        assert client.base_url == "https://example.test"


def test_client_chat_property() -> None:
    client = _make_client()
    chat = client.chat
    assert isinstance(chat, _ChatApi)
    # Cached
    assert client.chat is chat


def test_client_encryption_property() -> None:
    client = _make_client()
    enc = client.encryption
    assert isinstance(enc, _EncryptionApi)
    assert client.encryption is enc


# ── set_api_key / set_ledger_api_key / set_default_header ────────────


def test_set_api_key() -> None:
    client = _make_client()
    client.set_api_key("my-key")
    assert client.get_default_headers()["x-api-key"] == "my-key"


def test_set_ledger_api_key() -> None:
    client = _make_client()
    client.set_default_header("x-ledger-api-key", "old-ledger")
    client.set_ledger_api_key("new-key")
    headers = client.get_default_headers()
    assert headers["x-api-key"] == "new-key"
    assert "x-ledger-api-key" not in headers


def test_set_default_header_remove() -> None:
    client = _make_client()
    client.set_default_header("x-custom", "val")
    assert "x-custom" in client.get_default_headers()
    client.set_default_header("x-custom", None)
    assert "x-custom" not in client.get_default_headers()


def test_set_default_header_empty_name() -> None:
    client = _make_client()
    client.set_default_header("", "val")
    # Should be a no-op
    assert client.get_default_headers() == {}


# ── encryption_ready / build_url / delay / assert_node_runtime ───────


def test_encryption_ready() -> None:
    client = _make_client()
    assert client.encryption_ready() is None


def test_build_url() -> None:
    client = _make_client()
    assert client.build_url("/foo") == "https://example.test/foo"
    assert client.build_url("bar") == "https://example.test/bar"


def test_delay() -> None:
    client = _make_client()
    client.delay(0)  # No-op
    client.delay(-1)  # No-op


def test_assert_node_runtime() -> None:
    client = _make_client()
    assert client.assert_node_runtime("any") is None


# ── request / request_json ───────────────────────────────────────────


def test_request() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    mock_response = MagicMock(spec=httpx.Response)
    transport.request.return_value = mock_response
    client = _make_client(transport)
    result = client.request("/path")
    assert result is mock_response


def test_request_with_config() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    mock_response = MagicMock(spec=httpx.Response)
    transport.request.return_value = mock_response
    client = _make_client(transport)
    config: RequestConfig = {
        "method": "POST",
        "body": {"key": "value"},
        "headers": {"x-custom": "h"},
    }
    result = client.request("/path", config)
    assert result is mock_response
    transport.request.assert_called_once()


def test_request_json_non_json_content_type() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.headers = {"content-type": "text/html"}
    mock_response.status_code = 200
    mock_response.request = MagicMock()
    transport.request.return_value = mock_response
    client = _make_client(transport)
    with pytest.raises(ParseError, match="Expected JSON response but got non-JSON"):
        client.request_json("/path")


def test_request_json_success() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"ok": True}
    transport.request.return_value = mock_response
    client = _make_client(transport)
    result = client.request_json("/path")
    assert result == {"ok": True}


def test_delegate() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_DELEGATION_RESPONSE
    client = _make_client(transport)
    result = client.delegate(
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
    transport.request_json.assert_called_once()


def test_delegate_accepts_query_filter_alias() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_DELEGATION_RESPONSE
    client = _make_client(transport)
    result = client.delegate(
        task="Review SDK PR feedback",
        query_filter={"protocols": ["mcp"]},
    )
    assert result.should_delegate is True
    transport.request_json.assert_called_once()


def test_search_parses_typed_delegation_metadata() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_SEARCH_RESPONSE
    client = _make_client(transport)
    result = client.search(query="docs")
    assert isinstance(result, SearchResponse)
    assert result.hits[0].metadata is not None
    assert result.hits[0].metadata.delegation_roles == ["docs"]
    assert result.hits[0].metadata.delegation_signals["verified"] is True
    assert result.hits[0]["uaid"] == "uaid-1"
    assert result.hits[0].get("score") == 0.98


def test_search_hit_mapping_preserves_missing_key_behavior() -> None:
    hit = SearchHit(uaid="uaid-1")
    with pytest.raises(KeyError):
        _ = hit["metadata"]
    assert hit.get("metadata") is None


def test_search_hit_mapping_preserves_explicit_nulls_and_extra_fields() -> None:
    hit = SearchHit.model_validate(
        {
            "uaid": "uaid-1",
            "metadata": None,
            "verified": None,
            "customScore": 7,
        }
    )
    assert hit["metadata"] is None
    assert hit["verified"] is None
    assert hit.get("customScore") == 7
    assert dict(hit.items())["customScore"] == 7
    assert "metadata" in hit
    assert "verified" in hit
    assert "customScore" in hit
    assert "missing" not in hit


# ── call_operation ───────────────────────────────────────────────────


def test_call_operation_unknown() -> None:
    client = _make_client()
    with pytest.raises(ValidationError, match="Unknown Registry Broker operation"):
        client.call_operation("nonexistent_op")


def test_call_operation_text_response() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.text = "ok"
    transport.request.return_value = mock_response
    client = _make_client(transport)
    result = client.call_operation(
        "resolve_skill_markdown",
        path_params={"skill_ref": "skill-a"},
    )
    assert result == "ok"


def test_call_operation_json_response() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"status": "ok"}
    client = _make_client(transport)
    result = client.call_operation("stats")
    assert result == {"status": "ok"}


# ── _call_operation_alias ────────────────────────────────────────────


def test_call_operation_alias_with_path_params_in_kwargs() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_PROGRESS_RESPONSE
    client = _make_client(transport)
    result = client._call_operation_alias(
        "get_registration_progress",
        attempt_id="att-1",
    )
    assert result == _MOCK_PROGRESS_RESPONSE


def test_call_operation_alias_with_positional_path_param() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_PROGRESS_RESPONSE
    client = _make_client(transport)
    result = client._call_operation_alias("get_registration_progress", "att-1")
    assert result == _MOCK_PROGRESS_RESPONSE


def test_call_operation_alias_missing_path_param() -> None:
    client = _make_client()
    with pytest.raises(ValidationError, match="Missing required path parameter"):
        client._call_operation_alias("get_registration_progress")


def test_call_operation_alias_positional_body_for_post() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"status": "ok"}
    client = _make_client(transport)
    # search is a GET operation, first positional should be query
    result = client._call_operation_alias("search", {"q": "test"})
    assert result == {"status": "ok"}


def test_call_operation_alias_positional_primitive_for_get() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"status": "ok"}
    client = _make_client(transport)
    # search is GET, passing a non-dict positional gets wrapped as {"q": value}
    result = client._call_operation_alias("search", "test-query")
    assert result == {"status": "ok"}


def test_call_operation_alias_positional_body_for_post_non_dict() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"ok": True}
    client = _make_client(transport)
    # send_message is POST, passing a non-dict positional gets wrapped as {"value": ...}
    result = client._call_operation_alias("send_message", "hello")
    assert result == {"ok": True}


def test_call_operation_alias_remaining_kwargs_for_get() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"status": "ok"}
    client = _make_client(transport)
    result = client._call_operation_alias("search", q="test", limit=10)
    assert result == {"status": "ok"}


def test_call_operation_alias_remaining_kwargs_for_post() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"ok": True}
    client = _make_client(transport)
    result = client._call_operation_alias("send_message", content="hi", topicId="t-1")
    assert result == {"ok": True}


# ── search / search_erc8004 ──────────────────────────────────────────


def test_search() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_SEARCH_RESPONSE
    client = _make_client(transport)
    result = client.search(query="hello")
    assert isinstance(result, SearchResponse)


def test_search_erc8004_by_agent_id() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_SEARCH_RESPONSE
    client = _make_client(transport)
    result = client.search_erc8004_by_agent_id(
        chain_id=1,
        agent_id=42,
        limit=5,
        page=1,
        sort_by="name",
        sort_order="asc",
    )
    assert isinstance(result, SearchResponse)


# ── stats / registries / list_protocols / detect_protocol ────────────


def test_stats() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_STATS_RESPONSE
    client = _make_client(transport)
    assert isinstance(client.stats(), StatsResponse)


def test_registries() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_REGISTRIES_RESPONSE
    client = _make_client(transport)
    assert isinstance(client.registries(), RegistriesResponse)


def test_list_protocols() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_PROTOCOLS_RESPONSE
    client = _make_client(transport)
    assert isinstance(client.list_protocols(), ProtocolsResponse)


def test_detect_protocol() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"protocol": "hcs-10"}
    client = _make_client(transport)
    result = client.detect_protocol("hello")
    assert result == {"protocol": "hcs-10"}


# ── session / message / registration / verification ──────────────────


def test_create_session() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_SESSION_RESPONSE
    client = _make_client(transport)
    result = client.create_session({"uaid": "u-1"})
    assert isinstance(result, CreateSessionResponse)


def test_send_message() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_MESSAGE_RESPONSE
    client = _make_client(transport)
    result = client.send_message({"content": "hi"})
    assert isinstance(result, SendMessageResponse)


def test_get_registration_progress_with_progress_key() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"progress": _MOCK_PROGRESS_RESPONSE}
    client = _make_client(transport)
    result = client.get_registration_progress("att-1")
    assert isinstance(result, RegistrationProgressResponse)


def test_get_registration_progress_flat() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_PROGRESS_RESPONSE
    client = _make_client(transport)
    result = client.get_registration_progress("att-1")
    assert isinstance(result, RegistrationProgressResponse)


def test_wait_for_registration_completion_success() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_PROGRESS_RESPONSE
    client = _make_client(transport)
    result = client.wait_for_registration_completion("att-1", timeout_seconds=5)
    assert result.status == "completed"


def test_wait_for_registration_completion_timeout() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"status": "pending", "attemptId": "att-1"}
    client = _make_client(transport)
    with patch("standards_sdk_py.registry_broker.sync_client.monotonic", side_effect=[0.0, 100.0]):
        with pytest.raises(ValidationError, match="Timed out"):
            client.wait_for_registration_completion("att-1", timeout_seconds=0.001)


def test_get_verification_status() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_VERIFICATION_RESPONSE
    client = _make_client(transport)
    result = client.get_verification_status("u-1")
    assert isinstance(result, VerificationStatusResponse)


def test_publish_skill() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_SKILL_PUBLISH_RESPONSE
    client = _make_client(transport)
    result = client.publish_skill({"name": "test"})
    assert isinstance(result, SkillPublishResponse)


# ── verify_ledger_challenge / authenticate_with_ledger ───────────────


def test_verify_ledger_challenge_sets_api_key() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"key": "new-api-key", "accountId": "0.0.1"}
    client = _make_client(transport)
    result = client.verify_ledger_challenge({"challengeId": "ch-1"})
    assert isinstance(result, dict)
    assert client.get_default_headers()["x-api-key"] == "new-api-key"


def test_verify_ledger_challenge_no_key() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"status": "ok"}
    client = _make_client(transport)
    result = client.verify_ledger_challenge({"challengeId": "ch-1"})
    assert result == {"status": "ok"}


def test_authenticate_with_ledger_sign_callback() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.side_effect = [
        {"challengeId": "ch-1", "message": "sign me"},
        {"key": "api-key", "accountId": "0.0.1", "network": "testnet"},
    ]
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.text = "ok"
    transport.request.return_value = mock_resp
    client = _make_client(transport)

    def signer(msg: str) -> dict[str, str]:
        del msg
        return {"signature": "sig123", "publicKey": "pk123"}

    result = client.authenticate_with_ledger(
        {
            "accountId": "0.0.1",
            "network": "testnet",
            "sign": signer,
        }
    )
    assert isinstance(result, dict)


def test_authenticate_with_ledger_private_key() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.side_effect = [
        {"challengeId": "ch-1", "message": "sign me"},
        {"key": "api-key", "accountId": "0.0.1"},
    ]
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.text = "ok"
    transport.request.return_value = mock_resp
    client = _make_client(transport)
    with patch(
        "standards_sdk_py.registry_broker.sync_client._sign_ledger_challenge",
        return_value=("sig", "pubkey"),
    ):
        result = client.authenticate_with_ledger(
            {
                "accountId": "0.0.1",
                "network": "testnet",
                "privateKey": "pk-123",
            }
        )
    assert isinstance(result, dict)


def test_authenticate_with_ledger_no_signer_no_key() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"challengeId": "ch-1", "message": "sign me"}
    client = _make_client(transport)
    with pytest.raises(ValidationError, match="requires sign callback or privateKey"):
        client.authenticate_with_ledger(
            {
                "accountId": "0.0.1",
                "network": "testnet",
            }
        )


def test_authenticate_with_ledger_non_dict_challenge() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.text = "not-json"
    transport.request.return_value = mock_resp
    client = _make_client(transport)
    with pytest.raises(ValidationError, match="must be an object"):
        client.authenticate_with_ledger(
            {
                "accountId": "0.0.1",
                "network": "testnet",
            }
        )


def test_authenticate_with_ledger_credentials_sets_account_header() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.side_effect = [
        {"challengeId": "ch-1", "message": "sign me"},
        {"key": "api-key", "accountId": "0.0.1"},
    ]
    client = _make_client(transport)

    def signer(msg: str) -> dict[str, str]:
        del msg
        return {"signature": "sig"}

    client.authenticate_with_ledger_credentials(
        {
            "accountId": "0.0.1",
            "network": "testnet",
            "sign": signer,
        }
    )
    assert client.get_default_headers().get("x-account-id") == "0.0.1"


# ── register_agent / ensure_credits / purchase_credits ───────────────


def test_register_agent_without_auto_top_up() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"registered": True}
    client = _make_client(transport)
    result = client.register_agent({"name": "test"})
    assert result == {"registered": True}


def test_register_agent_with_auto_top_up() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    # Quote returns no shortfall, then register
    transport.request_json.side_effect = [
        {"shortfallCredits": 0, "creditsPerHbar": 100},
        {"registered": True},
    ]
    client = _make_client(transport)
    result = client.register_agent(
        {"name": "test"},
        {"autoTopUp": {"accountId": "0.0.1", "privateKey": "pk"}},
    )
    assert result == {"registered": True}


def test_ensure_credits_no_shortfall() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"shortfallCredits": 0}
    client = _make_client(transport)
    client.ensure_credits_for_registration(
        {"name": "test"},
        {"accountId": "0.0.1", "privateKey": "pk"},
    )


def test_ensure_credits_missing_account() -> None:
    client = _make_client()
    with pytest.raises(ValidationError, match="accountId and privateKey"):
        client.ensure_credits_for_registration({"name": "test"}, {})


def test_ensure_credits_with_shortfall() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.side_effect = [
        {"shortfallCredits": 10, "creditsPerHbar": 100},
        {"ok": True},  # purchase
        {"shortfallCredits": 0},  # next quote
    ]
    client = _make_client(transport)
    client.ensure_credits_for_registration(
        {"name": "test"},
        {"accountId": "0.0.1", "privateKey": "pk"},
    )


def test_ensure_credits_bad_credits_per_hbar() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"shortfallCredits": 10, "creditsPerHbar": 0}
    client = _make_client(transport)
    with pytest.raises(ValidationError, match="Unable to determine credits per HBAR"):
        client.ensure_credits_for_registration(
            {"name": "test"},
            {"accountId": "0.0.1", "privateKey": "pk"},
        )


def test_purchase_credits_with_hbar() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"ok": True}
    client = _make_client(transport)
    result = client.purchase_credits_with_hbar(
        {
            "accountId": "0.0.1",
            "privateKey": "pk",
            "hbarAmount": 1.0,
            "memo": "test",
            "metadata": {"purpose": "test"},
        }
    )
    assert result == {"ok": True}


def test_buy_credits_with_x402() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"ok": True}
    client = _make_client(transport)
    result = client.buy_credits_with_x402(
        {
            "amount": 10,
            "evmPrivateKey": "removed",
            "network": "removed",
            "rpcUrl": "removed",
        }
    )
    assert result == {"ok": True}


# ── Crypto / encryption helpers ──────────────────────────────────────


def test_create_ephemeral_key_pair() -> None:
    client = _make_client()
    pair = client.create_ephemeral_key_pair()
    assert "privateKey" in pair
    assert "publicKey" in pair


def test_derive_shared_secret() -> None:
    client = _make_client()
    secret = client.derive_shared_secret({"privateKey": "pk", "peerPublicKey": "peer"})
    assert isinstance(secret, bytes)
    assert len(secret) == 32


def test_normalize_shared_secret_bytes() -> None:
    client = _make_client()
    data = b"hello"
    assert client.normalize_shared_secret(data) == data


def test_normalize_shared_secret_bytearray() -> None:
    client = _make_client()
    data = bytearray(b"hello")
    assert client.normalize_shared_secret(data) == b"hello"


def test_normalize_shared_secret_hex_string() -> None:
    client = _make_client()
    result = client.normalize_shared_secret("deadbeef")
    assert result == bytes.fromhex("deadbeef")


def test_normalize_shared_secret_0x_hex() -> None:
    client = _make_client()
    result = client.normalize_shared_secret("0xdeadbeef")
    assert result == bytes.fromhex("deadbeef")


def test_normalize_shared_secret_base64() -> None:
    client = _make_client()
    b64 = base64.b64encode(b"secret").decode()
    result = client.normalize_shared_secret(b64)
    assert result == b"secret"


def test_normalize_shared_secret_unsupported() -> None:
    client = _make_client()
    with pytest.raises(ValidationError, match="Unsupported shared secret"):
        client.normalize_shared_secret(12345)


def test_buffer_from_string_empty() -> None:
    client = _make_client()
    with pytest.raises(ValidationError, match="cannot be empty"):
        client.buffer_from_string("")


def test_hex_to_buffer() -> None:
    client = _make_client()
    assert client.hex_to_buffer("deadbeef") == bytes.fromhex("deadbeef")
    assert client.hex_to_buffer("0xaabb") == bytes.fromhex("aabb")


def test_hex_to_buffer_invalid() -> None:
    client = _make_client()
    with pytest.raises(ValidationError, match="Expected hex-encoded"):
        client.hex_to_buffer("not-hex")


def test_build_and_open_cipher_envelope() -> None:
    client = _make_client()
    shared = os.urandom(32)
    envelope = client.build_cipher_envelope(
        {
            "sharedSecret": shared,
            "plaintext": "Hello, World!",
            "sessionId": "sess-1",
            "recipients": [{"uaid": "u-1"}],
        }
    )
    assert "ciphertext" in envelope
    assert "nonce" in envelope
    assert envelope["algorithm"] == "aes-256-gcm"

    decrypted = client.open_cipher_envelope(
        {
            "envelope": envelope,
            "sharedSecret": shared,
        }
    )
    assert decrypted == "Hello, World!"


# ── History / decryption ─────────────────────────────────────────────


def test_fetch_history_snapshot_text_response() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = "not-json"
    client = _make_client(transport)
    with pytest.raises(ParseError, match="Expected JSON response but got text"):
        client.fetch_history_snapshot("sess-1")


def test_attach_decrypted_history_no_decrypt() -> None:
    client = _make_client()
    snapshot = {"history": [{"content": "hi"}]}
    result = client.attach_decrypted_history("sess-1", snapshot)
    assert result == snapshot  # No decryption


def test_attach_decrypted_history_non_dict() -> None:
    client = _make_client()
    result = client.attach_decrypted_history("sess-1", [1, 2, 3])
    assert result == [1, 2, 3]


def test_attach_decrypted_history_with_decrypt() -> None:
    client = _make_client()
    shared = os.urandom(32)
    envelope = client.build_cipher_envelope(
        {
            "sharedSecret": shared,
            "plaintext": "secret message",
            "sessionId": "sess-1",
        }
    )
    snapshot = {
        "history": [
            {"content": "plain text"},
            {"cipherEnvelope": envelope},
        ],
    }
    client.register_conversation_context_for_encryption(
        {
            "sessionId": "sess-1",
            "sharedSecret": shared,
        }
    )
    result = client.attach_decrypted_history("sess-1", snapshot, {"decrypt": True})
    assert "decryptedHistory" in result
    assert len(result["decryptedHistory"]) == 2
    assert result["decryptedHistory"][0]["plaintext"] == "plain text"
    assert result["decryptedHistory"][1]["plaintext"] == "secret message"


def test_attach_decrypted_history_auto_decrypt() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    client = RegistryBrokerClient(
        config=SdkConfig.from_mapping({}),
        transport=transport,
        encryption_options={"autoDecryptHistory": True},
    )
    snapshot = {"history": [{"content": "hi"}]}
    client.register_conversation_context_for_encryption(
        {
            "sessionId": "sess-1",
            "sharedSecret": b"x" * 32,
        }
    )
    result = client.attach_decrypted_history("sess-1", snapshot)
    assert "decryptedHistory" in result


def test_resolve_decryption_context_from_options() -> None:
    client = _make_client()
    ctx = client.resolve_decryption_context("sess-1", {"sharedSecret": b"abc"})
    assert ctx is not None
    assert ctx["sessionId"] == "sess-1"


def test_resolve_decryption_context_no_context() -> None:
    client = _make_client()
    ctx = client.resolve_decryption_context("sess-1")
    assert ctx is None


def test_decrypt_history_entry_no_cipher() -> None:
    client = _make_client()
    result = client.decrypt_history_entry_from_context("sess-1", {"content": "plain"}, {})
    assert result == "plain"


def test_decrypt_history_entry_non_dict_envelope() -> None:
    client = _make_client()
    result = client.decrypt_history_entry_from_context(
        "sess-1", {"cipherEnvelope": "not-a-dict"}, {}
    )
    assert result is None


def test_decrypt_history_entry_bad_shared_secret() -> None:
    client = _make_client()
    result = client.decrypt_history_entry_from_context(
        "sess-1",
        {"cipherEnvelope": {"nonce": "x", "ciphertext": "y"}},
        {"sharedSecret": 12345},  # Not a string
    )
    assert result is None


# ── Chat / conversation ──────────────────────────────────────────────


def test_start_chat() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"sessionId": "sess-1"}
    client = _make_client(transport)
    result = client.start_chat(
        {
            "uaid": "u-1",
            "agentUrl": "https://agent.test",
            "auth": {"key": "val"},
            "historyTtlSeconds": 300,
            "senderUaid": "s-1",
        }
    )
    assert result["sessionId"] == "sess-1"
    assert result["mode"] == "plaintext"


def test_start_conversation() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"sessionId": "sess-1"}
    client = _make_client(transport)
    result = client.start_conversation({"uaid": "u-1"})
    assert result["mode"] == "plaintext"


def test_accept_conversation() -> None:
    client = _make_client()
    result = client.accept_conversation({"sessionId": "sess-1", "responderUaid": "r-1"})
    assert result["sessionId"] == "sess-1"
    assert result["mode"] == "plaintext"


def test_compact_history() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"ok": True}
    client = _make_client(transport)
    result = client.compact_history({"sessionId": "sess-1", "preserveEntries": 5})
    assert result == {"ok": True}


def test_end_session() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = None
    client = _make_client(transport)
    client.end_session("sess-1")


# ── parse_with_schema ────────────────────────────────────────────────


def test_parse_with_schema_pydantic() -> None:
    client = _make_client()
    result = client.parse_with_schema(
        {"results": [], "total": 0},
        SearchResponse,
        "test",
    )
    assert isinstance(result, SearchResponse)


def test_parse_with_schema_callable() -> None:
    client = _make_client()
    result = client.parse_with_schema(42, lambda v: v * 2, "test")
    assert result == 84


def test_parse_with_schema_callable_error() -> None:
    client = _make_client()
    with pytest.raises(ParseError, match="Failed to parse"):
        client.parse_with_schema(42, lambda v: (_ for _ in ()).throw(Exception("boom")), "test")


def test_parse_with_schema_raw() -> None:
    client = _make_client()
    result = client.parse_with_schema(42, "not-callable", "test")
    assert result == 42


# ── extract_insufficient_credits / auto_top_up ───────────────────────


def test_extract_insufficient_credits_402() -> None:
    client = _make_client()
    err = ApiError("insufficient", ErrorContext(status_code=402, body={"shortfallCredits": 10}))
    result = client.extract_insufficient_credits_details(err)
    assert result == {"shortfallCredits": 10}


def test_extract_insufficient_credits_not_402() -> None:
    client = _make_client()
    err = ApiError("other", ErrorContext(status_code=500))
    assert client.extract_insufficient_credits_details(err) is None


def test_extract_insufficient_credits_no_shortfall() -> None:
    client = _make_client()
    err = ApiError("insufficient", ErrorContext(status_code=402, body={"other": "val"}))
    assert client.extract_insufficient_credits_details(err) is None


def test_extract_insufficient_credits_non_api_error() -> None:
    client = _make_client()
    assert client.extract_insufficient_credits_details(Exception("x")) is None


def test_extract_insufficient_credits_non_dict_body() -> None:
    client = _make_client()
    err = ApiError("insufficient", ErrorContext(status_code=402, body="text"))
    assert client.extract_insufficient_credits_details(err) is None


def test_should_auto_top_up_history_true() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    client = RegistryBrokerClient(
        config=SdkConfig.from_mapping({}),
        transport=transport,
        history_auto_top_up={"accountId": "0.0.1", "privateKey": "pk"},
    )
    err = ApiError("insufficient", ErrorContext(status_code=402))
    assert client.should_auto_top_up_history({"historyTtlSeconds": 300}, err) is True


def test_should_auto_top_up_history_false_no_config() -> None:
    client = _make_client()
    err = ApiError("insufficient", ErrorContext(status_code=402))
    assert client.should_auto_top_up_history({"historyTtlSeconds": 300}, err) is False


def test_should_auto_top_up_history_false_no_ttl() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    client = RegistryBrokerClient(
        config=SdkConfig.from_mapping({}),
        transport=transport,
        history_auto_top_up={"accountId": "0.0.1"},
    )
    assert client.should_auto_top_up_history({}, None) is False


def test_execute_history_auto_top_up() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"ok": True}
    client = RegistryBrokerClient(
        config=SdkConfig.from_mapping({}),
        transport=transport,
        history_auto_top_up={"accountId": "0.0.1", "privateKey": "pk"},
    )
    client.execute_history_auto_top_up("test")
    transport.request_json.assert_called_once()


def test_execute_history_auto_top_up_no_config() -> None:
    client = _make_client()
    client.execute_history_auto_top_up("test")  # No-op


# ── bootstrap_encryption_options ─────────────────────────────────────


def test_bootstrap_encryption_options_none() -> None:
    client = _make_client()
    assert client.bootstrap_encryption_options(None) is None
    assert client.bootstrap_encryption_options({}) is None


def test_bootstrap_encryption_options_disabled() -> None:
    client = _make_client()
    assert client.bootstrap_encryption_options({"autoRegister": {"enabled": False}}) is None


def test_initialize_encryption_bootstrap() -> None:
    client = _make_client()
    client.initialize_encryption_bootstrap({"autoRegister": {"enabled": False}})


# ── __getattr__ ──────────────────────────────────────────────────────


def test_getattr_camel_alias() -> None:
    client = _make_client()
    # setApiKey is in _NON_OPERATION_CAMEL_ALIASES
    fn = client.setApiKey
    assert callable(fn)


def test_getattr_operation() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = _MOCK_STATS_RESPONSE
    client = _make_client(transport)
    fn = client.stats
    assert callable(fn)


def test_getattr_unknown_raises() -> None:
    client = _make_client()
    with pytest.raises(AttributeError):
        _ = client.totally_nonexistent_method_xyz


# ── close ────────────────────────────────────────────────────────────


def test_close() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    client = _make_client(transport)
    client.close()
    transport.close.assert_called_once()


# ── _ChatApi methods ─────────────────────────────────────────────────


def test_chat_api_methods() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"sessionId": "sess-1"}
    client = _make_client(transport)
    chat = client.chat

    # start
    result = chat.start({"uaid": "u-1"})
    assert result["mode"] == "plaintext"

    # create_session
    transport.request_json.return_value = {"sessionId": "sess-1"}
    result = chat.create_session({"uaid": "u-1"})
    assert isinstance(result, CreateSessionResponse)

    # send_message
    transport.request_json.return_value = {"messageId": "msg-1"}
    result = chat.send_message({"content": "hi"})
    assert isinstance(result, SendMessageResponse)

    # end_session
    transport.request_json.return_value = None
    chat.end_session("sess-1")

    # compact_history
    transport.request_json.return_value = {"ok": True}
    result = chat.compact_history({"sessionId": "sess-1"})

    # get_encryption_status
    transport.request_json.return_value = {"status": "active"}
    result = chat.get_encryption_status("sess-1")

    # submit_encryption_handshake
    transport.request_json.return_value = {"ok": True}
    result = chat.submit_encryption_handshake("sess-1", {"key": "val"})

    # start_conversation
    transport.request_json.return_value = {"sessionId": "sess-2"}
    result = chat.start_conversation({"uaid": "u-1"})

    # accept_conversation
    result = chat.accept_conversation({"sessionId": "sess-2"})

    # create_encrypted_session
    transport.request_json.return_value = {"sessionId": "sess-3"}
    result = chat.create_encrypted_session({"uaid": "u-1"})

    # accept_encrypted_session
    result = chat.accept_encrypted_session({"sessionId": "sess-3"})


# ── _EncryptionApi methods ───────────────────────────────────────────


def test_encryption_api_methods() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"ok": True}
    client = _make_client(transport)
    enc = client.encryption

    # register_key
    enc.register_key({"publicKey": "pk"})

    # generate_ephemeral_key_pair
    pair = enc.generate_ephemeral_key_pair()
    assert "publicKey" in pair

    # derive_shared_secret
    secret = enc.derive_shared_secret({"privateKey": "pk", "peerPublicKey": "peer"})
    assert isinstance(secret, bytes)

    # encrypt_cipher_envelope
    shared = os.urandom(32)
    envelope = enc.encrypt_cipher_envelope(
        {
            "sharedSecret": shared,
            "plaintext": "hi",
            "sessionId": "sess-1",
        }
    )
    assert "ciphertext" in envelope

    # decrypt_cipher_envelope
    plaintext = enc.decrypt_cipher_envelope(
        {
            "envelope": envelope,
            "sharedSecret": shared,
        }
    )
    assert plaintext == "hi"


def test_encryption_api_ensure_agent_key() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"ok": True}
    client = _make_client(transport)
    enc = client.encryption
    result = enc.ensure_agent_key({"uaid": "u-1", "keyType": "ed25519"})
    assert "publicKey" in result


# ── generate_encryption_key_pair ─────────────────────────────────────


def test_generate_encryption_key_pair() -> None:
    client = _make_client()
    pair = client.generate_encryption_key_pair()
    assert "privateKey" in pair
    assert "publicKey" in pair
    assert pair["envVar"] == "RB_ENCRYPTION_PRIVATE_KEY"


# ── _sign_ledger_challenge wrapper (lines 134-137) ───────────────────


def test_sync_sign_ledger_challenge_wrapper() -> None:
    """Cover the sync_client module-level wrapper that delegates to inscriber."""
    with patch(
        "standards_sdk_py.inscriber.client._sign_ledger_challenge",
        return_value=("sig-val", "pub-val"),
    ):
        sig, pub = _sync_sign_ledger_challenge("msg", "pk")
    assert sig == "sig-val"
    assert pub == "pub-val"


# ── initialize_agent (lines 244-251) ─────────────────────────────────


def test_initialize_agent() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"ok": True}
    with patch(
        "standards_sdk_py.registry_broker.sync_client.RegistryBrokerClient.__init__",
        return_value=None,
    ) as mock_init:
        mock_init.side_effect = lambda self=None, **kw: None
        with patch.object(RegistryBrokerClient, "__init__", lambda self, **kw: None):
            with patch.object(
                RegistryBrokerClient,
                "encryption",
                new_callable=lambda: property(
                    lambda self: MagicMock(
                        ensure_agent_key=MagicMock(return_value={"publicKey": "pk"})
                    )
                ),
            ):
                result = RegistryBrokerClient.initialize_agent({"uaid": "u-1"})
                assert "client" in result
                assert result["encryption"]["publicKey"] == "pk"


def test_initialize_agent_skip_encryption() -> None:
    with patch.object(RegistryBrokerClient, "__init__", lambda self, **kw: None):
        with patch.object(
            RegistryBrokerClient,
            "encryption",
            new_callable=lambda: property(lambda self: MagicMock()),
        ):
            result = RegistryBrokerClient.initialize_agent({"ensureEncryptionKey": False})
            assert result["encryption"] is None


# ── _ChatApi.get_history (line 157) ──────────────────────────────────


def test_chat_api_get_history() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"history": []}
    client = _make_client(transport)
    result = client.chat.get_history("sess-1", {"decrypt": False})
    assert "history" in result


# ── _call_operation_alias POST dict first positional (line 388) ──────


def test_alias_post_dict_body() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"ok": True}
    client = _make_client(transport)
    # send_message is POST, passing a dict as first positional should be used as body
    result = client._call_operation_alias("send_message", {"content": "hi"})
    assert result == {"ok": True}


# ── create_verification_challenge (line 502) ─────────────────────────


def test_create_verification_challenge() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"challengeId": "ch-1"}
    client = _make_client(transport)
    result = client.create_verification_challenge("u-1")
    assert result == {"challengeId": "ch-1"}


# ── verify_sender_ownership (line 505) ───────────────────────────────


def test_verify_sender_ownership() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"verified": True}
    client = _make_client(transport)
    result = client.verify_sender_ownership("u-1")
    assert result == {"verified": True}


# ── authenticate_with_ledger with expiresInMinutes / signatureKind ───


def test_authenticate_with_ledger_expires_and_signature_kind() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.side_effect = [
        {"challengeId": "ch-1", "message": "sign me"},
        {"key": "api-key", "accountId": "0.0.1"},
    ]
    client = _make_client(transport)

    def signer(msg: str) -> dict[str, str]:
        return {"signature": "sig", "signatureKind": "ed25519", "publicKey": "pk"}

    result = client.authenticate_with_ledger(
        {
            "accountId": "0.0.1",
            "network": "testnet",
            "sign": signer,
            "expiresInMinutes": 30,
        }
    )
    # The payload should now include publicKey and expiresInMinutes
    assert isinstance(result, dict)


# ── authenticate_with_ledger missing fields (line 532) ───────────────


def test_authenticate_with_ledger_missing_fields() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"challengeId": "ch-1"}  # no "message"
    client = _make_client(transport)
    with pytest.raises(ValidationError, match="missing required fields"):
        client.authenticate_with_ledger({"accountId": "0.0.1", "network": "testnet"})


# ── fetch_history_snapshot JSON success (line 640) ───────────────────


def test_fetch_history_snapshot_json() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"history": [{"content": "hi"}]}
    client = _make_client(transport)
    result = client.fetch_history_snapshot("sess-1")
    assert "history" in result


# ── attach_decrypted_history non-dict entry skip (line 668) ──────────


def test_attach_decrypted_non_dict_entries_skipped() -> None:
    client = _make_client()
    shared = os.urandom(32)
    client.register_conversation_context_for_encryption(
        {
            "sessionId": "s",
            "sharedSecret": shared,
        }
    )
    snapshot = {"history": ["not-a-dict", {"content": "hi"}, 42]}
    result = client.attach_decrypted_history("s", snapshot, {"decrypt": True})
    # Only dict entries are processed
    assert len(result["decryptedHistory"]) == 1


# ── register_conversation_context_for_encryption with identity (681) ─


def test_register_context_with_identity() -> None:
    client = _make_client()
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


# ── attach_decrypted_history: non-list history (line 661) ────────────


def test_attach_decrypted_non_list_history() -> None:
    client = _make_client()
    snapshot = {"history": "not-a-list"}
    result = client.attach_decrypted_history("sess-1", snapshot, {"decrypt": True})
    assert result == snapshot  # returned as-is


# ── attach_decrypted_history: no context (line 664) ──────────────────


def test_attach_decrypted_no_context() -> None:
    client = _make_client()
    snapshot = {"history": [{"content": "hi"}]}
    # decrypt=True but no context registered
    result = client.attach_decrypted_history("sess-1", snapshot, {"decrypt": True})
    assert result == snapshot  # returned as-is since context is None


# ── decrypt_history_entry exception (lines 724-725) ──────────────────


def test_decrypt_entry_exception_returns_none() -> None:
    client = _make_client()
    bad_envelope = {"nonce": "invalid-base64!!!", "ciphertext": "also-invalid!!!"}
    ctx = {
        "sharedSecret": base64.b64encode(b"x" * 32).decode(),
    }
    result = client.decrypt_history_entry_from_context("s", {"cipherEnvelope": bad_envelope}, ctx)
    assert result is None


# ── delay > 0 (line 821) ────────────────────────────────────────────


def test_delay_positive() -> None:
    client = _make_client()
    with patch("standards_sdk_py.registry_broker.sync_client.sleep") as mock_sleep:
        client.delay(100)
        mock_sleep.assert_called_once_with(0.1)


# ── _parse_model text / invalid (lines 940-954) ─────────────────────


def test_parse_model_text() -> None:
    with pytest.raises(ParseError, match="Expected JSON"):
        RegistryBrokerClient._parse_model("text", SearchResponse)


def test_parse_model_invalid() -> None:
    with pytest.raises(ParseError, match="Failed to validate"):
        # CreateSessionResponse requires sessionId; missing it triggers validation error
        RegistryBrokerClient._parse_model({"bad_field": True}, CreateSessionResponse)


# ── __getattr__ snake_name NON_OPERATION_CAMEL alias (line 950) ──────


def test_getattr_camel_from_snake() -> None:
    """Test __getattr__ converting snake_name back to camel for non-operation aliases."""
    client = _make_client()
    # Try a camel name that needs to be snake-ified to match
    # _NON_OPERATION_CAMEL_ALIASES has keys like "setApiKey" -> "set_api_key"
    fn = client.setLedgerApiKey
    assert callable(fn)


def test_getattr_operation_by_camel() -> None:
    """__getattr__ should match camelCase op names by converting to snake_case."""
    client = _make_client()
    # "createSession" -> snake "create_session" which is in REGISTRY_BROKER_OPERATIONS
    fn = client.createSession
    assert callable(fn)


# ── bootstrap_encryption_options enabled (line 940) ──────────────────


def test_bootstrap_encryption_options_enabled() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {}
    transport.request_json.return_value = {"ok": True}
    client = _make_client(transport)
    result = client.bootstrap_encryption_options({"autoRegister": {"enabled": True, "uaid": "u-1"}})
    assert result is not None


# ── _fill_path / _query_from_values helper ───────────────────────────


def test_fill_path() -> None:
    assert _fill_path("/agents/{uaid}/feedback", {"uaid": "u-1"}) == "/agents/u-1/feedback"
    assert _fill_path("/stats", None) == "/stats"


def test_query_from_values() -> None:
    assert _query_from_values(None) is None
    result = _query_from_values({"q": "test", "limit": 10})
    # int/float/bool/str values are kept as-is
    assert result == {"q": "test", "limit": 10}
    result2 = _query_from_values({"tags": ["a", "b"]})
    assert result2 == {"tags": "['a', 'b']"}
    # None values are filtered out
    assert _query_from_values({"a": None}) is None
