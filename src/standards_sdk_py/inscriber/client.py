"""Inscriber sync and async clients with Registry Broker workflows."""

from __future__ import annotations

import asyncio
import base64
import importlib
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from time import monotonic, sleep
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from standards_sdk_py.exceptions import (
    ApiError,
    ErrorContext,
    ParseError,
    TransportError,
    ValidationError,
)
from standards_sdk_py.registry_broker.async_client import AsyncRegistryBrokerClient
from standards_sdk_py.registry_broker.sync_client import RegistryBrokerClient
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.types import JsonObject, JsonValue

InscriptionInputType = Literal["url", "file", "buffer"]
InscriptionMode = Literal["file", "upload", "hashinal", "hashinal-collection", "bulk-files"]

DEFAULT_REGISTRY_BROKER_URL = "https://hol.org/registry/api/v1"
DEFAULT_REGISTRY_TIMEOUT_MS = 120000
DEFAULT_REGISTRY_POLL_INTERVAL_MS = 2000
DEFAULT_REGISTRY_RETRY_COUNT = 3


class InscriptionInput(BaseModel):
    """Inscription input."""

    type: InscriptionInputType
    url: str | None = None
    path: str | None = None
    buffer: bytes | None = None
    file_name: str | None = Field(default=None, alias="fileName")
    mime_type: str | None = Field(default=None, alias="mimeType")


class BrokerQuoteRequest(BaseModel):
    """Registry Broker quote payload."""

    input_type: str = Field(alias="inputType")
    mode: InscriptionMode
    url: str | None = None
    base64: str | None = None
    file_name: str | None = Field(default=None, alias="fileName")
    mime_type: str | None = Field(default=None, alias="mimeType")
    metadata: dict[str, object] | None = None
    tags: list[str] | None = None
    file_standard: str | None = Field(default=None, alias="fileStandard")
    chunk_size: int | None = Field(default=None, alias="chunkSize")


class BrokerQuoteResponse(BaseModel):
    """Registry Broker quote response."""

    model_config = ConfigDict(extra="allow")

    quote_id: str | None = Field(default=None, alias="quoteId")
    content_hash: str | None = Field(default=None, alias="contentHash")
    size_bytes: int | None = Field(default=None, alias="sizeBytes")
    total_cost_hbar: float | None = Field(default=None, alias="totalCostHbar")
    credits: float | None = None
    usd_cents: int | None = Field(default=None, alias="usdCents")
    expires_at: str | None = Field(default=None, alias="expiresAt")
    mode: str | None = None


class BrokerJobResponse(BaseModel):
    """Registry Broker inscription job response."""

    model_config = ConfigDict(extra="allow")

    job_id: str | None = Field(default=None, alias="jobId")
    id: str | None = None
    status: str | None = None
    hrl: str | None = None
    topic_id: str | None = Field(default=None, alias="topicId")
    network: str | None = None
    credits: float | None = None
    error: str | None = None
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")


class LedgerChallengeResponse(BaseModel):
    """Registry Broker ledger challenge response."""

    challenge_id: str = Field(alias="challengeId")
    message: str
    expires_at: str = Field(alias="expiresAt")


class LedgerVerifyApiKey(BaseModel):
    """Ledger-issued API key summary."""

    model_config = ConfigDict(extra="allow")

    id: str
    prefix: str
    last_four: str = Field(alias="lastFour")


class LedgerVerifyResponse(BaseModel):
    """Registry Broker ledger verification response."""

    key: str
    api_key: LedgerVerifyApiKey = Field(alias="apiKey")
    account_id: str = Field(alias="accountId")
    network: str
    network_canonical: str | None = Field(default=None, alias="networkCanonical")


class InscribeViaBrokerResult(BaseModel):
    """High-level result for broker-backed inscription."""

    confirmed: bool
    job_id: str = Field(alias="jobId")
    status: str
    hrl: str | None = None
    topic_id: str | None = Field(default=None, alias="topicId")
    network: str | None = None
    error: str | None = None
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")


@dataclass(slots=True, frozen=True)
class InscribeViaRegistryBrokerOptions:
    """Broker inscription options."""

    base_url: str = DEFAULT_REGISTRY_BROKER_URL
    api_key: str | None = None
    ledger_api_key: str | None = None
    ledger_account_id: str | None = None
    ledger_private_key: str | None = None
    ledger_network: str = "testnet"
    ledger_expires_in_minutes: int | None = None
    mode: InscriptionMode = "file"
    metadata: dict[str, object] | None = None
    tags: list[str] | None = None
    file_standard: str | None = None
    chunk_size: int | None = None
    wait_for_confirmation: bool = True
    wait_timeout_ms: int = DEFAULT_REGISTRY_TIMEOUT_MS
    poll_interval_ms: int = DEFAULT_REGISTRY_POLL_INTERVAL_MS


class InscriptionResponse(BaseModel):
    """Compatibility response model for prior inscriber client API."""

    model_config = ConfigDict(extra="allow")

    confirmed: bool | None = None
    quote: bool | None = None
    result: object | None = None
    inscription: object | None = None


def _guess_mime_type(file_name: str) -> str:
    guessed, _encoding = mimetypes.guess_type(file_name, strict=False)
    return guessed or "application/octet-stream"


def _is_transient_registry_error(exc: Exception) -> bool:
    if isinstance(exc, TransportError | ParseError):
        return True
    if isinstance(exc, ApiError):
        status_code = exc.context.status_code
        return status_code in {502, 503, 504}
    return False


def _request_registry_json_with_retry(
    transport: SyncHttpTransport,
    method: str,
    path: str,
    *,
    body: JsonObject | None = None,
    retry_count: int = DEFAULT_REGISTRY_RETRY_COUNT,
    retry_delay_ms: int = DEFAULT_REGISTRY_POLL_INTERVAL_MS,
) -> JsonValue:
    retries = max(retry_count, 1)
    for attempt in range(retries):
        try:
            return transport.request_json(method, path, body=body)
        except Exception as exc:
            if attempt + 1 >= retries or not _is_transient_registry_error(exc):
                raise
            sleep(max(retry_delay_ms, 1) / 1000.0)
    raise ValidationError("registry broker request retry loop exhausted", ErrorContext())


def _build_quote_request(
    input_payload: InscriptionInput,
    options: InscribeViaRegistryBrokerOptions,
) -> BrokerQuoteRequest:
    mode = options.mode
    if input_payload.type == "url":
        if not input_payload.url:
            raise ValidationError(
                "input.url is required for url input type",
                ErrorContext(details={"input_type": input_payload.type}),
            )
        return BrokerQuoteRequest(
            inputType="url",
            mode=mode,
            url=input_payload.url.strip(),
            metadata=options.metadata,
            tags=options.tags,
            fileStandard=options.file_standard,
            chunkSize=options.chunk_size,
        )

    if input_payload.type == "file":
        if not input_payload.path:
            raise ValidationError(
                "input.path is required for file input type",
                ErrorContext(details={"input_type": input_payload.type}),
            )
        file_path = Path(input_payload.path)
        if not file_path.exists():
            raise ValidationError(
                "input.path does not exist",
                ErrorContext(details={"path": str(file_path)}),
            )
        content = file_path.read_bytes()
        file_name = file_path.name
        mime_type = _guess_mime_type(file_name)
        return BrokerQuoteRequest(
            inputType="base64",
            mode=mode,
            base64=base64.b64encode(content).decode("utf-8"),
            fileName=file_name,
            mimeType=mime_type,
            metadata=options.metadata,
            tags=options.tags,
            fileStandard=options.file_standard,
            chunkSize=options.chunk_size,
        )

    if input_payload.type == "buffer":
        if not input_payload.buffer:
            raise ValidationError(
                "input.buffer is required for buffer input type",
                ErrorContext(details={"input_type": input_payload.type}),
            )
        if not input_payload.file_name:
            raise ValidationError(
                "input.fileName is required for buffer input type",
                ErrorContext(details={"input_type": input_payload.type}),
            )
        mime_type = input_payload.mime_type or _guess_mime_type(input_payload.file_name)
        return BrokerQuoteRequest(
            inputType="base64",
            mode=mode,
            base64=base64.b64encode(input_payload.buffer).decode("utf-8"),
            fileName=input_payload.file_name,
            mimeType=mime_type,
            metadata=options.metadata,
            tags=options.tags,
            fileStandard=options.file_standard,
            chunkSize=options.chunk_size,
        )

    raise ValidationError(
        "input.type must be one of: url, file, buffer",
        ErrorContext(details={"input_type": input_payload.type}),
    )


def _resolve_api_key(options: InscribeViaRegistryBrokerOptions) -> str:
    explicit_ledger_key = (options.ledger_api_key or "").strip()
    if explicit_ledger_key:
        return explicit_ledger_key

    account_id = (options.ledger_account_id or "").strip()
    private_key = (options.ledger_private_key or "").strip()
    if account_id and private_key:
        return authenticate_with_ledger_credentials(
            base_url=options.base_url,
            account_id=account_id,
            private_key=private_key,
            network=options.ledger_network,
            expires_in_minutes=options.ledger_expires_in_minutes,
        )

    explicit_api_key = (options.api_key or "").strip()
    if explicit_api_key:
        return explicit_api_key

    raise ValidationError(
        (
            "either ledger_api_key/api_key or ledger_account_id+ledger_private_key "
            "is required for Registry Broker inscription"
        ),
        ErrorContext(),
    )


def _normalize_ledger_network(network: str) -> str:
    normalized = network.strip().lower()
    aliases: dict[str, str] = {
        "mainnet": "mainnet",
        "hedera:mainnet": "mainnet",
        "hedera-mainnet": "mainnet",
        "hedera_mainnet": "mainnet",
        "testnet": "testnet",
        "hedera:testnet": "testnet",
        "hedera-testnet": "testnet",
        "hedera_testnet": "testnet",
    }
    return aliases.get(normalized, normalized)


def _sign_ledger_challenge(message: str, private_key: str) -> tuple[str, str]:
    try:
        hedera_module = importlib.import_module("hedera")
    except ModuleNotFoundError as exc:
        raise ValidationError(
            "hedera-sdk-py is required for ledger credential authentication",
            ErrorContext(details={"dependency": "hedera-sdk-py"}),
        ) from exc
    private_key_type = getattr(hedera_module, "PrivateKey", None)
    if private_key_type is None:
        raise ValidationError(
            "hedera-sdk-py PrivateKey type unavailable for ledger authentication",
            ErrorContext(),
        )

    try:
        key = private_key_type.fromString(private_key.strip())
    except Exception as exc:
        raise ValidationError(
            "invalid Hedera private key for ledger authentication",
            ErrorContext(details={"reason": str(exc)}),
        ) from exc

    try:
        signature = bytes(key.sign(message.encode("utf-8")))
        signature_b64 = base64.b64encode(signature).decode("utf-8")
        public_key = key.getPublicKey().toString()
    except Exception as exc:
        raise ValidationError(
            "failed to sign ledger challenge",
            ErrorContext(details={"reason": str(exc)}),
        ) from exc
    return signature_b64, public_key


def authenticate_with_ledger_credentials(
    *,
    base_url: str,
    account_id: str,
    private_key: str,
    network: str = "testnet",
    expires_in_minutes: int | None = None,
) -> str:
    """Authenticate against Registry Broker ledger auth and return API key."""

    normalized_account_id = account_id.strip()
    normalized_private_key = private_key.strip()
    if not normalized_account_id:
        raise ValidationError("ledger account_id is required", ErrorContext())
    if not normalized_private_key:
        raise ValidationError("ledger private_key is required", ErrorContext())

    resolved_network = _normalize_ledger_network(network)
    transport = SyncHttpTransport(
        base_url=base_url.rstrip("/"),
        timeout_seconds=DEFAULT_REGISTRY_TIMEOUT_MS / 1000.0,
    )
    try:
        challenge_raw = _request_registry_json_with_retry(
            transport,
            "POST",
            "/auth/ledger/challenge",
            body={"accountId": normalized_account_id, "network": resolved_network},
        )
        challenge = LedgerChallengeResponse.model_validate(challenge_raw)
        signature_b64, public_key = _sign_ledger_challenge(
            challenge.message,
            normalized_private_key,
        )
        verify_payload: JsonObject = {
            "challengeId": challenge.challenge_id,
            "accountId": normalized_account_id,
            "network": resolved_network,
            "signature": signature_b64,
            "signatureKind": "raw",
            "publicKey": public_key,
        }
        if expires_in_minutes is not None:
            verify_payload["expiresInMinutes"] = expires_in_minutes
        verify_raw = _request_registry_json_with_retry(
            transport,
            "POST",
            "/auth/ledger/verify",
            body=verify_payload,
        )
        verification = LedgerVerifyResponse.model_validate(verify_raw)
    finally:
        transport.close()

    return verification.key


class BrokerInscriberClient:
    """Synchronous Registry Broker-backed inscriber client."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_REGISTRY_BROKER_URL,
        api_key: str,
        transport: SyncHttpTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValidationError("registry broker API key is required", ErrorContext())
        self._transport = transport or SyncHttpTransport(
            base_url=base_url.rstrip("/"),
            headers={"x-api-key": api_key.strip()},
            timeout_seconds=DEFAULT_REGISTRY_TIMEOUT_MS / 1000.0,
        )

    def create_quote(self, payload: BrokerQuoteRequest) -> BrokerQuoteResponse:
        raw = self._transport.request_json(
            "POST",
            "/inscribe/content/quote",
            body=payload.model_dump(by_alias=True, exclude_none=True),
        )
        return BrokerQuoteResponse.model_validate(raw)

    def create_job(self, payload: BrokerQuoteRequest) -> BrokerJobResponse:
        raw = self._transport.request_json(
            "POST",
            "/inscribe/content",
            body=payload.model_dump(by_alias=True, exclude_none=True),
        )
        return BrokerJobResponse.model_validate(raw)

    def get_job(self, job_id: str) -> BrokerJobResponse:
        raw = self._transport.request_json("GET", f"/inscribe/content/{job_id}")
        return BrokerJobResponse.model_validate(raw)

    def wait_for_job(
        self,
        job_id: str,
        *,
        timeout_ms: int = DEFAULT_REGISTRY_TIMEOUT_MS,
        poll_interval_ms: int = DEFAULT_REGISTRY_POLL_INTERVAL_MS,
    ) -> BrokerJobResponse:
        deadline = monotonic() + (max(timeout_ms, 1) / 1000.0)
        latest: BrokerJobResponse | None = None
        while monotonic() < deadline:
            try:
                latest = self.get_job(job_id)
            except Exception as exc:
                if _is_transient_registry_error(exc):
                    sleep(max(poll_interval_ms, 1) / 1000.0)
                    continue
                raise
            status = (latest.status or "").lower()
            if status == "completed":
                return latest
            if status == "failed":
                raise ValidationError(
                    latest.error or "registry broker inscription failed",
                    ErrorContext(details={"job_id": job_id}),
                )
            sleep(max(poll_interval_ms, 1) / 1000.0)
        if latest is None:
            raise ValidationError(
                "registry broker job was never fetched before timeout",
                ErrorContext(details={"job_id": job_id}),
            )
        raise ValidationError(
            "registry broker job did not complete before timeout",
            ErrorContext(details={"job_id": job_id, "status": latest.status}),
        )

    def inscribe_and_wait(
        self,
        payload: BrokerQuoteRequest,
        *,
        timeout_ms: int = DEFAULT_REGISTRY_TIMEOUT_MS,
        poll_interval_ms: int = DEFAULT_REGISTRY_POLL_INTERVAL_MS,
    ) -> InscribeViaBrokerResult:
        job: BrokerJobResponse | None = None
        for attempt in range(DEFAULT_REGISTRY_RETRY_COUNT):
            try:
                job = self.create_job(payload)
                break
            except Exception as exc:
                if attempt + 1 >= DEFAULT_REGISTRY_RETRY_COUNT or not _is_transient_registry_error(
                    exc
                ):
                    raise
                sleep(max(poll_interval_ms, 1) / 1000.0)
        if job is None:
            raise ValidationError("registry broker response missing job ID", ErrorContext())
        job_id = (job.job_id or job.id or "").strip()
        if not job_id:
            raise ValidationError("registry broker response missing job ID", ErrorContext())
        final = self.wait_for_job(
            job_id,
            timeout_ms=timeout_ms,
            poll_interval_ms=poll_interval_ms,
        )
        return InscribeViaBrokerResult(
            confirmed=(final.status or "").lower() == "completed",
            jobId=job_id,
            status=final.status or "unknown",
            hrl=final.hrl,
            topicId=final.topic_id,
            network=final.network,
            error=final.error,
            createdAt=final.created_at,
            updatedAt=final.updated_at,
        )


class AsyncBrokerInscriberClient:
    """Asynchronous Registry Broker-backed inscriber client."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_REGISTRY_BROKER_URL,
        api_key: str,
        transport: AsyncHttpTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValidationError("registry broker API key is required", ErrorContext())
        self._transport = transport or AsyncHttpTransport(
            base_url=base_url.rstrip("/"),
            headers={"x-api-key": api_key.strip()},
            timeout_seconds=DEFAULT_REGISTRY_TIMEOUT_MS / 1000.0,
        )

    async def create_quote(self, payload: BrokerQuoteRequest) -> BrokerQuoteResponse:
        raw = await self._transport.request_json(
            "POST",
            "/inscribe/content/quote",
            body=payload.model_dump(by_alias=True, exclude_none=True),
        )
        return BrokerQuoteResponse.model_validate(raw)

    async def create_job(self, payload: BrokerQuoteRequest) -> BrokerJobResponse:
        raw = await self._transport.request_json(
            "POST",
            "/inscribe/content",
            body=payload.model_dump(by_alias=True, exclude_none=True),
        )
        return BrokerJobResponse.model_validate(raw)

    async def get_job(self, job_id: str) -> BrokerJobResponse:
        raw = await self._transport.request_json("GET", f"/inscribe/content/{job_id}")
        return BrokerJobResponse.model_validate(raw)

    async def wait_for_job(
        self,
        job_id: str,
        *,
        timeout_ms: int = DEFAULT_REGISTRY_TIMEOUT_MS,
        poll_interval_ms: int = DEFAULT_REGISTRY_POLL_INTERVAL_MS,
    ) -> BrokerJobResponse:
        deadline = monotonic() + (max(timeout_ms, 1) / 1000.0)
        latest: BrokerJobResponse | None = None
        while monotonic() < deadline:
            try:
                latest = await self.get_job(job_id)
            except Exception as exc:
                if _is_transient_registry_error(exc):
                    await asyncio.sleep(max(poll_interval_ms, 1) / 1000.0)
                    continue
                raise
            status = (latest.status or "").lower()
            if status == "completed":
                return latest
            if status == "failed":
                raise ValidationError(
                    latest.error or "registry broker inscription failed",
                    ErrorContext(details={"job_id": job_id}),
                )
            await asyncio.sleep(max(poll_interval_ms, 1) / 1000.0)
        if latest is None:
            raise ValidationError(
                "registry broker job was never fetched before timeout",
                ErrorContext(details={"job_id": job_id}),
            )
        raise ValidationError(
            "registry broker job did not complete before timeout",
            ErrorContext(details={"job_id": job_id, "status": latest.status}),
        )

    async def inscribe_and_wait(
        self,
        payload: BrokerQuoteRequest,
        *,
        timeout_ms: int = DEFAULT_REGISTRY_TIMEOUT_MS,
        poll_interval_ms: int = DEFAULT_REGISTRY_POLL_INTERVAL_MS,
    ) -> InscribeViaBrokerResult:
        job: BrokerJobResponse | None = None
        for attempt in range(DEFAULT_REGISTRY_RETRY_COUNT):
            try:
                job = await self.create_job(payload)
                break
            except Exception as exc:
                if attempt + 1 >= DEFAULT_REGISTRY_RETRY_COUNT or not _is_transient_registry_error(
                    exc
                ):
                    raise
                await asyncio.sleep(max(poll_interval_ms, 1) / 1000.0)
        if job is None:
            raise ValidationError("registry broker response missing job ID", ErrorContext())
        job_id = (job.job_id or job.id or "").strip()
        if not job_id:
            raise ValidationError("registry broker response missing job ID", ErrorContext())
        final = await self.wait_for_job(
            job_id,
            timeout_ms=timeout_ms,
            poll_interval_ms=poll_interval_ms,
        )
        return InscribeViaBrokerResult(
            confirmed=(final.status or "").lower() == "completed",
            jobId=job_id,
            status=final.status or "unknown",
            hrl=final.hrl,
            topicId=final.topic_id,
            network=final.network,
            error=final.error,
            createdAt=final.created_at,
            updatedAt=final.updated_at,
        )

    async def close(self) -> None:
        await self._transport.close()


class InscriberClient:
    """Synchronous inscriber client."""

    def __init__(self, broker_client: RegistryBrokerClient | None = None) -> None:
        self._broker_client = broker_client

    def get_registry_broker_quote(
        self,
        input_payload: InscriptionInput,
        options: InscribeViaRegistryBrokerOptions,
    ) -> BrokerQuoteResponse:
        request = _build_quote_request(input_payload, options)
        client = BrokerInscriberClient(
            base_url=options.base_url,
            api_key=_resolve_api_key(options),
        )
        return client.create_quote(request)

    def inscribe_via_registry_broker(
        self,
        input_payload: InscriptionInput,
        options: InscribeViaRegistryBrokerOptions,
    ) -> InscribeViaBrokerResult:
        request = _build_quote_request(input_payload, options)
        client = BrokerInscriberClient(
            base_url=options.base_url,
            api_key=_resolve_api_key(options),
        )
        if not options.wait_for_confirmation:
            job = client.create_job(request)
            job_id = (job.job_id or job.id or "").strip()
            return InscribeViaBrokerResult(
                confirmed=False,
                jobId=job_id,
                status=job.status or "pending",
                hrl=job.hrl,
                topicId=job.topic_id,
                network=job.network,
                error=job.error,
                createdAt=job.created_at,
                updatedAt=job.updated_at,
            )
        return client.inscribe_and_wait(
            request,
            timeout_ms=options.wait_timeout_ms,
            poll_interval_ms=options.poll_interval_ms,
        )

    def inscribe_skill_via_registry_broker(
        self,
        input_payload: InscriptionInput,
        options: InscribeViaRegistryBrokerOptions,
        *,
        skill_name: str | None = None,
        skill_version: str | None = None,
    ) -> InscribeViaBrokerResult:
        metadata = dict(options.metadata or {})
        metadata["kind"] = "skill"
        if skill_name:
            metadata["skillName"] = skill_name.strip()
        if skill_version:
            metadata["skillVersion"] = skill_version.strip()
        skill_options = InscribeViaRegistryBrokerOptions(
            base_url=options.base_url,
            api_key=options.api_key,
            ledger_api_key=options.ledger_api_key,
            ledger_account_id=options.ledger_account_id,
            ledger_private_key=options.ledger_private_key,
            ledger_network=options.ledger_network,
            ledger_expires_in_minutes=options.ledger_expires_in_minutes,
            mode="bulk-files",
            metadata=metadata,
            tags=options.tags,
            file_standard=options.file_standard,
            chunk_size=options.chunk_size,
            wait_for_confirmation=options.wait_for_confirmation,
            wait_timeout_ms=options.wait_timeout_ms,
            poll_interval_ms=options.poll_interval_ms,
        )
        return self.inscribe_via_registry_broker(input_payload, skill_options)

    def generate_quote(self, payload: JsonObject) -> InscriptionResponse:
        if self._broker_client is None:
            raise ValidationError(
                "broker-backed generate_quote requires RegistryBrokerClient",
                ErrorContext(),
            )
        raw = self._broker_client.call_operation("quote_skill_publish", body=payload)
        return InscriptionResponse(quote=True, result=raw)

    def publish(self, payload: JsonObject) -> InscriptionResponse:
        if self._broker_client is None:
            raise ValidationError(
                "broker-backed publish requires RegistryBrokerClient",
                ErrorContext(),
            )
        raw = self._broker_client.call_operation("publish_skill", body=payload)
        return InscriptionResponse(confirmed=False, result=raw)


class AsyncInscriberClient:
    """Asynchronous inscriber client."""

    def __init__(self, broker_client: AsyncRegistryBrokerClient | None = None) -> None:
        self._broker_client = broker_client

    async def get_registry_broker_quote(
        self,
        input_payload: InscriptionInput,
        options: InscribeViaRegistryBrokerOptions,
    ) -> BrokerQuoteResponse:
        request = _build_quote_request(input_payload, options)
        client = AsyncBrokerInscriberClient(
            base_url=options.base_url,
            api_key=_resolve_api_key(options),
        )
        return await client.create_quote(request)

    async def inscribe_via_registry_broker(
        self,
        input_payload: InscriptionInput,
        options: InscribeViaRegistryBrokerOptions,
    ) -> InscribeViaBrokerResult:
        request = _build_quote_request(input_payload, options)
        client = AsyncBrokerInscriberClient(
            base_url=options.base_url,
            api_key=_resolve_api_key(options),
        )
        if not options.wait_for_confirmation:
            job = await client.create_job(request)
            job_id = (job.job_id or job.id or "").strip()
            return InscribeViaBrokerResult(
                confirmed=False,
                jobId=job_id,
                status=job.status or "pending",
                hrl=job.hrl,
                topicId=job.topic_id,
                network=job.network,
                error=job.error,
                createdAt=job.created_at,
                updatedAt=job.updated_at,
            )
        return await client.inscribe_and_wait(
            request,
            timeout_ms=options.wait_timeout_ms,
            poll_interval_ms=options.poll_interval_ms,
        )

    async def generate_quote(self, payload: JsonObject) -> InscriptionResponse:
        if self._broker_client is None:
            raise ValidationError(
                "broker-backed generate_quote requires AsyncRegistryBrokerClient",
                ErrorContext(),
            )
        raw = await self._broker_client.call_operation("quote_skill_publish", body=payload)
        return InscriptionResponse(quote=True, result=raw)

    async def publish(self, payload: JsonObject) -> InscriptionResponse:
        if self._broker_client is None:
            raise ValidationError(
                "broker-backed publish requires AsyncRegistryBrokerClient",
                ErrorContext(),
            )
        raw = await self._broker_client.call_operation("publish_skill", body=payload)
        return InscriptionResponse(confirmed=False, result=raw)


def get_registry_broker_quote(
    input_payload: InscriptionInput,
    options: InscribeViaRegistryBrokerOptions,
) -> BrokerQuoteResponse:
    """TypeScript-compatible top-level quote helper."""

    return InscriberClient().get_registry_broker_quote(input_payload, options)


def inscribe_via_registry_broker(
    input_payload: InscriptionInput,
    options: InscribeViaRegistryBrokerOptions,
) -> InscribeViaBrokerResult:
    """TypeScript-compatible top-level broker inscription helper."""

    return InscriberClient().inscribe_via_registry_broker(input_payload, options)


def inscribe(
    input_payload: InscriptionInput,
    options: InscribeViaRegistryBrokerOptions,
) -> InscribeViaBrokerResult:
    """Top-level inscribe helper with parity to TypeScript `inscribe`."""

    return inscribe_via_registry_broker(input_payload, options)


def inscribe_with_signer(
    input_payload: InscriptionInput,
    options: InscribeViaRegistryBrokerOptions,
    *,
    signer: object | None = None,
) -> InscribeViaBrokerResult:
    """Parity wrapper for TypeScript `inscribeWithSigner`."""

    del signer
    return inscribe_via_registry_broker(input_payload, options)


def retrieve_inscription(
    job_id: str,
    options: InscribeViaRegistryBrokerOptions,
) -> BrokerJobResponse:
    """Fetch a Registry Broker inscription job by ID."""

    client = BrokerInscriberClient(
        base_url=options.base_url,
        api_key=_resolve_api_key(options),
    )
    return client.get_job(job_id)


def wait_for_inscription_confirmation(
    job_id: str,
    options: InscribeViaRegistryBrokerOptions,
) -> InscribeViaBrokerResult:
    """Wait for inscription completion and normalize result shape."""

    client = BrokerInscriberClient(
        base_url=options.base_url,
        api_key=_resolve_api_key(options),
    )
    final = client.wait_for_job(
        job_id,
        timeout_ms=options.wait_timeout_ms,
        poll_interval_ms=options.poll_interval_ms,
    )
    return InscribeViaBrokerResult(
        confirmed=(final.status or "").lower() == "completed",
        jobId=job_id,
        status=final.status or "unknown",
        hrl=final.hrl,
        topicId=final.topic_id,
        network=final.network,
        error=final.error,
        createdAt=final.created_at,
        updatedAt=final.updated_at,
    )


def generate_quote(
    input_payload: InscriptionInput,
    options: InscribeViaRegistryBrokerOptions,
) -> BrokerQuoteResponse:
    """Top-level quote helper matching TypeScript `generateQuote`."""

    return get_registry_broker_quote(input_payload, options)
