"""Tests for new top-level inscriber convenience functions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from standards_sdk_py.inscriber.client import (
    InscribeViaRegistryBrokerOptions,
    InscriptionInput,
    generate_quote,
    get_registry_broker_quote,
    inscribe,
    inscribe_via_registry_broker,
    inscribe_with_signer,
    retrieve_inscription,
    wait_for_inscription_confirmation,
)


def _input() -> InscriptionInput:
    return InscriptionInput(type="url", url="https://example.com/test.txt")


def _options() -> InscribeViaRegistryBrokerOptions:
    return InscribeViaRegistryBrokerOptions(
        base_url="https://broker.test",
        api_key="tok",
    )


def test_get_registry_broker_quote() -> None:
    with patch(
        "standards_sdk_py.inscriber.client.InscriberClient.get_registry_broker_quote"
    ) as mock_fn:
        mock_fn.return_value = MagicMock()
        result = get_registry_broker_quote(_input(), _options())
        mock_fn.assert_called_once()
        assert result is not None


def test_inscribe_via_registry_broker() -> None:
    with patch(
        "standards_sdk_py.inscriber.client.InscriberClient.inscribe_via_registry_broker"
    ) as mock_fn:
        mock_fn.return_value = MagicMock()
        inscribe_via_registry_broker(_input(), _options())
        mock_fn.assert_called_once()


def test_inscribe_delegates() -> None:
    with patch("standards_sdk_py.inscriber.client.inscribe_via_registry_broker") as mock_fn:
        mock_fn.return_value = MagicMock()
        inscribe(_input(), _options())
        mock_fn.assert_called_once()


def test_inscribe_with_signer_ignores_signer() -> None:
    with patch("standards_sdk_py.inscriber.client.inscribe_via_registry_broker") as mock_fn:
        mock_fn.return_value = MagicMock()
        inscribe_with_signer(_input(), _options(), signer="fake")
        mock_fn.assert_called_once()


def test_retrieve_inscription() -> None:
    with patch("standards_sdk_py.inscriber.client.BrokerInscriberClient.get_job") as mock_fn:
        mock_fn.return_value = MagicMock()
        retrieve_inscription("job-1", _options())
        mock_fn.assert_called_once_with("job-1")


def test_wait_for_inscription_confirmation() -> None:
    mock_job = MagicMock()
    mock_job.status = "completed"
    mock_job.hrl = "hrl://test"
    mock_job.topic_id = "0.0.1"
    mock_job.network = "testnet"
    mock_job.error = None
    mock_job.created_at = "2025-01-01"
    mock_job.updated_at = "2025-01-01"
    with patch("standards_sdk_py.inscriber.client.BrokerInscriberClient.wait_for_job") as mock_fn:
        mock_fn.return_value = mock_job
        result = wait_for_inscription_confirmation("job-1", _options())
        assert result.confirmed is True
        assert result.job_id == "job-1"


def test_generate_quote_delegates() -> None:
    with patch("standards_sdk_py.inscriber.client.get_registry_broker_quote") as mock_fn:
        mock_fn.return_value = MagicMock()
        generate_quote(_input(), _options())
        mock_fn.assert_called_once()
