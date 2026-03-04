"""Comprehensive tests for inscriber client covering all uncovered paths."""

import base64
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from standards_sdk_py.exceptions import ValidationError
from standards_sdk_py.inscriber.client import (
    AsyncBrokerInscriberClient,
    AsyncInscriberClient,
    BrokerInscriberClient,
    BrokerJobResponse,
    BrokerQuoteRequest,
    InscriberClient,
    InscribeViaBrokerResult,
    InscribeViaRegistryBrokerOptions,
    InscriptionInput,
    InscriptionResponse,
    _build_quote_request,
    _guess_mime_type,
    _resolve_api_key,
)
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport

# ── _guess_mime_type tests ────────────────────────────────────────────


def test_guess_mime_type_txt() -> None:
    assert _guess_mime_type("note.txt") == "text/plain"


def test_guess_mime_type_unknown() -> None:
    assert _guess_mime_type("file.xyz123") == "application/octet-stream"


def test_guess_mime_type_png() -> None:
    mime = _guess_mime_type("image.png")
    assert "png" in mime


# ── _resolve_api_key tests ────────────────────────────────────────────


def test_resolve_api_key_from_api_key() -> None:
    opts = InscribeViaRegistryBrokerOptions(api_key="my-key")
    assert _resolve_api_key(opts) == "my-key"


def test_resolve_api_key_from_ledger() -> None:
    opts = InscribeViaRegistryBrokerOptions(ledger_api_key="ledger-key")
    assert _resolve_api_key(opts) == "ledger-key"


def test_resolve_api_key_ledger_precedence() -> None:
    opts = InscribeViaRegistryBrokerOptions(api_key="api-key", ledger_api_key="ledger-key")
    assert _resolve_api_key(opts) == "ledger-key"


def test_resolve_api_key_prefers_ledger_credentials_over_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "standards_sdk_py.inscriber.client.authenticate_with_ledger_credentials",
        lambda **_kwargs: "ledger-derived-key",
    )
    opts = InscribeViaRegistryBrokerOptions(
        api_key="api-key",
        ledger_account_id="0.0.123",
        ledger_private_key="302e020100300506032b657004220420abc",
        ledger_network="testnet",
    )
    assert _resolve_api_key(opts) == "ledger-derived-key"


def test_resolve_api_key_empty_raises() -> None:
    opts = InscribeViaRegistryBrokerOptions()
    with pytest.raises(ValidationError, match="is required for Registry Broker inscription"):
        _resolve_api_key(opts)


def test_resolve_api_key_whitespace_raises() -> None:
    opts = InscribeViaRegistryBrokerOptions(api_key="   ")
    with pytest.raises(ValidationError):
        _resolve_api_key(opts)


# ── _build_quote_request tests ────────────────────────────────────────


def test_build_quote_request_url_type() -> None:
    inp = InscriptionInput(type="url", url="https://example.com/file.txt")
    opts = InscribeViaRegistryBrokerOptions(
        api_key="k",
        mode="file",
        metadata={"key": "val"},
        tags=["tag1"],
        file_standard="hcs5",
        chunk_size=8192,
    )
    req = _build_quote_request(inp, opts)
    assert req.input_type == "url"
    assert req.url == "https://example.com/file.txt"
    assert req.mode == "file"
    assert req.metadata == {"key": "val"}
    assert req.tags == ["tag1"]
    assert req.file_standard == "hcs5"
    assert req.chunk_size == 8192


def test_build_quote_request_url_missing() -> None:
    inp = InscriptionInput(type="url")
    opts = InscribeViaRegistryBrokerOptions(api_key="k")
    with pytest.raises(ValidationError, match="input.url is required"):
        _build_quote_request(inp, opts)


def test_build_quote_request_file_type() -> None:
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"hello world")
        f.flush()
        inp = InscriptionInput(type="file", path=f.name)
        opts = InscribeViaRegistryBrokerOptions(api_key="k")
        req = _build_quote_request(inp, opts)
        assert req.input_type == "base64"
        assert req.file_name == Path(f.name).name
        assert req.base64 is not None
        assert base64.b64decode(req.base64) == b"hello world"
    Path(f.name).unlink(missing_ok=True)


def test_build_quote_request_file_missing_path() -> None:
    inp = InscriptionInput(type="file")
    opts = InscribeViaRegistryBrokerOptions(api_key="k")
    with pytest.raises(ValidationError, match="input.path is required"):
        _build_quote_request(inp, opts)


def test_build_quote_request_file_nonexistent_path() -> None:
    inp = InscriptionInput(type="file", path="/nonexistent/fake.txt")
    opts = InscribeViaRegistryBrokerOptions(api_key="k")
    with pytest.raises(ValidationError, match="input.path does not exist"):
        _build_quote_request(inp, opts)


def test_build_quote_request_buffer_type() -> None:
    inp = InscriptionInput(type="buffer", buffer=b"hello", fileName="note.txt")
    opts = InscribeViaRegistryBrokerOptions(api_key="k")
    req = _build_quote_request(inp, opts)
    assert req.input_type == "base64"
    assert req.file_name == "note.txt"
    assert req.mime_type == "text/plain"


def test_build_quote_request_buffer_with_explicit_mime() -> None:
    inp = InscriptionInput(
        type="buffer", buffer=b"data", fileName="data.bin", mimeType="application/pdf"
    )
    opts = InscribeViaRegistryBrokerOptions(api_key="k")
    req = _build_quote_request(inp, opts)
    assert req.mime_type == "application/pdf"


def test_build_quote_request_buffer_missing_data() -> None:
    inp = InscriptionInput(type="buffer", fileName="note.txt")
    opts = InscribeViaRegistryBrokerOptions(api_key="k")
    with pytest.raises(ValidationError, match="input.buffer is required"):
        _build_quote_request(inp, opts)


def test_build_quote_request_buffer_missing_filename() -> None:
    inp = InscriptionInput(type="buffer", buffer=b"data")
    opts = InscribeViaRegistryBrokerOptions(api_key="k")
    with pytest.raises(ValidationError, match="input.fileName is required"):
        _build_quote_request(inp, opts)


def test_build_quote_request_invalid_type() -> None:
    """InscriptionInput.type invalid values are caught during model construction."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        InscriptionInput(type="invalid_type")


def test_build_quote_request_invalid_type_bypassed() -> None:
    """Use model_construct to bypass pydantic Literal validation and hit line 239."""
    inp = InscriptionInput.model_construct(type="exotic")
    opts = InscribeViaRegistryBrokerOptions(api_key="k")
    with pytest.raises(ValidationError, match="input.type must be one of"):
        _build_quote_request(inp, opts)


# ── BrokerInscriberClient tests ───────────────────────────────────────


def _job_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/inscribe/content/quote":
        return httpx.Response(200, json={"quoteId": "q-1", "credits": 5.0, "mode": "file"})
    if request.url.path == "/inscribe/content":
        return httpx.Response(200, json={"jobId": "j-1", "status": "pending"})
    if request.url.path == "/inscribe/content/j-1":
        return httpx.Response(200, json={"jobId": "j-1", "status": "completed", "topicId": "0.0.1"})
    return httpx.Response(404, json={"error": "not-found"})


def test_broker_client_empty_key_raises() -> None:
    with pytest.raises(ValidationError, match="API key is required"):
        BrokerInscriberClient(api_key="   ")


def test_broker_client_create_quote() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.Client(transport=httpx.MockTransport(_job_handler)),
    )
    client = BrokerInscriberClient(api_key="k", transport=transport)
    payload = BrokerQuoteRequest(inputType="url", mode="file", url="https://example.test/f.txt")
    quote = client.create_quote(payload)
    assert quote.quote_id == "q-1"


def test_broker_client_create_job() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.Client(transport=httpx.MockTransport(_job_handler)),
    )
    client = BrokerInscriberClient(api_key="k", transport=transport)
    payload = BrokerQuoteRequest(inputType="url", mode="file", url="https://example.test/f.txt")
    job = client.create_job(payload)
    assert job.job_id == "j-1"
    assert job.status == "pending"


def test_broker_client_get_job() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.Client(transport=httpx.MockTransport(_job_handler)),
    )
    client = BrokerInscriberClient(api_key="k", transport=transport)
    job = client.get_job("j-1")
    assert job.status == "completed"


def test_broker_client_wait_for_job_completed() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.Client(transport=httpx.MockTransport(_job_handler)),
    )
    client = BrokerInscriberClient(api_key="k", transport=transport)
    job = client.wait_for_job("j-1", timeout_ms=5000, poll_interval_ms=10)
    assert job.status == "completed"


def _failed_job_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/inscribe/content/j-fail":
        return httpx.Response(
            200, json={"jobId": "j-fail", "status": "failed", "error": "out of credits"}
        )
    return httpx.Response(404, json={})


def test_broker_client_wait_for_job_failed() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.Client(transport=httpx.MockTransport(_failed_job_handler)),
    )
    client = BrokerInscriberClient(api_key="k", transport=transport)
    with pytest.raises(ValidationError, match="out of credits"):
        client.wait_for_job("j-fail", timeout_ms=5000, poll_interval_ms=10)


def _failed_no_error_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/inscribe/content/j-fail":
        return httpx.Response(200, json={"jobId": "j-fail", "status": "failed"})
    return httpx.Response(404, json={})


def test_broker_client_wait_for_job_failed_no_error_msg() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.Client(transport=httpx.MockTransport(_failed_no_error_handler)),
    )
    client = BrokerInscriberClient(api_key="k", transport=transport)
    with pytest.raises(ValidationError, match="inscription failed"):
        client.wait_for_job("j-fail", timeout_ms=5000, poll_interval_ms=10)


def _pending_forever_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/inscribe/content/j-pending":
        return httpx.Response(200, json={"jobId": "j-pending", "status": "pending"})
    return httpx.Response(404, json={})


def test_broker_client_wait_for_job_timeout() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.Client(transport=httpx.MockTransport(_pending_forever_handler)),
    )
    client = BrokerInscriberClient(api_key="k", transport=transport)
    with pytest.raises(ValidationError, match="did not complete before timeout"):
        client.wait_for_job("j-pending", timeout_ms=50, poll_interval_ms=10)


def _slow_handler(request: httpx.Request) -> httpx.Response:
    """Handler that introduces a delay to cover zero-timeout edge case."""
    import time

    time.sleep(0.1)
    if request.url.path == "/inscribe/content/j-slow":
        return httpx.Response(200, json={"jobId": "j-slow", "status": "pending"})
    return httpx.Response(404, json={})


def test_broker_client_wait_for_job_zero_timeout() -> None:
    """Covers the branch where latest is None because deadline is already past (line 429)."""
    transport = SyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.Client(transport=httpx.MockTransport(_pending_forever_handler)),
    )
    client = BrokerInscriberClient(api_key="k", transport=transport)
    # Mock monotonic so the deadline is already in the past on the first check.
    # First call: set deadline (returns 100.0), second call: check condition (returns 200.0)
    with patch("standards_sdk_py.inscriber.client.monotonic", side_effect=[100.0, 200.0]):
        with pytest.raises(ValidationError, match="was never fetched before timeout"):
            client.wait_for_job("j-pending", timeout_ms=1, poll_interval_ms=10)


def test_broker_client_inscribe_and_wait() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.Client(transport=httpx.MockTransport(_job_handler)),
    )
    client = BrokerInscriberClient(api_key="k", transport=transport)
    payload = BrokerQuoteRequest(inputType="url", mode="file", url="https://example.test/f")
    result = client.inscribe_and_wait(payload, timeout_ms=5000, poll_interval_ms=10)
    assert result.confirmed is True
    assert result.job_id == "j-1"


def _no_job_id_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/inscribe/content":
        return httpx.Response(200, json={"status": "pending"})
    return httpx.Response(404, json={})


def test_broker_client_inscribe_and_wait_missing_job_id() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.Client(transport=httpx.MockTransport(_no_job_id_handler)),
    )
    client = BrokerInscriberClient(api_key="k", transport=transport)
    payload = BrokerQuoteRequest(inputType="url", mode="file", url="https://example.test/f")
    with pytest.raises(ValidationError, match="missing job ID"):
        client.inscribe_and_wait(payload, timeout_ms=5000, poll_interval_ms=10)


# ── InscriberClient high-level tests ──────────────────────────────────


def test_inscriber_client_no_wait() -> None:
    class _FakeBroker:
        def __init__(self, *, base_url: str, api_key: str) -> None:
            pass

        def create_job(self, _payload: object) -> BrokerJobResponse:
            return BrokerJobResponse(
                jobId="j-nw", status="pending", network="testnet", topicId="0.0.50"
            )

    with patch("standards_sdk_py.inscriber.client.BrokerInscriberClient", _FakeBroker):
        client = InscriberClient()
        opts = InscribeViaRegistryBrokerOptions(
            api_key="k",
            wait_for_confirmation=False,
        )
        result = client.inscribe_via_registry_broker(
            InscriptionInput(type="buffer", buffer=b"hi", fileName="a.txt"),
            opts,
        )
        assert result.confirmed is False
        assert result.job_id == "j-nw"
        assert result.status == "pending"


def test_inscriber_client_skill_inscription() -> None:
    client = InscriberClient()
    captured: dict[str, object] = {}

    def _fake_inscribe(
        input_payload: InscriptionInput,
        options: InscribeViaRegistryBrokerOptions,
    ) -> InscribeViaBrokerResult:
        captured["input"] = input_payload
        captured["options"] = options
        return InscribeViaBrokerResult(confirmed=True, jobId="j-skill", status="completed")

    client.inscribe_via_registry_broker = _fake_inscribe  # type: ignore[method-assign]

    source_options = InscribeViaRegistryBrokerOptions(
        api_key="k",
        ledger_api_key="ledger-k",
        ledger_account_id="0.0.123",
        ledger_private_key="302e020100300506032b657004220420abc",
        ledger_network="testnet",
        ledger_expires_in_minutes=45,
        metadata={"existing": "val"},
    )
    result = client.inscribe_skill_via_registry_broker(
        InscriptionInput(type="buffer", buffer=b"skill", fileName="skill.tar.gz"),
        source_options,
        skill_name="my-skill",
        skill_version="1.0.0",
    )
    assert result.confirmed is True
    applied = captured["options"]
    assert isinstance(applied, InscribeViaRegistryBrokerOptions)
    assert applied.mode == "bulk-files"
    assert applied.ledger_api_key == source_options.ledger_api_key
    assert applied.ledger_account_id == source_options.ledger_account_id
    assert applied.ledger_private_key == source_options.ledger_private_key
    assert applied.ledger_network == source_options.ledger_network
    assert applied.ledger_expires_in_minutes == source_options.ledger_expires_in_minutes


def test_inscriber_client_generate_quote_no_broker() -> None:
    client = InscriberClient()
    with pytest.raises(ValidationError, match="requires RegistryBrokerClient"):
        client.generate_quote({"name": "skill"})


def test_inscriber_client_publish_no_broker() -> None:
    client = InscriberClient()
    with pytest.raises(ValidationError, match="requires RegistryBrokerClient"):
        client.publish({"name": "skill"})


def test_inscriber_client_generate_quote_with_broker() -> None:
    mock_broker = MagicMock()
    mock_broker.call_operation.return_value = {"quoteId": "q-1"}
    client = InscriberClient(broker_client=mock_broker)
    result = client.generate_quote({"name": "skill"})
    assert isinstance(result, InscriptionResponse)
    assert result.quote is True


def test_inscriber_client_publish_with_broker() -> None:
    mock_broker = MagicMock()
    mock_broker.call_operation.return_value = {"jobId": "job-1"}
    client = InscriberClient(broker_client=mock_broker)
    result = client.publish({"name": "skill"})
    assert isinstance(result, InscriptionResponse)
    assert result.confirmed is False


# ── AsyncBrokerInscriberClient tests ──────────────────────────────────


@pytest.mark.asyncio
async def test_async_broker_client_empty_key_raises() -> None:
    with pytest.raises(ValidationError, match="API key is required"):
        AsyncBrokerInscriberClient(api_key="   ")


@pytest.mark.asyncio
async def test_async_broker_client_create_quote() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.AsyncClient(transport=httpx.MockTransport(_job_handler)),
    )
    client = AsyncBrokerInscriberClient(api_key="k", transport=transport)
    payload = BrokerQuoteRequest(inputType="url", mode="file", url="https://example.test/f")
    quote = await client.create_quote(payload)
    assert quote.quote_id == "q-1"


@pytest.mark.asyncio
async def test_async_broker_client_create_job() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.AsyncClient(transport=httpx.MockTransport(_job_handler)),
    )
    client = AsyncBrokerInscriberClient(api_key="k", transport=transport)
    payload = BrokerQuoteRequest(inputType="url", mode="file", url="https://example.test/f")
    job = await client.create_job(payload)
    assert job.job_id == "j-1"


@pytest.mark.asyncio
async def test_async_broker_client_get_job() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.AsyncClient(transport=httpx.MockTransport(_job_handler)),
    )
    client = AsyncBrokerInscriberClient(api_key="k", transport=transport)
    job = await client.get_job("j-1")
    assert job.status == "completed"


@pytest.mark.asyncio
async def test_async_broker_client_wait_for_job() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.AsyncClient(transport=httpx.MockTransport(_job_handler)),
    )
    client = AsyncBrokerInscriberClient(api_key="k", transport=transport)
    job = await client.wait_for_job("j-1", timeout_ms=5000, poll_interval_ms=10)
    assert job.status == "completed"


@pytest.mark.asyncio
async def test_async_broker_client_wait_for_job_failed() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.AsyncClient(transport=httpx.MockTransport(_failed_job_handler)),
    )
    client = AsyncBrokerInscriberClient(api_key="k", transport=transport)
    with pytest.raises(ValidationError, match="out of credits"):
        await client.wait_for_job("j-fail", timeout_ms=5000, poll_interval_ms=10)


@pytest.mark.asyncio
async def test_async_broker_client_wait_for_job_timeout() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.AsyncClient(transport=httpx.MockTransport(_pending_forever_handler)),
    )
    client = AsyncBrokerInscriberClient(api_key="k", transport=transport)
    with pytest.raises(ValidationError, match="did not complete before timeout"):
        await client.wait_for_job("j-pending", timeout_ms=50, poll_interval_ms=10)


@pytest.mark.asyncio
async def test_async_broker_client_wait_for_job_zero_timeout() -> None:
    """Covers the branch where latest is None because deadline is already past (line 526)."""
    transport = AsyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.AsyncClient(transport=httpx.MockTransport(_pending_forever_handler)),
    )
    client = AsyncBrokerInscriberClient(api_key="k", transport=transport)
    # Mock monotonic so the deadline is already in the past on the first check.
    with patch("standards_sdk_py.inscriber.client.monotonic", side_effect=[100.0, 200.0]):
        with pytest.raises(ValidationError, match="was never fetched before timeout"):
            await client.wait_for_job("j-pending", timeout_ms=1, poll_interval_ms=10)


@pytest.mark.asyncio
async def test_async_broker_client_inscribe_and_wait() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.AsyncClient(transport=httpx.MockTransport(_job_handler)),
    )
    client = AsyncBrokerInscriberClient(api_key="k", transport=transport)
    payload = BrokerQuoteRequest(inputType="url", mode="file", url="https://example.test/f")
    result = await client.inscribe_and_wait(payload, timeout_ms=5000, poll_interval_ms=10)
    assert result.confirmed is True
    assert result.job_id == "j-1"


@pytest.mark.asyncio
async def test_async_broker_client_inscribe_and_wait_missing_id() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.AsyncClient(transport=httpx.MockTransport(_no_job_id_handler)),
    )
    client = AsyncBrokerInscriberClient(api_key="k", transport=transport)
    payload = BrokerQuoteRequest(inputType="url", mode="file", url="https://example.test/f")
    with pytest.raises(ValidationError, match="missing job ID"):
        await client.inscribe_and_wait(payload, timeout_ms=5000, poll_interval_ms=10)


@pytest.mark.asyncio
async def test_async_broker_client_close() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        headers={"x-api-key": "k"},
        client=httpx.AsyncClient(transport=httpx.MockTransport(_job_handler)),
    )
    client = AsyncBrokerInscriberClient(api_key="k", transport=transport)
    await client.close()


# ── AsyncInscriberClient tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_inscriber_client_get_quote() -> None:
    class _FakeAsyncBroker:
        def __init__(self, *, base_url: str, api_key: str, transport: object = None) -> None:
            pass

        async def create_quote(self, _payload: object) -> object:
            from standards_sdk_py.inscriber.client import BrokerQuoteResponse

            return BrokerQuoteResponse(quoteId="q-async", credits=10.0)

    with patch("standards_sdk_py.inscriber.client.AsyncBrokerInscriberClient", _FakeAsyncBroker):
        client = AsyncInscriberClient()
        opts = InscribeViaRegistryBrokerOptions(api_key="k")
        q = await client.get_registry_broker_quote(
            InscriptionInput(type="buffer", buffer=b"hi", fileName="a.txt"),
            opts,
        )
        assert q.quote_id == "q-async"


@pytest.mark.asyncio
async def test_async_inscriber_client_inscribe_no_wait() -> None:
    class _FakeAsyncBroker:
        def __init__(self, *, base_url: str, api_key: str, transport: object = None) -> None:
            pass

        async def create_job(self, _payload: object) -> BrokerJobResponse:
            return BrokerJobResponse(jobId="j-async-nw", status="pending")

    with patch("standards_sdk_py.inscriber.client.AsyncBrokerInscriberClient", _FakeAsyncBroker):
        client = AsyncInscriberClient()
        opts = InscribeViaRegistryBrokerOptions(api_key="k", wait_for_confirmation=False)
        result = await client.inscribe_via_registry_broker(
            InscriptionInput(type="buffer", buffer=b"hi", fileName="a.txt"),
            opts,
        )
        assert result.confirmed is False
        assert result.job_id == "j-async-nw"


@pytest.mark.asyncio
async def test_async_inscriber_client_inscribe_with_wait() -> None:
    class _FakeAsyncBroker:
        def __init__(self, *, base_url: str, api_key: str, transport: object = None) -> None:
            pass

        async def inscribe_and_wait(
            self, _payload: object, *, timeout_ms: int, poll_interval_ms: int
        ) -> InscribeViaBrokerResult:
            return InscribeViaBrokerResult(confirmed=True, jobId="j-wait", status="completed")

    with patch("standards_sdk_py.inscriber.client.AsyncBrokerInscriberClient", _FakeAsyncBroker):
        client = AsyncInscriberClient()
        opts = InscribeViaRegistryBrokerOptions(api_key="k")
        result = await client.inscribe_via_registry_broker(
            InscriptionInput(type="buffer", buffer=b"hi", fileName="a.txt"),
            opts,
        )
        assert result.confirmed is True


@pytest.mark.asyncio
async def test_async_inscriber_client_generate_quote_no_broker() -> None:
    client = AsyncInscriberClient()
    with pytest.raises(ValidationError, match="requires AsyncRegistryBrokerClient"):
        await client.generate_quote({"name": "skill"})


@pytest.mark.asyncio
async def test_async_inscriber_client_publish_no_broker() -> None:
    client = AsyncInscriberClient()
    with pytest.raises(ValidationError, match="requires AsyncRegistryBrokerClient"):
        await client.publish({"name": "skill"})


@pytest.mark.asyncio
async def test_async_inscriber_client_generate_quote_with_broker() -> None:
    mock_broker = AsyncMock()
    mock_broker.call_operation.return_value = {"quoteId": "q-1"}
    client = AsyncInscriberClient(broker_client=mock_broker)
    result = await client.generate_quote({"name": "skill"})
    assert isinstance(result, InscriptionResponse)
    assert result.quote is True


@pytest.mark.asyncio
async def test_async_inscriber_client_publish_with_broker() -> None:
    mock_broker = AsyncMock()
    mock_broker.call_operation.return_value = {"jobId": "job-1"}
    client = AsyncInscriberClient(broker_client=mock_broker)
    result = await client.publish({"name": "skill"})
    assert isinstance(result, InscriptionResponse)
    assert result.confirmed is False


# ── Model tests ───────────────────────────────────────────────────────


def test_broker_job_response_uses_id_fallback() -> None:
    """BrokerJobResponse can use 'id' field if jobId is missing."""
    job = BrokerJobResponse(id="j-via-id", status="completed")
    assert job.id == "j-via-id"
    assert job.job_id is None


def test_inscription_response_model() -> None:
    resp = InscriptionResponse(confirmed=True, quote=False, result={"ok": True})
    assert resp.confirmed is True
    assert resp.quote is False
