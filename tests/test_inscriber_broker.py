import httpx
import pytest

from standards_sdk_py.inscriber import (
    AsyncBrokerInscriberClient,
    BrokerInscriberClient,
    InscriberClient,
    InscribeViaRegistryBrokerOptions,
    InscriptionInput,
)
from standards_sdk_py.inscriber.client import _build_quote_request, _resolve_api_key
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/inscribe/content/quote":
        return httpx.Response(
            200,
            json={
                "quoteId": "quote-1",
                "totalCostHbar": 0.1,
                "credits": 12.0,
                "mode": "file",
            },
        )
    if request.url.path == "/inscribe/content":
        return httpx.Response(
            200,
            json={
                "jobId": "job-1",
                "status": "pending",
                "network": "testnet",
            },
        )
    if request.url.path == "/inscribe/content/job-1":
        return httpx.Response(
            200,
            json={
                "jobId": "job-1",
                "status": "completed",
                "topicId": "0.0.12345",
                "network": "testnet",
            },
        )
    return httpx.Response(404, json={"error": "not-found"})


def test_build_quote_request_buffer() -> None:
    request = _build_quote_request(
        InscriptionInput(type="buffer", buffer=b"hello", fileName="note.txt"),
        InscribeViaRegistryBrokerOptions(
            api_key="k",
            base_url="https://example.test",
            mode="bulk-files",
            metadata={"kind": "skill"},
        ),
    )
    assert request.input_type == "base64"
    assert request.file_name == "note.txt"
    assert request.mode == "bulk-files"


def test_broker_inscriber_sync() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "api-key"},
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    broker = BrokerInscriberClient(
        base_url="https://example.test",
        api_key="api-key",
        transport=transport,
    )
    payload = _build_quote_request(
        InscriptionInput(type="buffer", buffer=b"hello", fileName="note.txt"),
        InscribeViaRegistryBrokerOptions(base_url="https://example.test", api_key="api-key"),
    )
    quote = broker.create_quote(payload)
    assert quote.quote_id == "quote-1"
    result = broker.inscribe_and_wait(payload, timeout_ms=1_000, poll_interval_ms=10)
    assert result.confirmed is True
    assert result.topic_id == "0.0.12345"


def test_inscriber_client_sync_high_level(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeBroker:
        def __init__(self, *, base_url: str, api_key: str) -> None:
            assert base_url == "https://example.test"
            assert api_key == "api-key"

        def create_quote(self, _payload: object) -> object:
            class _Quote:
                quote_id = "quote-1"

            return _Quote()

        def inscribe_and_wait(
            self,
            _payload: object,
            *,
            timeout_ms: int,
            poll_interval_ms: int,
        ) -> object:
            class _Result:
                confirmed = True
                topic_id = "0.0.99"

            assert timeout_ms == 1000
            assert poll_interval_ms == 10
            return _Result()

    monkeypatch.setattr("standards_sdk_py.inscriber.client.BrokerInscriberClient", _FakeBroker)
    client = InscriberClient()
    options = InscribeViaRegistryBrokerOptions(
        base_url="https://example.test",
        api_key="api-key",
        wait_timeout_ms=1000,
        poll_interval_ms=10,
    )
    quote = client.get_registry_broker_quote(
        InscriptionInput(type="buffer", buffer=b"hello", fileName="note.txt"),
        options,
    )
    assert quote.quote_id == "quote-1"
    result = client.inscribe_via_registry_broker(
        InscriptionInput(type="buffer", buffer=b"hello", fileName="note.txt"),
        options,
    )
    assert result.confirmed is True
    assert result.topic_id == "0.0.99"


@pytest.mark.asyncio
async def test_broker_inscriber_async() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "api-key"},
        client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)),
    )
    broker = AsyncBrokerInscriberClient(
        base_url="https://example.test",
        api_key="api-key",
        transport=transport,
    )
    payload = _build_quote_request(
        InscriptionInput(type="buffer", buffer=b"hello", fileName="note.txt"),
        InscribeViaRegistryBrokerOptions(base_url="https://example.test", api_key="api-key"),
    )
    quote = await broker.create_quote(payload)
    assert quote.quote_id == "quote-1"
    result = await broker.inscribe_and_wait(payload, timeout_ms=1_000, poll_interval_ms=10)
    assert result.confirmed is True
    await broker.close()


def test_resolve_api_key_from_ledger_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "standards_sdk_py.inscriber.client.authenticate_with_ledger_credentials",
        lambda **_kwargs: "ledger-api-key",
    )
    options = InscribeViaRegistryBrokerOptions(
        base_url="https://example.test",
        ledger_account_id="0.0.123",
        ledger_private_key="302e020100300506032b657004220420abc",
    )
    assert _resolve_api_key(options) == "ledger-api-key"
