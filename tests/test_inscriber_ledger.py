"""Additional inscriber tests covering new ledger auth functions and remaining gaps."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from standards_sdk_py.exceptions import ErrorContext, ParseError, ValidationError
from standards_sdk_py.inscriber.client import (
    BrokerInscriberClient,
    InscribeViaRegistryBrokerOptions,
    LedgerChallengeResponse,
    LedgerVerifyApiKey,
    LedgerVerifyResponse,
    _normalize_ledger_network,
    _resolve_api_key,
    _sign_ledger_challenge,
    authenticate_with_ledger_credentials,
)

# ── _normalize_ledger_network tests ───────────────────────────────────


def test_normalize_mainnet() -> None:
    assert _normalize_ledger_network("mainnet") == "mainnet"
    assert _normalize_ledger_network("hedera:mainnet") == "mainnet"
    assert _normalize_ledger_network("hedera-mainnet") == "mainnet"
    assert _normalize_ledger_network("hedera_mainnet") == "mainnet"


def test_normalize_testnet() -> None:
    assert _normalize_ledger_network("testnet") == "testnet"
    assert _normalize_ledger_network("hedera:testnet") == "testnet"
    assert _normalize_ledger_network("hedera-testnet") == "testnet"
    assert _normalize_ledger_network("hedera_testnet") == "testnet"


def test_normalize_case_insensitive() -> None:
    assert _normalize_ledger_network("  MAINNET  ") == "mainnet"
    assert _normalize_ledger_network("TESTNET") == "testnet"


def test_normalize_unknown_passthrough() -> None:
    assert _normalize_ledger_network("previewnet") == "previewnet"
    assert _normalize_ledger_network("custom") == "custom"


# ── _sign_ledger_challenge tests ──────────────────────────────────────


def test_sign_ledger_challenge_no_hedera_module() -> None:
    with patch.dict("sys.modules", {"hedera": None}):
        with pytest.raises(ValidationError, match="hedera-sdk-py is required"):
            _sign_ledger_challenge("message", "private-key")


def test_sign_ledger_challenge_no_private_key_type() -> None:
    mock_hedera = MagicMock(spec=[])
    with patch(
        "standards_sdk_py.inscriber.client.importlib.import_module",
        return_value=mock_hedera,
    ):
        with pytest.raises(ValidationError, match="PrivateKey type unavailable"):
            _sign_ledger_challenge("message", "private-key")


def test_sign_ledger_challenge_bad_private_key() -> None:
    mock_pk_type = MagicMock()
    mock_pk_type.fromString.side_effect = Exception("invalid key format")
    mock_hedera = MagicMock()
    mock_hedera.PrivateKey = mock_pk_type
    with patch(
        "standards_sdk_py.inscriber.client.importlib.import_module",
        return_value=mock_hedera,
    ):
        with pytest.raises(ValidationError, match="invalid Hedera private key"):
            _sign_ledger_challenge("message", "bad-key")


def test_sign_ledger_challenge_sign_fails() -> None:
    mock_key = MagicMock()
    mock_key.sign.side_effect = Exception("signature failure")
    mock_pk_type = MagicMock()
    mock_pk_type.fromString.return_value = mock_key
    mock_hedera = MagicMock()
    mock_hedera.PrivateKey = mock_pk_type
    with patch(
        "standards_sdk_py.inscriber.client.importlib.import_module",
        return_value=mock_hedera,
    ):
        with pytest.raises(ValidationError, match="failed to sign ledger challenge"):
            _sign_ledger_challenge("message", "good-key")


def test_sign_ledger_challenge_success() -> None:
    mock_key = MagicMock()
    mock_key.sign.return_value = b"\x01\x02\x03"
    mock_pub_key = MagicMock()
    mock_pub_key.toString.return_value = "302a300506..."
    mock_key.getPublicKey.return_value = mock_pub_key
    mock_pk_type = MagicMock()
    mock_pk_type.fromString.return_value = mock_key
    mock_hedera = MagicMock()
    mock_hedera.PrivateKey = mock_pk_type
    with patch(
        "standards_sdk_py.inscriber.client.importlib.import_module",
        return_value=mock_hedera,
    ):
        sig_b64, pub_key = _sign_ledger_challenge("hello", "test-key")
        assert isinstance(sig_b64, str)
        assert pub_key == "302a300506..."


# ── _resolve_api_key with ledger credentials ──────────────────────────


def test_resolve_api_key_with_ledger_credentials() -> None:
    with patch(
        "standards_sdk_py.inscriber.client.authenticate_with_ledger_credentials",
        return_value="ledger-api-key",
    ):
        opts = InscribeViaRegistryBrokerOptions(
            ledger_account_id="0.0.123",
            ledger_private_key="some-private-key",
        )
        key = _resolve_api_key(opts)
        assert key == "ledger-api-key"


def test_resolve_api_key_no_credentials_raises() -> None:
    opts = InscribeViaRegistryBrokerOptions()
    with pytest.raises(ValidationError, match="either ledger_api_key/api_key"):
        _resolve_api_key(opts)


# ── authenticate_with_ledger_credentials tests ────────────────────────


def test_authenticate_empty_account_id() -> None:
    with pytest.raises(ValidationError, match="ledger account_id is required"):
        authenticate_with_ledger_credentials(
            base_url="https://example.test",
            account_id="",
            private_key="some-key",
        )


def test_authenticate_empty_private_key() -> None:
    with pytest.raises(ValidationError, match="ledger private_key is required"):
        authenticate_with_ledger_credentials(
            base_url="https://example.test",
            account_id="0.0.123",
            private_key="  ",
        )


def _auth_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/auth/ledger/challenge":
        return httpx.Response(
            200,
            json={
                "challengeId": "ch-1",
                "message": "Sign this message to prove identity",
            },
        )
    if request.url.path == "/auth/ledger/verify":
        return httpx.Response(
            200,
            json={
                "key": "returned-api-key-xyz",
                "apiKey": {
                    "id": "ak-1",
                    "prefix": "hol_",
                    "lastFour": "abcd",
                },
                "accountId": "0.0.123",
                "network": "testnet",
            },
        )
    return httpx.Response(404, json={"error": "not-found"})


def test_authenticate_with_ledger_credentials_success() -> None:
    with patch(
        "standards_sdk_py.inscriber.client._sign_ledger_challenge",
        return_value=("sig_b64_value", "pub_key_value"),
    ):
        with patch(
            "standards_sdk_py.inscriber.client.SyncHttpTransport",
        ) as mock_transport_cls:
            mock_transport = MagicMock()
            mock_transport_cls.return_value = mock_transport
            mock_transport.request_json.side_effect = [
                {"challengeId": "ch-1", "message": "sign me", "expiresAt": "2030-01-01T00:00:00Z"},
                {
                    "key": "returned-api-key-xyz",
                    "apiKey": {"id": "ak-1", "prefix": "hol_", "lastFour": "abcd"},
                    "accountId": "0.0.123",
                    "network": "testnet",
                },
            ]
            api_key = authenticate_with_ledger_credentials(
                base_url="https://example.test",
                account_id="0.0.123",
                private_key="test-key",
                network="testnet",
                expires_in_minutes=60,
            )
            assert api_key == "returned-api-key-xyz"
            mock_transport.close.assert_called_once()


def test_authenticate_without_expires_in_minutes() -> None:
    with patch(
        "standards_sdk_py.inscriber.client._sign_ledger_challenge",
        return_value=("sig_b64_value", "pub_key_value"),
    ):
        with patch(
            "standards_sdk_py.inscriber.client.SyncHttpTransport",
        ) as mock_transport_cls:
            mock_transport = MagicMock()
            mock_transport_cls.return_value = mock_transport
            mock_transport.request_json.side_effect = [
                {"challengeId": "ch-1", "message": "sign me", "expiresAt": "2030-01-01T00:00:00Z"},
                {
                    "key": "returned-api-key-xyz",
                    "apiKey": {"id": "ak-1", "prefix": "hol_", "lastFour": "abcd"},
                    "accountId": "0.0.123",
                    "network": "testnet",
                },
            ]
            api_key = authenticate_with_ledger_credentials(
                base_url="https://example.test",
                account_id="0.0.123",
                private_key="test-key",
            )
            assert api_key == "returned-api-key-xyz"


def test_authenticate_retries_transient_challenge_parse_error() -> None:
    with patch(
        "standards_sdk_py.inscriber.client._sign_ledger_challenge",
        return_value=("sig_b64_value", "pub_key_value"),
    ):
        with patch(
            "standards_sdk_py.inscriber.client.SyncHttpTransport",
        ) as mock_transport_cls:
            mock_transport = MagicMock()
            mock_transport_cls.return_value = mock_transport
            mock_transport.request_json.side_effect = [
                ParseError(
                    "Failed to parse JSON response body",
                    ErrorContext(status_code=503, method="POST"),
                ),
                {"challengeId": "ch-1", "message": "sign me", "expiresAt": "2030-01-01T00:00:00Z"},
                {
                    "key": "returned-api-key-xyz",
                    "apiKey": {"id": "ak-1", "prefix": "hol_", "lastFour": "abcd"},
                    "accountId": "0.0.123",
                    "network": "testnet",
                },
            ]
            api_key = authenticate_with_ledger_credentials(
                base_url="https://example.test",
                account_id="0.0.123",
                private_key="test-key",
            )
            assert api_key == "returned-api-key-xyz"
            assert mock_transport.request_json.call_count == 3


def test_authenticate_raises_after_transient_retry_exhaustion() -> None:
    with patch(
        "standards_sdk_py.inscriber.client._sign_ledger_challenge",
        return_value=("sig_b64_value", "pub_key_value"),
    ):
        with patch(
            "standards_sdk_py.inscriber.client.SyncHttpTransport",
        ) as mock_transport_cls:
            mock_transport = MagicMock()
            mock_transport_cls.return_value = mock_transport
            mock_transport.request_json.side_effect = ParseError(
                "Failed to parse JSON response body",
                ErrorContext(status_code=503, method="POST"),
            )
            with pytest.raises(ParseError, match="Failed to parse JSON response body"):
                authenticate_with_ledger_credentials(
                    base_url="https://example.test",
                    account_id="0.0.123",
                    private_key="test-key",
                )
            assert mock_transport.request_json.call_count == 3


# ── Ledger models tests ──────────────────────────────────────────────


def test_ledger_challenge_response_model() -> None:
    resp = LedgerChallengeResponse(
        challengeId="ch-1", message="sign me", expiresAt="2030-01-01T00:00:00Z"
    )
    assert resp.challenge_id == "ch-1"
    assert resp.message == "sign me"
    assert resp.expires_at == "2030-01-01T00:00:00Z"


def test_ledger_verify_response_model() -> None:
    resp = LedgerVerifyResponse(
        key="api-key",
        apiKey={"id": "ak-1", "prefix": "hol_", "lastFour": "abcd"},
        accountId="0.0.123",
        network="testnet",
    )
    assert resp.key == "api-key"
    assert resp.api_key.prefix == "hol_"
    assert resp.network_canonical is None


def test_ledger_verify_api_key_model() -> None:
    ak = LedgerVerifyApiKey(id="id-1", prefix="p", lastFour="1234")
    assert ak.last_four == "1234"


# ── BrokerInscriberClient with default transport ──────────────────────


def test_broker_client_creates_default_transport() -> None:
    """When no transport is provided, one is created from base_url + api_key."""
    client = BrokerInscriberClient(
        base_url="https://example.test",
        api_key="my-key",
    )
    assert client._transport is not None
    assert client._transport.base_url == "https://example.test"


# ── InscribeViaRegistryBrokerOptions model tests ─────────────────────


def test_options_new_fields() -> None:
    opts = InscribeViaRegistryBrokerOptions(
        ledger_account_id="0.0.123",
        ledger_private_key="pk",
        ledger_network="mainnet",
        ledger_expires_in_minutes=30,
    )
    assert opts.ledger_account_id == "0.0.123"
    assert opts.ledger_private_key == "pk"
    assert opts.ledger_network == "mainnet"
    assert opts.ledger_expires_in_minutes == 30


# ── Sync _fill_path and _query_from_values (sync_client.py) ──────────


def test_sync_fill_path_missing_param() -> None:
    from standards_sdk_py.registry_broker.sync_client import _fill_path

    with pytest.raises(ValidationError, match="Missing required path parameter"):
        _fill_path("/resolve/{uaid}", {"other": "val"})


def test_sync_query_from_values_non_primitive() -> None:
    from standards_sdk_py.registry_broker.sync_client import _query_from_values

    result = _query_from_values({"a": [1, 2]})
    assert result is not None
    assert result["a"] == "[1, 2]"


def test_sync_query_from_values_all_none() -> None:
    from standards_sdk_py.registry_broker.sync_client import _query_from_values

    assert _query_from_values({"a": None}) is None


# ── Sync _parse_model validation error ────────────────────────────────


def test_sync_parse_model_validation_error() -> None:
    from pydantic import BaseModel

    from standards_sdk_py.exceptions import ParseError
    from standards_sdk_py.registry_broker.sync_client import RegistryBrokerClient

    class StrictModel(BaseModel):
        name: str
        count: int

    with pytest.raises(ParseError, match="Failed to validate"):
        RegistryBrokerClient._parse_model({"name": 123}, StrictModel)


def test_async_parse_model_validation_error() -> None:
    from pydantic import BaseModel

    from standards_sdk_py.exceptions import ParseError
    from standards_sdk_py.registry_broker.async_client import AsyncRegistryBrokerClient

    class StrictModel(BaseModel):
        name: str
        count: int

    with pytest.raises(ParseError, match="Failed to validate"):
        AsyncRegistryBrokerClient._parse_model({"name": 123}, StrictModel)
