"""Tests for inscriber transient error helpers, retries, and remaining paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from standards_sdk_py.exceptions import (
    ApiError,
    ErrorContext,
    ParseError,
    TransportError,
    ValidationError,
)
from standards_sdk_py.inscriber.client import (
    AsyncBrokerInscriberClient,
    BrokerInscriberClient,
    BrokerQuoteRequest,
    _is_transient_registry_error,
    _normalize_ledger_network,
    _request_registry_json_with_retry,
    authenticate_with_ledger_credentials,
)
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport

# ── _is_transient_registry_error ─────────────────────────────────────


def test_transient_transport_error() -> None:
    assert _is_transient_registry_error(TransportError("timeout", ErrorContext())) is True


def test_transient_parse_error() -> None:
    assert _is_transient_registry_error(ParseError("bad json", ErrorContext())) is True


def test_transient_api_error_502() -> None:
    err = ApiError("bad gw", ErrorContext(status_code=502))
    assert _is_transient_registry_error(err) is True


def test_transient_api_error_503() -> None:
    err = ApiError("unavail", ErrorContext(status_code=503))
    assert _is_transient_registry_error(err) is True


def test_transient_api_error_504() -> None:
    err = ApiError("gw timeout", ErrorContext(status_code=504))
    assert _is_transient_registry_error(err) is True


def test_non_transient_api_error_400() -> None:
    err = ApiError("bad request", ErrorContext(status_code=400))
    assert _is_transient_registry_error(err) is False


def test_non_transient_api_error_401() -> None:
    err = ApiError("unauthorized", ErrorContext(status_code=401))
    assert _is_transient_registry_error(err) is False


def test_non_transient_generic_error() -> None:
    assert _is_transient_registry_error(Exception("generic")) is False


def test_non_transient_value_error() -> None:
    assert _is_transient_registry_error(ValueError("bad value")) is False


# ── _request_registry_json_with_retry ────────────────────────────────


def test_retry_succeeds_first_try() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.request_json.return_value = {"ok": True}
    result = _request_registry_json_with_retry(transport, "POST", "/test")
    assert result == {"ok": True}
    transport.request_json.assert_called_once()


def test_retry_succeeds_after_transient() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.request_json.side_effect = [
        TransportError("timeout", ErrorContext()),
        {"ok": True},
    ]
    with patch("standards_sdk_py.inscriber.client.sleep"):
        result = _request_registry_json_with_retry(
            transport, "POST", "/test", retry_count=3, retry_delay_ms=10
        )
    assert result == {"ok": True}


def test_retry_exhausted_raises() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.request_json.side_effect = TransportError("timeout", ErrorContext())
    with patch("standards_sdk_py.inscriber.client.sleep"):
        with pytest.raises(TransportError, match="timeout"):
            _request_registry_json_with_retry(
                transport, "POST", "/test", retry_count=2, retry_delay_ms=10
            )


def test_retry_non_transient_raises_immediately() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.request_json.side_effect = ApiError("not found", ErrorContext(status_code=404))
    with pytest.raises(ApiError, match="not found"):
        _request_registry_json_with_retry(transport, "POST", "/test", retry_count=3)
    assert transport.request_json.call_count == 1


def test_retry_with_body() -> None:
    transport = MagicMock(spec=SyncHttpTransport)
    transport.request_json.return_value = {"ok": True}
    result = _request_registry_json_with_retry(transport, "POST", "/test", body={"key": "val"})
    assert result == {"ok": True}
    transport.request_json.assert_called_once_with("POST", "/test", body={"key": "val"})


# ── _normalize_ledger_network ────────────────────────────────────────


def test_normalize_ledger_network_mainnet() -> None:
    assert _normalize_ledger_network("mainnet") == "mainnet"


def test_normalize_ledger_network_testnet() -> None:
    assert _normalize_ledger_network("testnet") == "testnet"


def test_normalize_ledger_network_hedera_mainnet() -> None:
    assert _normalize_ledger_network("hedera-mainnet") == "mainnet"


def test_normalize_ledger_network_hedera_testnet() -> None:
    assert _normalize_ledger_network("hedera-testnet") == "testnet"


def test_normalize_ledger_network_passthrough() -> None:
    assert _normalize_ledger_network("customnet") == "customnet"


# ── wait_for_job transient error retry ───────────────────────────────


def test_sync_wait_for_job_transient_retry() -> None:
    """wait_for_job should retry on transient transport errors."""
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {"x-api-key": "k"}
    # First call raises transient, second succeeds
    transport.request_json.side_effect = [
        TransportError("timeout", ErrorContext()),
        {"jobId": "j-1", "status": "completed", "topicId": "0.0.1"},
    ]
    client = BrokerInscriberClient(api_key="k", transport=transport)
    with patch("standards_sdk_py.inscriber.client.sleep"):
        job = client.wait_for_job("j-1", timeout_ms=30000, poll_interval_ms=10)
    assert job.status == "completed"


def test_sync_wait_for_job_non_transient_raises() -> None:
    """wait_for_job should immediately raise on non-transient errors."""
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {"x-api-key": "k"}
    transport.request_json.side_effect = ApiError("forbidden", ErrorContext(status_code=403))
    client = BrokerInscriberClient(api_key="k", transport=transport)
    with pytest.raises(ApiError, match="forbidden"):
        client.wait_for_job("j-1", timeout_ms=30000, poll_interval_ms=10)


# ── inscribe_and_wait retry logic ────────────────────────────────────


def test_sync_inscribe_and_wait_transient_retry() -> None:
    """inscribe_and_wait retries create_job on transient errors."""
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {"x-api-key": "k"}
    # First create_job fails with transient, second succeeds, then get_job completes
    transport.request_json.side_effect = [
        TransportError("timeout", ErrorContext()),
        {"jobId": "j-1", "status": "pending"},
        {"jobId": "j-1", "status": "completed", "topicId": "0.0.1"},
    ]
    client = BrokerInscriberClient(api_key="k", transport=transport)
    payload = BrokerQuoteRequest(inputType="url", mode="file", url="https://example.test/f")
    with patch("standards_sdk_py.inscriber.client.sleep"):
        result = client.inscribe_and_wait(payload, timeout_ms=30000, poll_interval_ms=10)
    assert result.confirmed is True


def test_sync_inscribe_and_wait_non_transient_raises() -> None:
    """inscribe_and_wait should not retry non-transient errors."""
    transport = MagicMock(spec=SyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {"x-api-key": "k"}
    transport.request_json.side_effect = ApiError("bad request", ErrorContext(status_code=400))
    client = BrokerInscriberClient(api_key="k", transport=transport)
    payload = BrokerQuoteRequest(inputType="url", mode="file", url="https://example.test/f")
    with pytest.raises(ApiError, match="bad request"):
        client.inscribe_and_wait(payload, timeout_ms=30000, poll_interval_ms=10)


# ── Async wait_for_job / inscribe_and_wait transient retry ───────────


@pytest.mark.asyncio
async def test_async_wait_for_job_transient_retry() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {"x-api-key": "k"}
    transport.request_json = AsyncMock(
        side_effect=[
            TransportError("timeout", ErrorContext()),
            {"jobId": "j-1", "status": "completed"},
        ]
    )
    client = AsyncBrokerInscriberClient(api_key="k", transport=transport)
    with patch("standards_sdk_py.inscriber.client.asyncio") as mock_asyncio:
        mock_asyncio.sleep = AsyncMock()
        job = await client.wait_for_job("j-1", timeout_ms=30000, poll_interval_ms=10)
    assert job.status == "completed"


@pytest.mark.asyncio
async def test_async_wait_for_job_non_transient() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {"x-api-key": "k"}
    transport.request_json = AsyncMock(
        side_effect=ApiError("forbidden", ErrorContext(status_code=403))
    )
    client = AsyncBrokerInscriberClient(api_key="k", transport=transport)
    with pytest.raises(ApiError, match="forbidden"):
        await client.wait_for_job("j-1", timeout_ms=30000, poll_interval_ms=10)


@pytest.mark.asyncio
async def test_async_inscribe_and_wait_transient_retry() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {"x-api-key": "k"}
    transport.request_json = AsyncMock(
        side_effect=[
            TransportError("timeout", ErrorContext()),
            {"jobId": "j-1", "status": "pending"},
            {"jobId": "j-1", "status": "completed"},
        ]
    )
    client = AsyncBrokerInscriberClient(api_key="k", transport=transport)
    payload = BrokerQuoteRequest(inputType="url", mode="file", url="https://example.test/f")
    with patch("standards_sdk_py.inscriber.client.asyncio") as mock_asyncio:
        mock_asyncio.sleep = AsyncMock()
        result = await client.inscribe_and_wait(payload, timeout_ms=30000, poll_interval_ms=10)
    assert result.confirmed is True


@pytest.mark.asyncio
async def test_async_wait_for_job_failed_no_error() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {"x-api-key": "k"}
    transport.request_json = AsyncMock(return_value={"jobId": "j-1", "status": "failed"})
    client = AsyncBrokerInscriberClient(api_key="k", transport=transport)
    with pytest.raises(ValidationError, match="inscription failed"):
        await client.wait_for_job("j-1", timeout_ms=30000, poll_interval_ms=10)


@pytest.mark.asyncio
async def test_async_inscribe_and_wait_non_transient() -> None:
    transport = MagicMock(spec=AsyncHttpTransport)
    transport.base_url = "https://example.test"
    transport.headers = {"x-api-key": "k"}
    transport.request_json = AsyncMock(side_effect=ApiError("bad", ErrorContext(status_code=400)))
    client = AsyncBrokerInscriberClient(api_key="k", transport=transport)
    payload = BrokerQuoteRequest(inputType="url", mode="file", url="https://example.test/f")
    with pytest.raises(ApiError, match="bad"):
        await client.inscribe_and_wait(payload, timeout_ms=30000, poll_interval_ms=10)


# ── authenticate_with_ledger_credentials module-level function ───────


def test_authenticate_with_ledger_credentials_missing_account_id() -> None:
    with pytest.raises(ValidationError, match="account_id is required"):
        authenticate_with_ledger_credentials(
            base_url="https://example.test",
            account_id="  ",
            private_key="pk",
        )


def test_authenticate_with_ledger_credentials_missing_key() -> None:
    with pytest.raises(ValidationError, match="private_key is required"):
        authenticate_with_ledger_credentials(
            base_url="https://example.test",
            account_id="0.0.1",
            private_key="  ",
        )
