"""Tests for the expanded mirror node client (mirror/client.py)."""

from __future__ import annotations

import base64
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from standards_sdk_py.exceptions import ApiError, ErrorContext, TransportError
from standards_sdk_py.mirror.client import (
    HederaMirrorNode,
    MirrorNodeClient,
    _camel_to_snake,
    _decode_base64_message,
    _next_path_from_links,
    _to_query,
)
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.http import SyncHttpTransport

# ── Helper ───────────────────────────────────────────────────────────


def _make_mirror(mock_transport: MagicMock | None = None) -> MirrorNodeClient:
    transport = mock_transport or MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test/api/v1"
    transport.headers = {}
    return MirrorNodeClient(config=SdkConfig.from_mapping({}), transport=transport)


# ── Utility functions ────────────────────────────────────────────────


def test_camel_to_snake() -> None:
    assert _camel_to_snake("getAccountBalance") == "get_account_balance"
    assert _camel_to_snake("getNFTOwnership") == "get_nft_ownership"


def test_to_query_none_values() -> None:
    assert _to_query({"a": None, "b": None}) is None


def test_to_query_mixed() -> None:
    result = _to_query({"a": 1, "b": "x", "c": True, "d": None})
    assert result == {"a": 1, "b": "x", "c": True}


def test_to_query_datetime() -> None:
    dt = datetime(2025, 1, 1, 12, 0, 0)
    result = _to_query({"ts": dt})
    assert result is not None
    assert result["ts"] == dt.isoformat()


def test_to_query_fallback_str() -> None:
    result = _to_query({"x": [1, 2]})
    assert result == {"x": "[1, 2]"}


def test_next_path_from_links_none() -> None:
    assert _next_path_from_links({}) is None
    assert _next_path_from_links({"links": "not-dict"}) is None
    assert _next_path_from_links({"links": {"next": ""}}) is None
    assert _next_path_from_links({"links": {"next": "  "}}) is None


def test_next_path_from_links_full_url() -> None:
    result = _next_path_from_links(
        {"links": {"next": "https://mirror.test/api/v1/tokens?limit=25&page=2"}}
    )
    assert result == "/api/v1/tokens?limit=25&page=2"


def test_next_path_from_links_relative() -> None:
    result = _next_path_from_links({"links": {"next": "/api/v1/tokens?page=2"}})
    assert result == "/api/v1/tokens?page=2"


def test_decode_base64_message() -> None:
    encoded = base64.b64encode(b"hello world").decode()
    assert _decode_base64_message(encoded) == "hello world"
    assert _decode_base64_message(42) is None
    assert _decode_base64_message("!!!invalid-b64!!!") is None


# ── MirrorNodeClient init ────────────────────────────────────────────


def test_mirror_init() -> None:
    client = _make_mirror()
    assert isinstance(client, MirrorNodeClient)
    assert HederaMirrorNode is MirrorNodeClient


# ── configure_retry ──────────────────────────────────────────────────


def test_configure_retry() -> None:
    client = _make_mirror()
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


def test_configure_retry_ignores_invalid() -> None:
    client = _make_mirror()
    original = (client._max_retries, client._initial_delay_ms)
    client.configure_retry({"maxRetries": -1, "initialDelayMs": "bad"})
    assert (client._max_retries, client._initial_delay_ms) == original


# ── configure_mirror_node ────────────────────────────────────────────


def test_configure_mirror_node_custom_url() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://old.test"
    transport.headers = {}
    client = _make_mirror(transport)
    client.configure_mirror_node({"customUrl": "https://new.test/"})
    assert transport.base_url == "https://new.test"


def test_configure_mirror_node_headers() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {"existing": "val"}
    client = MirrorNodeClient(config=SdkConfig.from_mapping({}), transport=transport)
    client.configure_mirror_node({"headers": {"x-custom": "value"}})
    # configure_mirror_node sets transport.headers to a new merged dict
    assert transport.headers["x-custom"] == "value"
    assert transport.headers["existing"] == "val"


def test_configure_mirror_node_api_key() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    client = _make_mirror(transport)
    client.configure_mirror_node({"apiKey": "my-key"})
    assert transport.headers["authorization"] == "Bearer my-key"


# ── _request_json / retry logic ──────────────────────────────────────


def test_request_json_success() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"data": True}
    client = _make_mirror(transport)
    result = client._request_json("/test")
    assert result == {"data": True}


def test_request_json_retry_on_transport_error() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.side_effect = [
        TransportError("timeout", ErrorContext()),
        {"data": True},
    ]
    client = _make_mirror(transport)
    with patch("standards_sdk_py.mirror.client.sleep"):
        result = client._request_json("/test")
    assert result == {"data": True}


def test_request_json_retry_on_429() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.side_effect = [
        ApiError("rate limit", ErrorContext(status_code=429)),
        {"data": True},
    ]
    client = _make_mirror(transport)
    with patch("standards_sdk_py.mirror.client.sleep"):
        result = client._request_json("/test")
    assert result == {"data": True}


def test_request_json_no_retry_on_404() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.side_effect = ApiError("not found", ErrorContext(status_code=404))
    client = _make_mirror(transport)
    with pytest.raises(ApiError, match="not found"):
        client._request_json("/test")
    assert transport.request_json.call_count == 1


def test_request_json_retries_exhausted() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.side_effect = TransportError("timeout", ErrorContext())
    client = _make_mirror(transport)
    client._max_retries = 2
    with patch("standards_sdk_py.mirror.client.sleep"):
        with pytest.raises(TransportError, match="timeout"):
            client._request_json("/test")


# ── _collect_items ────────────────────────────────────────────────────


def test_collect_items_pagination() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.side_effect = [
        {"tokens": [{"id": "1"}], "links": {"next": "/api/v1/tokens?page=2"}},
        {"tokens": [{"id": "2"}], "links": {}},
    ]
    client = _make_mirror(transport)
    items = client._collect_items("/tokens", query=None, item_key="tokens")
    assert len(items) == 2


def test_collect_items_non_dict_response() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = "not-a-dict"
    client = _make_mirror(transport)
    items = client._collect_items("/tokens", query=None, item_key="tokens")
    assert items == []


# ── Account methods ──────────────────────────────────────────────────


def test_request_account() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"account": "0.0.1", "balance": {"balance": 100}}
    client = _make_mirror(transport)
    assert client.request_account("0.0.1")["account"] == "0.0.1"


def test_request_account_non_dict() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = "not-dict"
    client = _make_mirror(transport)
    assert client.request_account("0.0.1") == {}


def test_get_public_key() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"key": {"key": "3030..."}}
    client = _make_mirror(transport)
    assert client.get_public_key("0.0.1") == "3030..."


def test_get_public_key_missing() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"key": {}}
    client = _make_mirror(transport)
    assert client.get_public_key("0.0.1") is None


def test_get_account_memo() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"memo": "my-memo"}
    client = _make_mirror(transport)
    assert client.get_account_memo("0.0.1") == "my-memo"


def test_get_account_memo_not_string() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"memo": 123}
    client = _make_mirror(transport)
    assert client.get_account_memo("0.0.1") is None


def test_get_account_balance() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"balance": {"balance": 50000000}}
    client = _make_mirror(transport)
    assert client.get_account_balance("0.0.1") == 50000000.0


def test_get_account_balance_missing() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"balance": {}}
    client = _make_mirror(transport)
    assert client.get_account_balance("0.0.1") is None


# ── Topic methods ────────────────────────────────────────────────────


def test_get_topic_info() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"topic_id": "0.0.100"}
    client = _make_mirror(transport)
    assert client.get_topic_info("0.0.100")["topic_id"] == "0.0.100"


def test_get_topic_fees() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"custom_fees": {"fee": 1}}
    client = _make_mirror(transport)
    assert client.get_topic_fees("0.0.100") == {"fee": 1}


def test_get_topic_fees_none() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {}
    client = _make_mirror(transport)
    assert client.get_topic_fees("0.0.100") is None


def test_get_topic_messages() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"messages": []}
    client = _make_mirror(transport)
    result = client.get_topic_messages("0.0.100", limit=10)
    assert result.messages == []


def test_get_topic_messages_by_filter() -> None:
    msg_b64 = base64.b64encode(b"hello").decode()
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {
        "messages": [
            {
                "consensus_timestamp": "1.0",
                "sequence_number": 1,
                "running_hash": "h",
                "message": msg_b64,
            },
        ]
    }
    client = _make_mirror(transport)
    result = client.get_topic_messages_by_filter(
        "0.0.100", {"limit": 1, "order": "asc", "sequenceNumber": 1}
    )
    assert len(result) == 1
    assert result[0]["message"] == "hello"


# ── HBAR / Token / NFT ──────────────────────────────────────────────


def test_get_hbar_price() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {
        "current_rate": {"cent_equivalent": 1200, "hbar_equivalent": 100},
    }
    client = _make_mirror(transport)
    price = client.get_hbar_price("2025-01-01")
    assert price == 0.12


def test_get_hbar_price_missing_rate() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {}
    client = _make_mirror(transport)
    assert client.get_hbar_price("2025-01-01") is None


def test_get_hbar_price_non_dict() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = "not-dict"
    client = _make_mirror(transport)
    assert client.get_hbar_price("2025-01-01") is None


def test_get_hbar_price_zero_hbar() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {
        "current_rate": {"cent_equivalent": 100, "hbar_equivalent": 0},
    }
    client = _make_mirror(transport)
    assert client.get_hbar_price("2025-01-01") is None


def test_get_hbar_price_datetime() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {
        "current_rate": {"cent_equivalent": 500, "hbar_equivalent": 50},
    }
    client = _make_mirror(transport)
    price = client.get_hbar_price(datetime(2025, 1, 1))
    assert price == 0.1


def test_get_token_info() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"token_id": "0.0.42"}
    client = _make_mirror(transport)
    assert client.get_token_info("0.0.42")["token_id"] == "0.0.42"


def test_get_nft_info() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"account_id": "0.0.1"}
    client = _make_mirror(transport)
    assert client.get_nft_info("0.0.42", 1)["account_id"] == "0.0.1"


def test_validate_nft_ownership_match() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"account_id": "0.0.1"}
    client = _make_mirror(transport)
    assert client.validate_nft_ownership("0.0.1", "0.0.42", 1) == {"account_id": "0.0.1"}


def test_validate_nft_ownership_no_match() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"account_id": "0.0.2"}
    client = _make_mirror(transport)
    assert client.validate_nft_ownership("0.0.1", "0.0.42", 1) is None


# ── Transaction / Schedule methods ───────────────────────────────────


def test_get_transaction_with_list() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"transactions": [{"id": "tx-1", "result": "OK"}]}
    client = _make_mirror(transport)
    assert client.get_transaction("tx-1")["id"] == "tx-1"


def test_get_transaction_no_list() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"id": "tx-1"}
    client = _make_mirror(transport)
    assert client.get_transaction("tx-1") == {"id": "tx-1"}


def test_get_transaction_non_dict() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = "not-dict"
    client = _make_mirror(transport)
    assert client.get_transaction("tx-1") is None


def test_get_transaction_by_timestamp() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"transactions": [{"id": "tx-1"}]}
    client = _make_mirror(transport)
    result = client.get_transaction_by_timestamp("1234567890.000")
    assert len(result) == 1


def test_get_transaction_by_timestamp_empty() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {}
    client = _make_mirror(transport)
    assert client.get_transaction_by_timestamp("1234567890.000") == []


def test_get_schedule_info() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"schedule_id": "0.0.5"}
    client = _make_mirror(transport)
    assert client.get_schedule_info("0.0.5")["schedule_id"] == "0.0.5"


def test_get_scheduled_transaction_status_executed() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"executed_timestamp": "1234567890.000", "deleted": False}
    client = _make_mirror(transport)
    result = client.get_scheduled_transaction_status("0.0.5")
    assert result["executed"] is True
    assert result["deleted"] is False


def test_get_scheduled_transaction_status_not_executed() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"deleted": True}
    client = _make_mirror(transport)
    result = client.get_scheduled_transaction_status("0.0.5")
    assert result["executed"] is False
    assert result["deleted"] is True


# ── check_key_list_access ────────────────────────────────────────────


def test_check_key_list_access_match() -> None:
    client = _make_mirror()
    assert client.check_key_list_access("3030abc123", "abc123") is True


def test_check_key_list_access_no_match() -> None:
    client = _make_mirror()
    assert client.check_key_list_access("3030abc123", "xyz999") is False


def test_check_key_list_access_bytes() -> None:
    client = _make_mirror()
    assert client.check_key_list_access(b"\xab\xc1\x23", "abc123") is True


# ── Contract methods ─────────────────────────────────────────────────


def test_read_smart_contract_query() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"result": "0x1234"}
    client = _make_mirror(transport)
    result = client.read_smart_contract_query("0.0.10", "0xaabbccdd", "0.0.1")
    assert result["result"] == "0x1234"


def test_read_smart_contract_query_with_options() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"result": "0x"}
    client = _make_mirror(transport)
    result = client.read_smart_contract_query("0.0.10", "0xaabb", "0.0.1", {"gas": 500000})
    assert result is not None


def test_get_block() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"number": 42}
    client = _make_mirror(transport)
    assert client.get_block("42")["number"] == 42


def test_get_contract() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"contract_id": "0.0.10"}
    client = _make_mirror(transport)
    assert client.get_contract("0.0.10")["contract_id"] == "0.0.10"


def test_get_contract_result() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"result": "OK"}
    client = _make_mirror(transport)
    assert client.get_contract_result("tx-hash")["result"] == "OK"


def test_get_opcode_traces() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"opcodes": []}
    client = _make_mirror(transport)
    assert client.get_opcode_traces("tx-hash") is not None


# ── Collection methods ───────────────────────────────────────────────


def test_get_account_tokens() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"tokens": [{"token_id": "0.0.42"}]}
    client = _make_mirror(transport)
    result = client.get_account_tokens("0.0.1")
    assert len(result) == 1


def test_get_account_nfts() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"nfts": [{"serial_number": 1}]}
    client = _make_mirror(transport)
    result = client.get_account_nfts("0.0.1", token_id="0.0.42")
    assert len(result) == 1


def test_get_blocks() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"blocks": [{"number": 1}]}
    client = _make_mirror(transport)
    result = client.get_blocks()
    assert len(result) == 1


def test_get_contracts() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"contracts": [{"id": "0.0.10"}]}
    client = _make_mirror(transport)
    assert len(client.get_contracts()) == 1


def test_get_contract_results() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"results": [{"hash": "0x"}]}
    client = _make_mirror(transport)
    assert len(client.get_contract_results()) == 1


def test_get_contract_results_by_contract() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"results": [{"hash": "0x"}]}
    client = _make_mirror(transport)
    assert len(client.get_contract_results_by_contract("0.0.10")) == 1


def test_get_contract_state() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"state": [{"slot": "0x"}]}
    client = _make_mirror(transport)
    assert len(client.get_contract_state("0.0.10")) == 1


def test_get_contract_actions() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"actions": [{"type": "call"}]}
    client = _make_mirror(transport)
    assert len(client.get_contract_actions("tx-1")) == 1


def test_get_contract_logs() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"logs": [{"data": "0x"}]}
    client = _make_mirror(transport)
    assert len(client.get_contract_logs()) == 1


def test_get_contract_logs_by_contract() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"logs": [{"data": "0x"}]}
    client = _make_mirror(transport)
    assert len(client.get_contract_logs_by_contract("0.0.10")) == 1


def test_get_nfts_by_token() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"nfts": [{"serial_number": 1}]}
    client = _make_mirror(transport)
    assert len(client.get_nfts_by_token("0.0.42")) == 1


# ── Network methods ─────────────────────────────────────────────────


def test_get_network_info() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"nodes": []}
    client = _make_mirror(transport)
    assert client.get_network_info() is not None


def test_get_network_fees() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"fees": []}
    client = _make_mirror(transport)
    assert client.get_network_fees() is not None


def test_get_network_supply() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"total_supply": 50000000000}
    client = _make_mirror(transport)
    assert client.get_network_supply() is not None


def test_get_network_stake() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"stake_total": 100}
    client = _make_mirror(transport)
    assert client.get_network_stake() is not None


# ── Airdrop methods ──────────────────────────────────────────────────


def test_get_outstanding_airdrops() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"airdrops": [{"token_id": "0.0.42"}]}
    client = _make_mirror(transport)
    assert len(client.get_outstanding_token_airdrops("0.0.1")) == 1


def test_get_pending_airdrops() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    transport.request_json.return_value = {"airdrops": [{"token_id": "0.0.42"}]}
    client = _make_mirror(transport)
    assert len(client.get_pending_token_airdrops("0.0.1")) == 1


# ── get_base_url / close ────────────────────────────────────────────


def test_get_base_url() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test/api/v1"
    transport.headers = {}
    client = _make_mirror(transport)
    assert client.get_base_url() == "https://mirror.test/api/v1"


def test_close() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://mirror.test"
    transport.headers = {}
    client = _make_mirror(transport)
    client.close()
    transport.close.assert_called_once()


# ── CamelCase aliases ────────────────────────────────────────────────


def test_camel_aliases_exist() -> None:
    client = _make_mirror()
    for camel_name in ("getAccountBalance", "getTopicInfo", "getPublicKey"):
        assert hasattr(client, camel_name), f"Missing camel alias: {camel_name}"
