"""Inscriber clients and explicit Registry Broker workflows."""

from __future__ import annotations

import asyncio
import base64
import importlib
import json
import mimetypes
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from time import monotonic, sleep
from typing import Literal, cast

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
ConnectionMode = Literal["http", "websocket", "auto"]

DEFAULT_INSCRIBER_AUTH_URL = "https://kiloscribe.com"
DEFAULT_INSCRIBER_API_URL = "https://v2-api.tier.bot/api"
DEFAULT_REGISTRY_BROKER_URL = "https://hol.org/registry/api/v1"
DEFAULT_INSCRIBER_TIMEOUT_MS = 120000
DEFAULT_INSCRIBER_POLL_INTERVAL_MS = 2000
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
    job_id: str | None = Field(default=None, alias="jobId")
    status: str | None = None
    hrl: str | None = None
    topic_id: str | None = Field(default=None, alias="topicId")
    network: str | None = None
    error: str | None = None
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")
    result: object | None = None
    inscription: object | None = None
    cost_summary: object | None = Field(default=None, alias="costSummary")


@dataclass(slots=True, frozen=True)
class HederaClientConfig:
    """Inscriber-compatible Hedera signer configuration."""

    account_id: str
    private_key: str
    network: str = "mainnet"


@dataclass(slots=True, frozen=True)
class InscriptionOptions:
    """Inscriber options."""

    mode: InscriptionMode = "file"
    websocket: bool | None = None
    connection_mode: ConnectionMode | None = None
    wait_for_confirmation: bool = True
    wait_max_attempts: int = 450
    wait_interval_ms: int = 4000
    api_key: str | None = None
    base_url: str | None = None
    auth_base_url: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, object] | None = None
    json_file_url: str | None = None
    file_standard: str | None = None
    chunk_size: int | None = None
    network: str | None = None
    quote_only: bool = False


class AuthResult(BaseModel):
    """Inscriber auth response."""

    api_key: str = Field(alias="apiKey")


class InscriberQuoteTransfer(BaseModel):
    """Inscriber quote transfer entry."""

    to: str
    amount: str
    description: str


class InscriberQuoteBreakdown(BaseModel):
    """Inscriber quote breakdown."""

    transfers: list[InscriberQuoteTransfer]


class InscriberQuoteResult(BaseModel):
    """Inscriber quote result."""

    total_cost_hbar: str = Field(alias="totalCostHbar")
    valid_until: str = Field(alias="validUntil")
    breakdown: InscriberQuoteBreakdown


class InscriberJob(BaseModel):
    """Inscriber job."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    status: str | None = None
    completed: bool = False
    tx_id: str | None = Field(default=None, alias="tx_id")
    topic_id: str | None = Field(default=None, alias="topic_id")
    transaction_id: str | None = Field(default=None, alias="transactionId")
    transaction_bytes: str | None = Field(default=None, alias="transactionBytes")
    error: str | None = None
    total_cost: int | None = Field(default=None, alias="totalCost")
    total_messages: int | None = Field(default=None, alias="totalMessages")


def _guess_mime_type(file_name: str) -> str:
    guessed, _encoding = mimetypes.guess_type(file_name, strict=False)
    return guessed or "application/octet-stream"


def _normalize_network(network: str) -> str:
    aliases = {
        "mainnet": "mainnet",
        "hedera:mainnet": "mainnet",
        "hedera-mainnet": "mainnet",
        "hedera_mainnet": "mainnet",
        "testnet": "testnet",
        "hedera:testnet": "testnet",
        "hedera-testnet": "testnet",
        "hedera_testnet": "testnet",
    }
    normalized = aliases.get(network.strip().lower(), network.strip().lower())
    if normalized not in {"mainnet", "testnet"}:
        raise ValidationError(
            "network must be testnet or mainnet",
            ErrorContext(details={"network": network}),
        )
    return normalized


def _normalize_inscriber_auth_url(base_url: str | None) -> str:
    normalized = (base_url or DEFAULT_INSCRIBER_AUTH_URL).strip().rstrip("/")
    if normalized.endswith("/api"):
        normalized = normalized[: -len("/api")]
    return normalized or DEFAULT_INSCRIBER_AUTH_URL


def _normalize_inscriber_api_url(base_url: str | None) -> str:
    normalized = (base_url or DEFAULT_INSCRIBER_API_URL).strip().rstrip("/")
    if normalized.endswith("/api"):
        return normalized
    return f"{normalized}/api"


def _resolve_connection_mode(options: InscriptionOptions) -> ConnectionMode:
    if options.connection_mode is not None:
        return options.connection_mode
    if isinstance(options.websocket, bool):
        return "websocket" if options.websocket else "http"
    return "websocket"


def _normalize_transaction_id(tx_id: str) -> str:
    trimmed = tx_id.strip()
    if "@" not in trimmed:
        return trimmed
    account_id, valid_start = trimmed.split("@", 1)
    return f"{account_id}-{valid_start.replace('.', '-')}"


def _normalize_transaction_bytes(raw_value: object) -> str:
    if raw_value is None:
        return ""
    if isinstance(raw_value, str):
        return raw_value
    if isinstance(raw_value, Mapping):
        type_value = raw_value.get("type")
        data = raw_value.get("data")
        if type_value != "Buffer" or not isinstance(data, list):
            raise ParseError(
                "unsupported transactionBytes object shape",
                ErrorContext(details={"type": type_value}),
            )
        byte_values = bytearray()
        for item in data:
            if not isinstance(item, int | float):
                raise ParseError(
                    "transactionBytes Buffer object includes non-numeric data",
                    ErrorContext(details={"value_type": type(item).__name__}),
                )
            byte_values.append(int(item))
        return base64.b64encode(bytes(byte_values)).decode("utf-8")
    raise ParseError(
        "unsupported transactionBytes value",
        ErrorContext(details={"value_type": type(raw_value).__name__}),
    )


def _normalize_auth_challenge(raw_message: object) -> tuple[str, JsonValue]:
    if isinstance(raw_message, str):
        normalized = raw_message.strip()
        if not normalized:
            raise ValidationError("signature challenge string cannot be empty", ErrorContext())
        return normalized, normalized
    try:
        normalized = json.dumps(raw_message, separators=(",", ":"))
        normalized_payload = cast(JsonValue, json.loads(normalized))
    except Exception as exc:
        raise ParseError(
            "failed to normalize signature challenge",
            ErrorContext(details={"reason": str(exc)}),
        ) from exc
    if not normalized:
        raise ValidationError("signature challenge cannot be empty", ErrorContext())
    return normalized, normalized_payload


def _sign_inscriber_challenge(signing_payload: str, private_key: str) -> str:
    try:
        hedera_module = importlib.import_module("hedera")
        key = hedera_module.PrivateKey.fromString(private_key.strip())
    except ModuleNotFoundError as exc:
        raise ValidationError(
            "hedera-sdk-py is required for inscriber authentication",
            ErrorContext(details={"dependency": "hedera-sdk-py"}),
        ) from exc
    except Exception as exc:
        raise ValidationError(
            "invalid Hedera private key for inscriber authentication",
            ErrorContext(details={"reason": str(exc)}),
        ) from exc
    return bytes(key.sign(signing_payload.encode("utf-8"))).hex()


def _build_inscriber_request_body(
    input_payload: InscriptionInput,
    holder_id: str,
    network: str,
    options: InscriptionOptions,
) -> JsonObject:
    body: JsonObject = {
        "holderId": holder_id,
        "mode": options.mode,
        "network": network,
    }
    if options.metadata:
        body["metadata"] = cast(JsonObject, options.metadata)
    if options.tags:
        body["tags"] = cast(JsonValue, options.tags)
    if options.chunk_size:
        body["chunkSize"] = options.chunk_size
    if options.file_standard:
        body["fileStandard"] = options.file_standard
    if options.json_file_url:
        body["jsonFileURL"] = options.json_file_url

    if input_payload.type == "url":
        if not input_payload.url or not input_payload.url.strip():
            raise ValidationError("input.url is required for url input type", ErrorContext())
        body["fileURL"] = input_payload.url.strip()
        return body

    if input_payload.type == "file":
        if not input_payload.path:
            raise ValidationError("input.path is required for file input type", ErrorContext())
        file_path = Path(input_payload.path)
        if not file_path.exists():
            raise ValidationError(
                "input.path does not exist",
                ErrorContext(details={"path": str(file_path)}),
            )
        content = file_path.read_bytes()
        body["fileBase64"] = base64.b64encode(content).decode("utf-8")
        body["fileName"] = file_path.name
        body["fileMimeType"] = _guess_mime_type(file_path.name)
        return body

    if input_payload.type == "buffer":
        if not input_payload.buffer:
            raise ValidationError("input.buffer is required for buffer input type", ErrorContext())
        if not input_payload.file_name:
            raise ValidationError(
                "input.fileName is required for buffer input type", ErrorContext()
            )
        body["fileBase64"] = base64.b64encode(input_payload.buffer).decode("utf-8")
        body["fileName"] = input_payload.file_name
        mime_type = input_payload.mime_type or _guess_mime_type(input_payload.file_name)
        if mime_type:
            body["fileMimeType"] = mime_type
        return body

    raise ValidationError(
        "input.type must be one of: url, file, buffer",
        ErrorContext(details={"input_type": input_payload.type}),
    )


def _parse_inscriber_job(raw: JsonValue) -> InscriberJob:
    if not isinstance(raw, dict):
        raise ParseError(
            "failed to parse inscription job",
            ErrorContext(details={"payload_type": type(raw).__name__}),
        )
    payload = dict(raw)
    payload["transactionBytes"] = _normalize_transaction_bytes(raw.get("transactionBytes"))
    return InscriberJob.model_validate(payload)


def _parse_inscriber_quote(job: InscriberJob) -> InscriberQuoteResult:
    total_cost_hbar = "0.001"
    total_cost = job.total_cost or 0
    if total_cost > 0:
        total_cost_hbar = format(total_cost / 100_000_000, "g")
    return InscriberQuoteResult(
        totalCostHbar=total_cost_hbar,
        validUntil="",
        breakdown=InscriberQuoteBreakdown(
            transfers=[
                InscriberQuoteTransfer(
                    to="Inscription Service",
                    amount=total_cost_hbar,
                    description="Inscription fee",
                )
            ]
        ),
    )


def _coerce_hedera_client_config(value: object) -> HederaClientConfig:
    if isinstance(value, HederaClientConfig):
        return value
    if isinstance(value, Mapping):
        account_id = str(value.get("accountId", value.get("account_id", ""))).strip()
        private_key = str(value.get("privateKey", value.get("private_key", ""))).strip()
        network = str(value.get("network", "mainnet")).strip() or "mainnet"
        if not account_id:
            raise ValidationError("accountId is required", ErrorContext())
        if not private_key:
            raise ValidationError("privateKey is required", ErrorContext())
        return HederaClientConfig(
            account_id=account_id,
            private_key=private_key,
            network=_normalize_network(network),
        )
    raise ValidationError(
        "client config must be a HederaClientConfig or mapping",
        ErrorContext(details={"type": type(value).__name__}),
    )


def _coerce_inscription_options(value: object | None) -> InscriptionOptions:
    if value is None:
        return InscriptionOptions()
    if isinstance(value, InscriptionOptions):
        return value
    if isinstance(value, Mapping):
        payload = dict(value)
        return InscriptionOptions(
            mode=cast(InscriptionMode, payload.get("mode", "file")),
            websocket=cast(bool | None, payload.get("websocket")),
            connection_mode=cast(
                ConnectionMode | None, payload.get("connectionMode", payload.get("connection_mode"))
            ),
            wait_for_confirmation=bool(
                payload.get("waitForConfirmation", payload.get("wait_for_confirmation", True))
            ),
            wait_max_attempts=int(
                payload.get("waitMaxAttempts", payload.get("wait_max_attempts", 450))
            ),
            wait_interval_ms=int(
                payload.get("waitIntervalMs", payload.get("wait_interval_ms", 4000))
            ),
            api_key=cast(str | None, payload.get("apiKey", payload.get("api_key"))),
            base_url=cast(str | None, payload.get("baseURL", payload.get("base_url"))),
            auth_base_url=cast(
                str | None, payload.get("authBaseURL", payload.get("auth_base_url"))
            ),
            tags=cast(list[str] | None, payload.get("tags")),
            metadata=cast(dict[str, object] | None, payload.get("metadata")),
            json_file_url=cast(
                str | None, payload.get("jsonFileURL", payload.get("json_file_url"))
            ),
            file_standard=cast(
                str | None, payload.get("fileStandard", payload.get("file_standard"))
            ),
            chunk_size=cast(int | None, payload.get("chunkSize", payload.get("chunk_size"))),
            network=cast(str | None, payload.get("network")),
            quote_only=bool(payload.get("quoteOnly", payload.get("quote_only", False))),
        )
    raise ValidationError(
        "inscription options must be an InscriptionOptions or mapping",
        ErrorContext(details={"type": type(value).__name__}),
    )


def _coerce_legacy_inscriber_inputs(
    options: InscribeViaRegistryBrokerOptions,
) -> tuple[HederaClientConfig, InscriptionOptions]:
    account_id = (options.ledger_account_id or "").strip()
    private_key = (options.ledger_private_key or "").strip()
    if not account_id or not private_key:
        raise ValidationError(
            "ledger_account_id and ledger_private_key are required for inscriber operations",
            ErrorContext(),
        )
    client_config = HederaClientConfig(
        account_id=account_id,
        private_key=private_key,
        network=_normalize_network(options.ledger_network or "mainnet"),
    )
    inscription_options = InscriptionOptions(
        mode=options.mode,
        wait_for_confirmation=options.wait_for_confirmation,
        wait_interval_ms=options.poll_interval_ms,
        wait_max_attempts=max(options.wait_timeout_ms // max(options.poll_interval_ms, 1), 1),
        api_key=(options.api_key or options.ledger_api_key),
        base_url=options.base_url,
        metadata=options.metadata,
        tags=options.tags,
        file_standard=options.file_standard,
        chunk_size=options.chunk_size,
        network=client_config.network,
    )
    return client_config, inscription_options


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


class AuthClient:
    """Inscriber authentication client."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_INSCRIBER_AUTH_URL,
        transport: SyncHttpTransport | None = None,
    ) -> None:
        normalized_base_url = _normalize_inscriber_auth_url(base_url)
        self._transport = transport or SyncHttpTransport(
            base_url=normalized_base_url,
            timeout_seconds=DEFAULT_INSCRIBER_TIMEOUT_MS / 1000.0,
        )

    def authenticate(self, account_id: str, private_key: str, network: str) -> AuthResult:
        normalized_account_id = account_id.strip()
        normalized_network = _normalize_network(network)
        challenge_raw = self._transport.request_json(
            "GET",
            "/api/auth/request-signature",
            headers={"x-session": normalized_account_id},
        )
        if not isinstance(challenge_raw, dict) or "message" not in challenge_raw:
            raise ParseError("signature challenge did not include message", ErrorContext())
        signing_payload, auth_data_value = _normalize_auth_challenge(challenge_raw["message"])
        signature_hex = _sign_inscriber_challenge(signing_payload, private_key)
        auth_raw = self._transport.request_json(
            "POST",
            "/api/auth/authenticate",
            body={
                "authData": {
                    "id": normalized_account_id,
                    "signature": signature_hex,
                    "data": auth_data_value,
                    "network": normalized_network,
                },
                "include": "apiKey",
            },
            headers={"content-type": "application/json"},
        )
        if not isinstance(auth_raw, dict):
            raise ParseError("failed to decode inscriber auth response", ErrorContext())
        user_value = auth_raw.get("user")
        session_token = user_value.get("sessionToken") if isinstance(user_value, dict) else None
        result = AuthResult.model_validate(auth_raw)
        if not isinstance(session_token, str) or not session_token.strip():
            raise ParseError("authenticate response did not include session token", ErrorContext())
        if not result.api_key.strip():
            raise ParseError("authenticate response did not include api key", ErrorContext())
        return result


class Client:
    """Inscriber HTTP client."""

    def __init__(
        self,
        *,
        api_key: str,
        network: str,
        base_url: str = DEFAULT_INSCRIBER_API_URL,
        transport: SyncHttpTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValidationError("API key is required", ErrorContext())
        self.network = _normalize_network(network)
        normalized_base_url = _normalize_inscriber_api_url(base_url)
        self._transport = transport or SyncHttpTransport(
            base_url=normalized_base_url,
            headers={"x-api-key": api_key.strip()},
            timeout_seconds=DEFAULT_INSCRIBER_TIMEOUT_MS / 1000.0,
        )

    def start_inscription(self, request: JsonObject) -> InscriberJob:
        raw = self._transport.request_json(
            "POST",
            "/inscriptions/start-inscription",
            body=request,
        )
        return _parse_inscriber_job(raw)

    def retrieve_inscription(self, transaction_id: str) -> InscriberJob:
        normalized_transaction_id = _normalize_transaction_id(transaction_id)
        if not normalized_transaction_id:
            raise ValidationError("transaction ID is required", ErrorContext())
        raw = self._transport.request_json(
            "GET",
            "/inscriptions/retrieve-inscription",
            query={"id": normalized_transaction_id},
        )
        return _parse_inscriber_job(raw)

    def wait_for_inscription(
        self,
        transaction_id: str,
        *,
        max_attempts: int,
        interval_ms: int,
    ) -> InscriberJob:
        attempts = max(max_attempts, 1)
        wait_interval_ms = max(interval_ms, 1)
        latest: InscriberJob | None = None
        for _attempt in range(attempts):
            latest = self.retrieve_inscription(transaction_id)
            status = (latest.status or "").lower()
            if latest.completed or status == "completed":
                latest.completed = True
                return latest
            if status == "failed":
                raise ValidationError(latest.error or "inscription failed", ErrorContext())
            sleep(wait_interval_ms / 1000.0)
        if latest is None:
            raise ValidationError("inscription status was never fetched", ErrorContext())
        raise ValidationError("inscription did not complete before timeout", ErrorContext())


def _execute_inscriber_transaction(
    transaction_bytes: str,
    client_config: HederaClientConfig,
) -> str:
    try:
        hedera_module = importlib.import_module("hedera")
    except ModuleNotFoundError as exc:
        raise ValidationError(
            "hedera-sdk-py is required for inscriber operations",
            ErrorContext(details={"dependency": "hedera-sdk-py"}),
        ) from exc
    try:
        private_key = hedera_module.PrivateKey.fromString(client_config.private_key.strip())
        account_id = hedera_module.AccountId.fromString(client_config.account_id.strip())
        client = (
            hedera_module.Client.forMainnet()
            if _normalize_network(client_config.network) == "mainnet"
            else hedera_module.Client.forTestnet()
        )
        client.setOperator(account_id, private_key)
        transaction = hedera_module.Transaction.fromBytes(base64.b64decode(transaction_bytes))
    except Exception as exc:
        raise ValidationError(
            "failed to prepare inscriber transaction",
            ErrorContext(details={"reason": str(exc)}),
        ) from exc
    try:
        response = transaction.execute(client)
    except Exception:
        try:
            signed = hedera_module.Transaction.fromBytes(base64.b64decode(transaction_bytes))
            signed.sign(private_key)
            response = signed.execute(client)
        except Exception as exc:
            raise TransportError(
                "failed to execute inscriber transaction",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc
    transaction_id = getattr(response, "transactionId", None)
    return str(transaction_id) if transaction_id is not None else ""


def _resolve_inscriber_client(
    client_config: HederaClientConfig,
    options: InscriptionOptions,
    existing_client: Client | None,
) -> Client:
    if existing_client is not None:
        return existing_client
    api_key = (options.api_key or "").strip()
    if not api_key:
        auth_result = AuthClient(
            base_url=options.auth_base_url or DEFAULT_INSCRIBER_AUTH_URL
        ).authenticate(
            client_config.account_id,
            client_config.private_key,
            options.network or client_config.network,
        )
        api_key = auth_result.api_key
    return Client(
        api_key=api_key,
        network=options.network or client_config.network,
        base_url=options.base_url or DEFAULT_INSCRIBER_API_URL,
    )


def _inscribe_with_inscriber(
    input_payload: InscriptionInput,
    client_config: HederaClientConfig,
    options: InscriptionOptions,
    existing_client: Client | None = None,
) -> InscriptionResponse:
    client = _resolve_inscriber_client(client_config, options, existing_client)
    request = _build_inscriber_request_body(
        input_payload,
        client_config.account_id,
        options.network or client_config.network,
        options,
    )
    job = client.start_inscription(request)
    if options.quote_only:
        quote = _parse_inscriber_quote(job)
        return InscriptionResponse(
            confirmed=False, quote=True, result=quote.model_dump(by_alias=True)
        )
    if not job.transaction_bytes:
        raise ParseError("inscription start did not return transaction bytes", ErrorContext())
    executed_transaction_id = _execute_inscriber_transaction(job.transaction_bytes, client_config)
    wait_id = _normalize_transaction_id(
        job.tx_id or job.id or job.transaction_id or executed_transaction_id
    )
    result = {
        "jobId": wait_id,
        "transactionId": _normalize_transaction_id(executed_transaction_id),
        "topicId": job.topic_id,
        "status": job.status,
        "completed": False,
    }
    if not options.wait_for_confirmation:
        return InscriptionResponse(confirmed=False, result=result)
    waited = client.wait_for_inscription(
        wait_id,
        max_attempts=options.wait_max_attempts,
        interval_ms=options.wait_interval_ms,
    )
    result["topicId"] = waited.topic_id or result["topicId"]
    result["status"] = waited.status or result["status"]
    result["completed"] = waited.completed
    return InscriptionResponse(
        confirmed=waited.completed or (waited.status or "").lower() == "completed",
        result=result,
        inscription=waited.model_dump(by_alias=True, exclude_none=True),
    )


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

    def inscribe(
        self,
        input_payload: InscriptionInput,
        client_config: HederaClientConfig,
        options: InscriptionOptions,
        existing_client: Client | None = None,
    ) -> InscriptionResponse:
        return _inscribe_with_inscriber(input_payload, client_config, options, existing_client)


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

    async def inscribe(
        self,
        input_payload: InscriptionInput,
        client_config: HederaClientConfig,
        options: InscriptionOptions,
        existing_client: Client | None = None,
    ) -> InscriptionResponse:
        return await asyncio.to_thread(
            _inscribe_with_inscriber,
            input_payload,
            client_config,
            options,
            existing_client,
        )


def _resolve_inscriber_invocation(
    client_config_or_options: object,
    options: object | None,
) -> tuple[HederaClientConfig, InscriptionOptions]:
    if isinstance(client_config_or_options, InscribeViaRegistryBrokerOptions):
        if options is not None:
            raise ValidationError(
                "legacy inscribe invocation does not accept a third positional options argument",
                ErrorContext(),
            )
        return _coerce_legacy_inscriber_inputs(client_config_or_options)
    client_config = _coerce_hedera_client_config(client_config_or_options)
    inscription_options = _coerce_inscription_options(options)
    if inscription_options.network is None:
        inscription_options = InscriptionOptions(
            mode=inscription_options.mode,
            websocket=inscription_options.websocket,
            connection_mode=inscription_options.connection_mode,
            wait_for_confirmation=inscription_options.wait_for_confirmation,
            wait_max_attempts=inscription_options.wait_max_attempts,
            wait_interval_ms=inscription_options.wait_interval_ms,
            api_key=inscription_options.api_key,
            base_url=inscription_options.base_url,
            auth_base_url=inscription_options.auth_base_url,
            tags=inscription_options.tags,
            metadata=inscription_options.metadata,
            json_file_url=inscription_options.json_file_url,
            file_standard=inscription_options.file_standard,
            chunk_size=inscription_options.chunk_size,
            network=client_config.network,
            quote_only=inscription_options.quote_only,
        )
    return client_config, inscription_options


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
    client_config_or_options: (
        HederaClientConfig | InscribeViaRegistryBrokerOptions | Mapping[str, object]
    ),
    options: InscriptionOptions | Mapping[str, object] | None = None,
    existing_client: Client | None = None,
) -> InscriptionResponse:
    """Top-level inscribe helper with legacy two-argument support."""

    client_config, inscription_options = _resolve_inscriber_invocation(
        client_config_or_options,
        options,
    )
    return _inscribe_with_inscriber(
        input_payload,
        client_config,
        inscription_options,
        existing_client,
    )


def inscribe_with_signer(
    input_payload: InscriptionInput,
    client_config_or_options: (
        HederaClientConfig | InscribeViaRegistryBrokerOptions | Mapping[str, object]
    ),
    options: InscriptionOptions | Mapping[str, object] | None = None,
    *,
    signer: object | None = None,
) -> InscriptionResponse:
    """Parity wrapper for TypeScript `inscribeWithSigner`."""

    del signer
    return inscribe(input_payload, client_config_or_options, options)


def retrieve_inscription(
    transaction_id: str,
    options: InscribeViaRegistryBrokerOptions | Mapping[str, object],
) -> InscriberJob:
    """Fetch an inscription job by transaction ID."""

    if isinstance(options, InscribeViaRegistryBrokerOptions):
        client_config, inscription_options = _coerce_legacy_inscriber_inputs(options)
    else:
        payload = options
        client_config = _coerce_hedera_client_config(payload.get("clientConfig", payload))
        inscription_options = _coerce_inscription_options(payload.get("options", payload))
    client = _resolve_inscriber_client(client_config, inscription_options, None)
    return client.retrieve_inscription(transaction_id)


def wait_for_inscription_confirmation(
    transaction_id: str,
    options: InscribeViaRegistryBrokerOptions | Mapping[str, object],
) -> InscriberJob:
    """Wait for inscription completion."""

    if isinstance(options, InscribeViaRegistryBrokerOptions):
        client_config, inscription_options = _coerce_legacy_inscriber_inputs(options)
    else:
        payload = options
        client_config = _coerce_hedera_client_config(payload.get("clientConfig", payload))
        inscription_options = _coerce_inscription_options(payload.get("options", payload))
    client = _resolve_inscriber_client(client_config, inscription_options, None)
    return client.wait_for_inscription(
        transaction_id,
        max_attempts=inscription_options.wait_max_attempts,
        interval_ms=inscription_options.wait_interval_ms,
    )


def generate_quote(
    input_payload: InscriptionInput,
    client_config_or_options: (
        HederaClientConfig | InscribeViaRegistryBrokerOptions | Mapping[str, object]
    ),
    options: InscriptionOptions | Mapping[str, object] | None = None,
    existing_client: Client | None = None,
) -> InscriberQuoteResult:
    """Top-level quote helper matching TypeScript `generateQuote`."""

    client_config, inscription_options = _resolve_inscriber_invocation(
        client_config_or_options,
        options,
    )
    quote_options = InscriptionOptions(
        mode=inscription_options.mode,
        websocket=inscription_options.websocket,
        connection_mode=inscription_options.connection_mode,
        wait_for_confirmation=False,
        wait_max_attempts=inscription_options.wait_max_attempts,
        wait_interval_ms=inscription_options.wait_interval_ms,
        api_key=inscription_options.api_key,
        base_url=inscription_options.base_url,
        auth_base_url=inscription_options.auth_base_url,
        tags=inscription_options.tags,
        metadata=inscription_options.metadata,
        json_file_url=inscription_options.json_file_url,
        file_standard=inscription_options.file_standard,
        chunk_size=inscription_options.chunk_size,
        network=inscription_options.network,
        quote_only=True,
    )
    response = _inscribe_with_inscriber(
        input_payload, client_config, quote_options, existing_client
    )
    result = response.result
    if not isinstance(result, dict):
        raise ParseError("failed to parse inscriber quote response", ErrorContext())
    return InscriberQuoteResult.model_validate(result)
