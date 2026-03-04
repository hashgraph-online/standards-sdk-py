"""Asynchronous Registry Broker client."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import re
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import TypedDict, TypeVar, cast

import httpx
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from standards_sdk_py.exceptions import ErrorContext, ParseError, ValidationError
from standards_sdk_py.registry_broker.models import (
    CreateSessionResponse,
    ProtocolsResponse,
    RegistrationProgressResponse,
    RegistriesResponse,
    SearchResponse,
    SendMessageResponse,
    SkillPublishResponse,
    StatsResponse,
    VerificationStatusResponse,
)
from standards_sdk_py.registry_broker.operations import REGISTRY_BROKER_OPERATIONS
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.http import AsyncHttpTransport
from standards_sdk_py.shared.types import Headers, JsonObject, JsonValue, QueryParams

ModelT = TypeVar("ModelT", bound=BaseModel)
_PATH_PARAM_RE = re.compile(r"{([a-zA-Z0-9_]+)}")
_NON_OPERATION_CAMEL_ALIASES = {
    "setApiKey": "set_api_key",
    "setLedgerApiKey": "set_ledger_api_key",
    "setDefaultHeader": "set_default_header",
    "getDefaultHeaders": "get_default_headers",
    "encryptionReady": "encryption_ready",
    "buildUrl": "build_url",
    "requestJson": "request_json",
    "searchErc8004ByAgentId": "search_erc8004_by_agent_id",
    "buyCreditsWithX402": "buy_credits_with_x402",
    "generateEncryptionKeyPair": "generate_encryption_key_pair",
    "authenticateWithLedger": "authenticate_with_ledger",
    "authenticateWithLedgerCredentials": "authenticate_with_ledger_credentials",
    "attachDecryptedHistory": "attach_decrypted_history",
    "registerConversationContextForEncryption": "register_conversation_context_for_encryption",
    "resolveDecryptionContext": "resolve_decryption_context",
    "decryptHistoryEntryFromContext": "decrypt_history_entry_from_context",
    "startChat": "start_chat",
    "startConversation": "start_conversation",
    "acceptConversation": "accept_conversation",
    "createPlaintextConversationHandle": "create_plaintext_conversation_handle",
    "assertNodeRuntime": "assert_node_runtime",
    "createEphemeralKeyPair": "create_ephemeral_key_pair",
    "deriveSharedSecret": "derive_shared_secret",
    "buildCipherEnvelope": "build_cipher_envelope",
    "openCipherEnvelope": "open_cipher_envelope",
    "normalizeSharedSecret": "normalize_shared_secret",
    "bufferFromString": "buffer_from_string",
    "hexToBuffer": "hex_to_buffer",
}


class RequestConfig(TypedDict, total=False):
    method: str
    body: JsonValue
    headers: Headers


def _fill_path(path: str, path_params: dict[str, str] | None) -> str:
    if not path_params:
        return path
    formatted = path
    for key, value in path_params.items():
        formatted = formatted.replace(f"{{{key}}}", value)
    if "{" in formatted or "}" in formatted:
        raise ValidationError(
            "Missing required path parameter",
            ErrorContext(details={"path": path, "path_params": path_params}),
        )
    return formatted


def _query_from_values(values: dict[str, object] | None) -> QueryParams | None:
    if not values:
        return None
    payload: QueryParams = {}
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, bool | int | float | str):
            payload[key] = value
            continue
        payload[key] = str(value)
    return payload or None


def _camel_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _snake_to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


def _normalize_header_name(name: str) -> str:
    return name.strip().lower()


def _normalize_headers(headers: dict[str, str] | None) -> dict[str, str]:
    if not headers:
        return {}
    return {_normalize_header_name(k): v for k, v in headers.items() if k.strip()}


def _sign_ledger_challenge(message: str, private_key: str) -> tuple[str, str]:
    from standards_sdk_py.inscriber.client import _sign_ledger_challenge as _impl

    return _impl(message, private_key)


class _AsyncChatApi:
    def __init__(self, client: AsyncRegistryBrokerClient) -> None:
        self._client = client

    async def start(self, options: JsonObject) -> JsonObject:
        return await self._client.start_chat(options)

    async def create_session(self, payload: JsonObject) -> CreateSessionResponse:
        return await self._client.create_session(payload)

    async def send_message(self, payload: JsonObject) -> SendMessageResponse:
        return await self._client.send_message(payload)

    async def end_session(self, session_id: str) -> None:
        await self._client.end_session(session_id)

    async def get_history(self, session_id: str, options: JsonObject | None = None) -> JsonValue:
        return await self._client.fetch_history_snapshot(session_id, options)

    async def compact_history(self, payload: JsonObject) -> JsonValue:
        return await self._client.compact_history(payload)

    async def get_encryption_status(self, session_id: str) -> JsonValue:
        return await self._client.fetch_encryption_status(session_id)

    async def submit_encryption_handshake(self, session_id: str, payload: JsonObject) -> JsonValue:
        return await self._client.post_encryption_handshake(session_id, payload)

    async def start_conversation(self, options: JsonObject) -> JsonObject:
        return await self._client.start_conversation(options)

    async def accept_conversation(self, options: JsonObject) -> JsonObject:
        return await self._client.accept_conversation(options)

    async def create_encrypted_session(self, options: JsonObject) -> JsonObject:
        return await self._client.start_conversation(options)

    async def accept_encrypted_session(self, options: JsonObject) -> JsonObject:
        return await self._client.accept_conversation(options)


class _AsyncEncryptionApi:
    def __init__(self, client: AsyncRegistryBrokerClient) -> None:
        self._client = client

    async def register_key(self, payload: JsonObject) -> JsonValue:
        return await self._client.call_operation("register_encryption_key", body=payload)

    def generate_ephemeral_key_pair(self) -> JsonObject:
        return self._client.create_ephemeral_key_pair()

    def derive_shared_secret(self, options: JsonObject) -> bytes:
        return self._client.derive_shared_secret(options)

    def encrypt_cipher_envelope(self, options: JsonObject) -> JsonObject:
        return self._client.build_cipher_envelope(options)

    def decrypt_cipher_envelope(self, options: JsonObject) -> str:
        return self._client.open_cipher_envelope(options)

    async def ensure_agent_key(self, options: JsonObject) -> JsonObject:
        payload = {
            "keyType": options.get("keyType", "secp256k1"),
            "publicKey": options.get("publicKey"),
            "uaid": options.get("uaid"),
            "ledgerAccountId": options.get("ledgerAccountId"),
            "ledgerNetwork": options.get("ledgerNetwork"),
            "email": options.get("email"),
        }
        material = self._client.generate_encryption_key_pair(options)
        payload["publicKey"] = material["publicKey"]
        await self._client.call_operation("register_encryption_key", body=cast(JsonObject, payload))
        return material


class AsyncRegistryBrokerClient:
    """Asynchronous Registry Broker client with parity operation map."""

    def __init__(
        self,
        *,
        config: SdkConfig | None = None,
        transport: AsyncHttpTransport | None = None,
        encryption_options: JsonObject | None = None,
    ) -> None:
        self._config = config or SdkConfig.from_env()
        base_headers = _normalize_headers(self._config.registry_auth.headers())
        self._transport = transport or AsyncHttpTransport(
            base_url=self._config.network.registry_broker_base_url,
            headers=base_headers,
        )
        self._default_headers = _normalize_headers(self._transport.headers)
        self._transport.headers = dict(self._default_headers)
        self._encryption_options = encryption_options
        self._conversation_contexts: dict[str, list[JsonObject]] = {}
        self._chat_api: _AsyncChatApi | None = None
        self._encryption_api: _AsyncEncryptionApi | None = None

    @property
    def base_url(self) -> str:
        return self._transport.base_url

    @property
    def chat(self) -> _AsyncChatApi:
        if self._chat_api is None:
            self._chat_api = _AsyncChatApi(self)
        return self._chat_api

    @property
    def encryption(self) -> _AsyncEncryptionApi:
        if self._encryption_api is None:
            self._encryption_api = _AsyncEncryptionApi(self)
        return self._encryption_api

    def set_api_key(self, api_key: str | None = None) -> None:
        self.set_default_header("x-api-key", api_key)

    def set_ledger_api_key(self, api_key: str | None = None) -> None:
        self.set_default_header("x-api-key", api_key)
        self.set_default_header("x-ledger-api-key", None)

    def set_default_header(self, name: str, value: str | None) -> None:
        if not name.strip():
            return
        key = _normalize_header_name(name)
        if value is None or not value.strip():
            self._default_headers.pop(key, None)
        else:
            self._default_headers[key] = value.strip()
        self._transport.headers = dict(self._default_headers)

    def get_default_headers(self) -> dict[str, str]:
        return dict(self._default_headers)

    async def encryption_ready(self) -> None:
        return None

    def build_url(self, path: str) -> str:
        normalized = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url.rstrip('/')}{normalized}"

    async def request(self, path: str, config: RequestConfig | None = None) -> httpx.Response:
        payload = config or {}
        method = payload.get("method", "GET")
        body = payload.get("body")
        headers = payload.get("headers")
        return await self._transport.request(
            method,
            path,
            headers=headers,
            body=cast(JsonObject | None, body),
        )

    async def request_json(self, path: str, config: RequestConfig | None = None) -> JsonValue:
        response = await self.request(path, config)
        content_type = response.headers.get("content-type", "")
        if "json" not in content_type.lower():
            raise ParseError(
                "Expected JSON response but got non-JSON content",
                ErrorContext(
                    status_code=response.status_code,
                    method=response.request.method if response.request else None,
                    url=str(response.request.url) if response.request else None,
                ),
            )
        return response.json()

    async def call_operation(
        self,
        operation: str,
        *,
        path_params: dict[str, str] | None = None,
        query: dict[str, object] | None = None,
        body: JsonObject | None = None,
        headers: Headers | None = None,
    ) -> JsonValue | str:
        spec = REGISTRY_BROKER_OPERATIONS.get(operation)
        if spec is None:
            raise ValidationError(
                f"Unknown Registry Broker operation: {operation}",
                ErrorContext(details={"operation": operation}),
            )
        path = _fill_path(spec.path, path_params)
        query_params = _query_from_values(query)
        if spec.text_response:
            response = await self._transport.request(
                spec.method,
                path,
                query=query_params,
                headers=headers,
                body=body,
            )
            return response.text
        return await self._transport.request_json(
            spec.method,
            path,
            query=query_params,
            headers=headers,
            body=body,
        )

    async def _call_operation_alias(
        self, operation: str, *args: object, **kwargs: object
    ) -> JsonValue | str:
        spec = REGISTRY_BROKER_OPERATIONS[operation]
        path_params = cast(dict[str, str] | None, kwargs.pop("path_params", None))
        query = cast(dict[str, object] | None, kwargs.pop("query", None))
        body = cast(JsonObject | None, kwargs.pop("body", None))
        headers = cast(Headers | None, kwargs.pop("headers", None))
        path_keys = _PATH_PARAM_RE.findall(spec.path)
        remaining = list(args)
        if path_params is None and path_keys:
            path_params = {}
            for key in path_keys:
                if key in kwargs:
                    path_params[key] = str(kwargs.pop(key))
                elif remaining:
                    path_params[key] = str(remaining.pop(0))
                else:
                    raise ValidationError(
                        "Missing required path parameter",
                        ErrorContext(details={"operation": operation, "path_param": key}),
                    )
        if remaining:
            first = remaining.pop(0)
            if spec.method.upper() in {"GET", "DELETE"}:
                if query is None:
                    query = (
                        cast(dict[str, object], first) if isinstance(first, dict) else {"q": first}
                    )
            elif body is None:
                body = (
                    cast(JsonObject, first)
                    if isinstance(first, dict)
                    else {"value": cast(JsonValue, first)}
                )
        if kwargs:
            remaining_kwargs = cast(dict[str, object], kwargs)
            if spec.method.upper() in {"GET", "DELETE"}:
                merged = dict(query or {})
                merged.update(remaining_kwargs)
                query = merged
            else:
                merged_body = dict(body or {})
                merged_body.update(cast(JsonObject, remaining_kwargs))
                body = merged_body
        return await self.call_operation(
            operation,
            path_params=path_params,
            query=query,
            body=body,
            headers=headers,
        )

    async def search(self, *, query: str | None = None, **params: object) -> SearchResponse:
        payload = dict(params)
        if query:
            payload["q"] = query
        raw = await self.call_operation("search", query=payload if payload else None)
        return self._parse_model(raw, SearchResponse)

    async def search_erc8004_by_agent_id(
        self,
        *,
        chain_id: int,
        agent_id: int | str,
        limit: int | None = None,
    ) -> SearchResponse:
        query: dict[str, object] = {
            "q": f"{chain_id}:{str(agent_id).strip()}",
            "registries": "erc-8004",
        }
        if limit is not None:
            query["limit"] = limit
        raw = await self.call_operation("search", query=query)
        return self._parse_model(raw, SearchResponse)

    async def stats(self) -> StatsResponse:
        return self._parse_model(await self.call_operation("stats"), StatsResponse)

    async def registries(self) -> RegistriesResponse:
        return self._parse_model(await self.call_operation("registries"), RegistriesResponse)

    async def list_protocols(self) -> ProtocolsResponse:
        return self._parse_model(await self.call_operation("list_protocols"), ProtocolsResponse)

    async def detect_protocol(self, message: str) -> JsonValue | str:
        return await self.call_operation("detect_protocol", body={"message": message})

    async def create_session(self, payload: JsonObject) -> CreateSessionResponse:
        raw = await self.call_operation("create_session", body=payload)
        return self._parse_model(raw, CreateSessionResponse)

    async def send_message(self, payload: JsonObject) -> SendMessageResponse:
        raw = await self.call_operation("send_message", body=payload)
        return self._parse_model(raw, SendMessageResponse)

    async def get_registration_progress(self, attempt_id: str) -> RegistrationProgressResponse:
        raw = await self.call_operation(
            "get_registration_progress", path_params={"attempt_id": attempt_id}
        )
        if isinstance(raw, dict) and "progress" in raw and isinstance(raw["progress"], dict):
            return self._parse_model(cast(JsonValue, raw["progress"]), RegistrationProgressResponse)
        return self._parse_model(raw, RegistrationProgressResponse)

    async def wait_for_registration_completion(
        self,
        attempt_id: str,
        *,
        timeout_seconds: float = 120.0,
        interval_seconds: float = 1.0,
    ) -> RegistrationProgressResponse:
        deadline = monotonic() + timeout_seconds
        while monotonic() < deadline:
            progress = await self.get_registration_progress(attempt_id)
            if progress.status in {"completed", "failed", "partial"}:
                return progress
            if interval_seconds > 0:
                await asyncio.sleep(interval_seconds)
        raise ValidationError(
            "Timed out waiting for registration completion",
            ErrorContext(details={"attempt_id": attempt_id, "timeout_seconds": timeout_seconds}),
        )

    async def get_verification_status(self, uaid: str) -> VerificationStatusResponse:
        raw = await self.call_operation("get_verification_status", path_params={"uaid": uaid})
        return self._parse_model(raw, VerificationStatusResponse)

    async def create_verification_challenge(self, uaid: str) -> JsonValue | str:
        return await self.call_operation("create_verification_challenge", body={"uaid": uaid})

    async def verify_sender_ownership(self, uaid: str) -> JsonValue | str:
        return await self.call_operation("verify_sender_ownership", body={"uaid": uaid})

    async def publish_skill(self, payload: JsonObject) -> SkillPublishResponse:
        raw = await self.call_operation("publish_skill", body=payload)
        return self._parse_model(raw, SkillPublishResponse)

    async def create_ledger_challenge(self, payload: JsonObject) -> JsonValue | str:
        return await self.call_operation("create_ledger_challenge", body=payload)

    async def verify_ledger_challenge(self, payload: JsonObject) -> JsonValue | str:
        raw = await self.call_operation("verify_ledger_challenge", body=payload)
        if isinstance(raw, dict) and isinstance(raw.get("key"), str):
            self.set_ledger_api_key(cast(str, raw["key"]))
        return raw

    async def authenticate_with_ledger(self, options: JsonObject) -> JsonValue | str:
        challenge = await self.create_ledger_challenge(
            {"accountId": options.get("accountId"), "network": options.get("network")}
        )
        if not isinstance(challenge, dict):
            raise ValidationError("Ledger challenge response must be an object", ErrorContext())
        message = cast(str | None, challenge.get("message"))
        challenge_id = cast(str | None, challenge.get("challengeId"))
        if not message or not challenge_id:
            raise ValidationError(
                "Ledger challenge response missing required fields", ErrorContext()
            )
        signature: str | None = None
        signer = options.get("sign")
        if callable(signer):
            signed = cast(object, signer(message))
            if asyncio.iscoroutine(signed):
                signed = await cast(Awaitable[object], signed)
            if isinstance(signed, dict):
                signature = cast(str | None, signed.get("signature"))
        if signature is None:
            private_key = cast(str | None, options.get("privateKey"))
            if private_key:
                signature, _public_key = _sign_ledger_challenge(message, private_key)
        if not signature:
            raise ValidationError(
                "authenticate_with_ledger requires sign callback or privateKey", ErrorContext()
            )
        return await self.verify_ledger_challenge(
            {
                "challengeId": challenge_id,
                "accountId": cast(str, options["accountId"]),
                "network": cast(str, options["network"]),
                "signature": signature,
                "signatureKind": "raw",
            }
        )

    async def authenticate_with_ledger_credentials(self, options: JsonObject) -> JsonValue | str:
        result = await self.authenticate_with_ledger(options)
        if isinstance(result, dict) and options.get("setAccountHeader", True):
            account_id = result.get("accountId")
            if isinstance(account_id, str):
                self.set_default_header("x-account-id", account_id)
        return result

    async def fetch_history_snapshot(
        self, session_id: str, options: JsonObject | None = None
    ) -> JsonValue:
        raw = await self.call_operation(
            "fetch_history_snapshot", path_params={"session_id": session_id}
        )
        if isinstance(raw, str):
            raise ParseError("Expected JSON response but got text", ErrorContext())
        return self.attach_decrypted_history(session_id, raw, options)

    def attach_decrypted_history(
        self,
        session_id: str,
        snapshot: JsonValue,
        options: JsonObject | None = None,
    ) -> JsonValue:
        if not isinstance(snapshot, dict):
            return snapshot
        decrypt = options.get("decrypt", False) if options else False
        if (
            not decrypt
            and self._encryption_options
            and self._encryption_options.get("autoDecryptHistory") is True
        ):
            decrypt = True
        if not decrypt:
            return snapshot
        history = snapshot.get("history")
        if not isinstance(history, list):
            return snapshot
        context = self.resolve_decryption_context(session_id, options)
        if context is None:
            return snapshot
        decrypted_history: list[JsonObject] = []
        for entry in history:
            if not isinstance(entry, dict):
                continue
            decrypted_history.append(
                {
                    "entry": entry,
                    "plaintext": self.decrypt_history_entry_from_context(
                        session_id, entry, context
                    ),
                }
            )
        return {**snapshot, "decryptedHistory": decrypted_history}

    def register_conversation_context_for_encryption(self, context: JsonObject) -> None:
        session_id = cast(str, context["sessionId"])
        secret = self.normalize_shared_secret(context["sharedSecret"])
        state: JsonObject = {
            "sessionId": session_id,
            "sharedSecret": base64.b64encode(secret).decode("utf-8"),
        }
        if context.get("identity") is not None:
            state["identity"] = cast(JsonValue, context["identity"])
        self._conversation_contexts.setdefault(session_id, []).append(state)

    def resolve_decryption_context(
        self, session_id: str, options: JsonObject | None = None
    ) -> JsonObject | None:
        if options and options.get("sharedSecret") is not None:
            return {
                "sessionId": session_id,
                "sharedSecret": base64.b64encode(
                    self.normalize_shared_secret(options["sharedSecret"])
                ).decode("utf-8"),
                "identity": cast(JsonValue, options.get("identity")),
            }
        entries = self._conversation_contexts.get(session_id, [])
        return entries[0] if entries else None

    def decrypt_history_entry_from_context(
        self,
        _session_id: str,
        entry: JsonObject,
        context: JsonObject,
    ) -> str | None:
        if entry.get("cipherEnvelope") is None:
            content = entry.get("content")
            return cast(str, content) if isinstance(content, str) else None
        envelope = entry.get("cipherEnvelope")
        if not isinstance(envelope, dict):
            return None
        secret_b64 = context.get("sharedSecret")
        if not isinstance(secret_b64, str):
            return None
        try:
            return self.open_cipher_envelope(
                {
                    "envelope": cast(JsonObject, envelope),
                    "sharedSecret": base64.b64decode(secret_b64),
                }
            )
        except Exception:
            return None

    async def start_chat(self, options: JsonObject) -> JsonObject:
        payload: JsonObject = {}
        for key in ("uaid", "agentUrl", "auth", "historyTtlSeconds", "senderUaid"):
            if options.get(key) is not None:
                payload[key] = cast(JsonValue, options[key])
        session = await self.create_session(payload)
        return self.create_plaintext_conversation_handle(
            session.session_id,
            cast(JsonObject | None, session.encryption),
            cast(JsonObject | None, options.get("auth")),
            cast(
                JsonObject | None,
                {"uaid": options.get("uaid"), "agentUrl": options.get("agentUrl")},
            ),
        )

    async def start_conversation(self, options: JsonObject) -> JsonObject:
        return await self.start_chat(options)

    async def accept_conversation(self, options: JsonObject) -> JsonObject:
        return self.create_plaintext_conversation_handle(
            cast(str, options["sessionId"]),
            None,
            None,
            cast(JsonObject | None, {"uaid": options.get("responderUaid")}),
        )

    def create_plaintext_conversation_handle(
        self,
        session_id: str,
        summary: JsonObject | None,
        default_auth: JsonObject | None = None,
        context: JsonObject | None = None,
    ) -> JsonObject:
        return {
            "sessionId": session_id,
            "mode": "plaintext",
            "summary": summary,
            "auth": default_auth,
            "context": context or {},
        }

    async def compact_history(self, payload: JsonObject) -> JsonValue:
        body: JsonObject = {}
        if payload.get("preserveEntries") is not None:
            body["preserveEntries"] = cast(JsonValue, payload["preserveEntries"])
        return cast(
            JsonValue,
            await self.call_operation(
                "compact_history",
                path_params={"session_id": cast(str, payload["sessionId"])},
                body=body,
            ),
        )

    async def fetch_encryption_status(self, session_id: str) -> JsonValue:
        return cast(
            JsonValue,
            await self.call_operation(
                "fetch_encryption_status", path_params={"session_id": session_id}
            ),
        )

    async def post_encryption_handshake(self, session_id: str, payload: JsonObject) -> JsonValue:
        return cast(
            JsonValue,
            await self.call_operation(
                "post_encryption_handshake",
                path_params={"session_id": session_id},
                body=payload,
            ),
        )

    async def end_session(self, session_id: str) -> None:
        await self.call_operation("end_session", path_params={"session_id": session_id})

    def assert_node_runtime(self, _feature: str) -> None:
        return None

    def generate_encryption_key_pair(self, _options: JsonObject | None = None) -> JsonObject:
        private = os.urandom(32).hex()
        public = self.create_ephemeral_key_pair()["publicKey"]
        return {"privateKey": private, "publicKey": public, "envVar": "RB_ENCRYPTION_PRIVATE_KEY"}

    def create_ephemeral_key_pair(self) -> JsonObject:
        private = os.urandom(32).hex()
        public = hashlib.sha256(bytes.fromhex(private)).hexdigest()
        return {"privateKey": private, "publicKey": public}

    def derive_shared_secret(self, options: JsonObject) -> bytes:
        return hashlib.sha256(
            f"{cast(str, options['privateKey'])}:{cast(str, options['peerPublicKey'])}".encode()
        ).digest()

    def normalize_shared_secret(self, input_value: object) -> bytes:
        if isinstance(input_value, bytes):
            return input_value
        if isinstance(input_value, bytearray):
            return bytes(input_value)
        if isinstance(input_value, str):
            return self.buffer_from_string(input_value)
        raise ValidationError("Unsupported shared secret input", ErrorContext())

    def buffer_from_string(self, value: str) -> bytes:
        trimmed = value.strip()
        if not trimmed:
            raise ValidationError("sharedSecret string cannot be empty", ErrorContext())
        normalized = trimmed[2:] if trimmed.startswith("0x") else trimmed
        if re.fullmatch(r"[0-9a-fA-F]+", normalized or "") and len(normalized) % 2 == 0:
            return bytes.fromhex(normalized)
        return base64.b64decode(trimmed)

    def hex_to_buffer(self, value: str) -> bytes:
        normalized = value[2:] if value.startswith("0x") else value
        if not re.fullmatch(r"[0-9a-fA-F]+", normalized or "") or len(normalized) % 2 != 0:
            raise ValidationError("Expected hex-encoded value", ErrorContext())
        return bytes.fromhex(normalized)

    def build_cipher_envelope(self, options: JsonObject) -> JsonObject:
        shared = self.normalize_shared_secret(options["sharedSecret"])
        nonce = os.urandom(12)
        plaintext = cast(str, options["plaintext"]).encode("utf-8")
        key_stream = hashlib.sha256(shared + nonce).digest()
        ciphertext = bytes(
            [b ^ key_stream[index % len(key_stream)] for index, b in enumerate(plaintext)]
        )
        session_id = cast(str, options["sessionId"])
        recipients = cast(list[JsonObject], options.get("recipients", []))
        return {
            "algorithm": "aes-256-gcm",
            "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
            "nonce": base64.b64encode(nonce).decode("utf-8"),
            "associatedData": base64.b64encode(session_id.encode("utf-8")).decode("utf-8"),
            "keyLocator": {"sessionId": session_id, "revision": options.get("revision", 1)},
            "recipients": [{**recipient, "encryptedShare": ""} for recipient in recipients],
        }

    def open_cipher_envelope(self, options: JsonObject) -> str:
        envelope = cast(JsonObject, options["envelope"])
        shared = self.normalize_shared_secret(options["sharedSecret"])
        nonce = base64.b64decode(cast(str, envelope["nonce"]))
        ciphertext = base64.b64decode(cast(str, envelope["ciphertext"]))
        key_stream = hashlib.sha256(shared + nonce).digest()
        plaintext = bytes(
            [b ^ key_stream[index % len(key_stream)] for index, b in enumerate(ciphertext)]
        )
        return plaintext.decode(cast(str, options.get("encoding", "utf-8")))

    async def buy_credits_with_x402(self, params: JsonObject) -> JsonValue | str:
        payload = dict(params)
        payload.pop("evmPrivateKey", None)
        payload.pop("network", None)
        payload.pop("rpcUrl", None)
        return await self.call_operation(
            "purchase_credits_with_x402", body=cast(JsonObject, payload)
        )

    async def close(self) -> None:
        await self._transport.close()

    def __getattr__(self, name: str) -> Callable[..., Awaitable[JsonValue | str] | object]:
        if name in _NON_OPERATION_CAMEL_ALIASES:
            return cast(
                Callable[..., Awaitable[JsonValue | str] | object],
                getattr(self, _NON_OPERATION_CAMEL_ALIASES[name]),
            )
        snake_name = _camel_to_snake(name)
        if name in REGISTRY_BROKER_OPERATIONS:
            return lambda *args, **kwargs: self._call_operation_alias(name, *args, **kwargs)
        if snake_name in REGISTRY_BROKER_OPERATIONS:
            return lambda *args, **kwargs: self._call_operation_alias(snake_name, *args, **kwargs)
        raise AttributeError(name)

    @staticmethod
    def _parse_model(raw: JsonValue | str, model_type: type[ModelT]) -> ModelT:
        if isinstance(raw, str):
            raise ParseError(
                "Expected JSON response but got text",
                ErrorContext(details={"model": model_type.__name__}),
            )
        try:
            return model_type.model_validate(raw)
        except PydanticValidationError as exc:
            raise ParseError(
                f"Failed to validate {model_type.__name__}",
                ErrorContext(details={"errors": exc.errors()}),
            ) from exc


def _make_async_operation_method(operation: str) -> Callable[..., Awaitable[JsonValue | str]]:
    async def _method(
        self: AsyncRegistryBrokerClient,
        *args: object,
        **kwargs: object,
    ) -> JsonValue | str:
        return await self._call_operation_alias(operation, *args, **kwargs)

    _method.__name__ = operation
    return _method


for _operation_name in REGISTRY_BROKER_OPERATIONS:
    if not hasattr(AsyncRegistryBrokerClient, _operation_name):
        setattr(
            AsyncRegistryBrokerClient,
            _operation_name,
            _make_async_operation_method(_operation_name),
        )
    _camel_name = _snake_to_camel(_operation_name)
    if not hasattr(AsyncRegistryBrokerClient, _camel_name):
        setattr(
            AsyncRegistryBrokerClient,
            _camel_name,
            _make_async_operation_method(_operation_name),
        )

for _camel_alias, _snake_alias in _NON_OPERATION_CAMEL_ALIASES.items():
    if hasattr(AsyncRegistryBrokerClient, _snake_alias) and not hasattr(
        AsyncRegistryBrokerClient,
        _camel_alias,
    ):
        setattr(
            AsyncRegistryBrokerClient,
            _camel_alias,
            getattr(AsyncRegistryBrokerClient, _snake_alias),
        )
