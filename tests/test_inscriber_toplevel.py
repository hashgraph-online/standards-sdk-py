"""Tests for new top-level inscriber convenience functions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from standards_sdk_py.inscriber import client as inscriber_client_module
from standards_sdk_py.inscriber.client import (
    HederaClientConfig,
    InscriberJob,
    InscriberQuoteResult,
    InscribeViaRegistryBrokerOptions,
    InscriptionInput,
    InscriptionOptions,
    InscriptionResponse,
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


def _direct_config() -> HederaClientConfig:
    return HederaClientConfig(account_id="0.0.1", private_key="pk", network="testnet")


def test_get_registry_broker_quote() -> None:
    with patch(
        "standards_sdk_py.inscriber.client.InscriberClient.get_registry_broker_quote"
    ) as mock_fn:
        mock_fn.return_value = MagicMock()
        result = get_registry_broker_quote(_input(), _options())
        mock_fn.assert_called_once()
        assert result is not None


def test_coerce_inscription_options_accepts_base_url_alias() -> None:
    options = inscriber_client_module._coerce_inscription_options(
        {"baseUrl": "https://inscriber.test", "apiKey": "tok", "network": "testnet"}
    )
    assert options.base_url == "https://inscriber.test"


def test_inscribe_via_registry_broker() -> None:
    with patch(
        "standards_sdk_py.inscriber.client.InscriberClient.inscribe_via_registry_broker"
    ) as mock_fn:
        mock_fn.return_value = MagicMock()
        inscribe_via_registry_broker(_input(), _options())
        mock_fn.assert_called_once()


def test_inscribe_delegates() -> None:
    with patch("standards_sdk_py.inscriber.client._resolve_inscriber_invocation") as mock_resolve:
        with patch("standards_sdk_py.inscriber.client._inscribe_with_inscriber") as mock_fn:
            mock_resolve.return_value = (
                _direct_config(),
                InscriptionOptions(network="testnet"),
            )
            mock_fn.return_value = MagicMock()
            inscribe(_input(), _direct_config())
            mock_fn.assert_called_once()


def test_inscribe_with_signer_ignores_signer() -> None:
    with patch("standards_sdk_py.inscriber.client._resolve_inscriber_invocation") as mock_resolve:
        with patch("standards_sdk_py.inscriber.client._inscribe_with_inscriber") as mock_fn:
            mock_resolve.return_value = (
                _direct_config(),
                InscriptionOptions(network="testnet"),
            )
            mock_fn.return_value = MagicMock()
            inscribe_with_signer(_input(), _direct_config(), signer="fake")
            mock_fn.assert_called_once()


def test_inscribe_legacy_broker_options_accept_api_key_only() -> None:
    with patch("standards_sdk_py.inscriber.client.inscribe_via_registry_broker") as mock_fn:
        mock_fn.return_value = MagicMock(
            confirmed=False,
            job_id="job-1",
            status="pending",
            hrl=None,
            topic_id=None,
            network="testnet",
            error=None,
            created_at=None,
            updated_at=None,
            model_dump=lambda **_: {"jobId": "job-1", "status": "pending"},
        )
        result = inscribe(_input(), _options())
        assert result.job_id == "job-1"
        mock_fn.assert_called_once_with(_input(), _options())


def test_retrieve_inscription() -> None:
    fake_client = MagicMock()
    fake_client.retrieve_inscription.return_value = InscriberJob(id="job-1", status="completed")
    with patch("standards_sdk_py.inscriber.client._resolve_inscriber_client") as mock_client:
        mock_client.return_value = fake_client
        retrieve_inscription(
            "job-1",
            {"accountId": "0.0.1", "privateKey": "pk", "network": "testnet"},
        )
        fake_client.retrieve_inscription.assert_called_once_with("job-1")


def test_retrieve_inscription_accepts_plain_options_mapping() -> None:
    fake_client = MagicMock()
    fake_client.retrieve_inscription.return_value = InscriberJob(id="job-2", status="completed")
    with patch(
        "standards_sdk_py.inscriber.client._resolve_readonly_inscriber_client"
    ) as mock_client:
        mock_client.return_value = fake_client
        result = retrieve_inscription("job-2", {"network": "testnet", "apiKey": "tok"})
        assert result.id == "job-2"
        fake_client.retrieve_inscription.assert_called_once_with("job-2")


def test_wait_for_inscription_confirmation() -> None:
    fake_client = MagicMock()
    fake_client.wait_for_inscription.return_value = InscriberJob(status="completed", completed=True)
    with patch("standards_sdk_py.inscriber.client._resolve_inscriber_client") as mock_client:
        mock_client.return_value = fake_client
        result = wait_for_inscription_confirmation(
            "job-1",
            {
                "accountId": "0.0.1",
                "privateKey": "pk",
                "network": "testnet",
                "waitMaxAttempts": 3,
                "waitIntervalMs": 100,
            },
        )
        assert result.completed is True
        fake_client.wait_for_inscription.assert_called_once_with(
            "job-1",
            max_attempts=3,
            interval_ms=100,
        )


def test_wait_for_inscription_confirmation_uses_broker_job_ids() -> None:
    fake_client = MagicMock()
    fake_client.wait_for_job.return_value = MagicMock(
        job_id="job-1",
        id="job-1",
        status="completed",
        topic_id="0.0.123",
        error=None,
    )
    with patch("standards_sdk_py.inscriber.client.BrokerInscriberClient") as mock_client:
        mock_client.return_value = fake_client
        result = wait_for_inscription_confirmation("job-1", _options())
        assert result.completed is True
        fake_client.wait_for_job.assert_called_once_with(
            "job-1",
            timeout_ms=120000,
            poll_interval_ms=2000,
        )


def test_generate_quote_delegates() -> None:
    with patch("standards_sdk_py.inscriber.client._resolve_inscriber_invocation") as mock_resolve:
        with patch("standards_sdk_py.inscriber.client._inscribe_with_inscriber") as mock_fn:
            mock_resolve.return_value = (
                _direct_config(),
                InscriptionOptions(network="testnet"),
            )
            mock_fn.return_value = InscriptionResponse(
                quote=True,
                result={
                    "totalCostHbar": "1",
                    "validUntil": "",
                    "breakdown": {"transfers": []},
                },
            )
            result = generate_quote(_input(), _direct_config())
            assert isinstance(result, InscriberQuoteResult)
            mock_fn.assert_called_once()


def test_generate_quote_legacy_broker_options_accept_api_key_only() -> None:
    with patch("standards_sdk_py.inscriber.client.get_registry_broker_quote") as mock_quote:
        mock_quote.return_value = MagicMock(
            total_cost_hbar=1.5,
            expires_at="2026-01-01T00:00:00Z",
            mode="file",
        )
        result = generate_quote(_input(), _options())
        assert result.total_cost_hbar == "1.5"
        mock_quote.assert_called_once_with(_input(), _options())


def test_inscribe_waits_on_job_id_before_executed_transaction_id() -> None:
    fake_client = MagicMock()
    fake_client.start_inscription.return_value = InscriberJob(
        tx_id="0.0.123@1.2.3",
        transactionBytes="dGVzdA==",
        status="submitted",
    )
    fake_client.wait_for_inscription.return_value = InscriberJob(status="completed", completed=True)
    with patch("standards_sdk_py.inscriber.client._resolve_inscriber_client") as mock_client:
        with patch(
            "standards_sdk_py.inscriber.client._execute_inscriber_transaction"
        ) as mock_execute:
            mock_client.return_value = fake_client
            mock_execute.return_value = "0.0.123@9.8.7"
            response = inscribe(
                _input(),
                HederaClientConfig(account_id="0.0.1", private_key="pk", network="testnet"),
                InscriptionOptions(network="testnet"),
            )
            assert response.confirmed is True
            fake_client.wait_for_inscription.assert_called_once_with(
                "0.0.123-1-2-3",
                max_attempts=450,
                interval_ms=4000,
            )
