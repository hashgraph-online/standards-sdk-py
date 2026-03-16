"""HCS-7 client with direct on-chain execution parity."""

# ruff: noqa: N802

from __future__ import annotations

import asyncio
import base64
import importlib
import json
import re
from collections.abc import Mapping
from typing import Any, cast

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from standards_sdk_py.exceptions import ErrorContext, ParseError, TransportError, ValidationError
from standards_sdk_py.hcs7.models import (
    EvmConfigPayload,
    Hcs7ConfigType,
    Hcs7CreateRegistryOptions,
    Hcs7CreateRegistryResult,
    Hcs7Message,
    Hcs7Operation,
    Hcs7QueryRegistryOptions,
    Hcs7RegisterConfigOptions,
    Hcs7RegisterMetadataOptions,
    Hcs7RegistryEntry,
    Hcs7RegistryOperationResult,
    Hcs7RegistryTopic,
    WasmConfigPayload,
)
from standards_sdk_py.mirror import MirrorNodeClient
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.hcs_module import AsyncHcsModuleClient, HcsModuleClient
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.types import JsonValue

_TOPIC_ID_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_EVM_ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")
_TOPIC_MEMO_PATTERN = re.compile(r"^hcs-7:indexed:(\d+)$")
_DEFAULT_MIRROR_BY_NETWORK = {
    "mainnet": "https://mainnet-public.mirrornode.hedera.com/api/v1",
    "testnet": "https://testnet.mirrornode.hedera.com/api/v1",
}
_DEFAULT_REGISTRY_BROKER_BASE_URL = "https://registry.hashgraphonline.com"
_DEFAULT_TTL = 86400
_MIN_TTL = 3600


def _clean(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _normalize_network(raw_network: str) -> str:
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
    normalized = aliases.get(raw_network.strip().lower(), raw_network.strip().lower())
    if normalized not in {"mainnet", "testnet"}:
        raise ValidationError(
            "network must be testnet or mainnet",
            ErrorContext(details={"network": raw_network}),
        )
    return normalized


def _to_string(value: object | None) -> str:
    if value is None:
        return ""
    to_string = getattr(value, "toString", None)
    if callable(to_string):
        rendered = to_string()
        if isinstance(rendered, str):
            return rendered
    return str(value)


def _validate_topic_id(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not _TOPIC_ID_PATTERN.fullmatch(normalized):
        raise ValidationError(
            f"{field_name} must be a Hedera topic ID (e.g. 0.0.12345)",
            ErrorContext(details={"field": field_name, "value": value}),
        )
    return normalized


def _coerce_mapping(value: object, field_name: str) -> dict[str, object]:
    if isinstance(value, BaseModel):
        return cast(dict[str, object], value.model_dump(by_alias=True, exclude_none=True))
    if isinstance(value, Mapping):
        return {str(k): v for k, v in value.items()}
    raise ValidationError(
        f"{field_name} must be a mapping/object",
        ErrorContext(details={"field": field_name, "type": type(value).__name__}),
    )


class Hcs7Client(HcsModuleClient):
    """Synchronous HCS-7 client."""

    def __init__(
        self,
        transport: SyncHttpTransport | None = None,
        *,
        operator_id: str,
        operator_key: str,
        hedera_client: object | None = None,
        network: str = "testnet",
        mirror_base_url: str | None = None,
        key_type: str | None = None,
        mirror_client: MirrorNodeClient | None = None,
    ) -> None:
        config = SdkConfig.from_env()
        resolved_transport = transport or SyncHttpTransport(
            base_url=config.network.registry_broker_base_url or _DEFAULT_REGISTRY_BROKER_BASE_URL,
        )
        super().__init__("hcs7", resolved_transport)
        self._network = _normalize_network(network)
        resolved_mirror_base = (
            mirror_base_url.strip()
            if isinstance(mirror_base_url, str) and mirror_base_url.strip()
            else _DEFAULT_MIRROR_BY_NETWORK[self._network]
        )
        self._mirror_client = mirror_client or MirrorNodeClient(
            transport=SyncHttpTransport(base_url=resolved_mirror_base),
        )

        self._hedera: Any | None = None
        self._hedera_client: object | None = None
        self._operator_key: Any | None = None
        self._key_type: str | None = None

        cleaned_operator_id = _clean(operator_id)
        cleaned_operator_key = _clean(operator_key)
        if not cleaned_operator_id:
            raise ValidationError("operator_id is required", ErrorContext())
        if not cleaned_operator_key:
            raise ValidationError("operator_key is required", ErrorContext())
        self._initialize_onchain(
            cleaned_operator_id,
            cleaned_operator_key,
            key_type=key_type,
            hedera_client=hedera_client,
        )

    def _initialize_onchain(
        self,
        operator_id: str,
        operator_key: str,
        *,
        key_type: str | None,
        hedera_client: object | None = None,
    ) -> None:
        try:
            hedera = importlib.import_module("hedera")
        except ModuleNotFoundError as exc:
            raise ValidationError(
                "hedera-sdk-py is required for on-chain HCS-7 operations",
                ErrorContext(details={"dependency": "hedera-sdk-py"}),
            ) from exc

        try:
            account_id = hedera.AccountId.fromString(operator_id)
            private_key = hedera.PrivateKey.fromString(operator_key)
        except Exception as exc:
            raise ValidationError(
                "invalid operator credentials", ErrorContext(details={"reason": str(exc)})
            ) from exc

        client = hedera_client or (
            hedera.Client.forMainnet() if self._network == "mainnet" else hedera.Client.forTestnet()
        )
        if hedera_client is None:
            cast(Any, client).setOperator(account_id, private_key)
        self._hedera = hedera
        self._hedera_client = client
        self._operator_key = private_key

        normalized_key_type = _clean(key_type).lower()
        if normalized_key_type in {"ed25519", "ecdsa"}:
            self._key_type = normalized_key_type
        elif callable(getattr(private_key, "isECDSA", None)) and bool(private_key.isECDSA()):
            self._key_type = "ecdsa"
        else:
            self._key_type = "ed25519"

    def _resolve_public_key(self, raw_key: object | None, use_operator: bool) -> object | None:
        if self._operator_key is None or self._hedera is None:
            return None
        if use_operator or raw_key is True:
            return cast(object, self._operator_key.getPublicKey())
        if raw_key is None or raw_key is False:
            return None
        if isinstance(raw_key, str):
            cleaned = raw_key.strip()
            if not cleaned:
                return None
            try:
                return cast(object, self._hedera.PublicKey.fromString(cleaned))
            except Exception:
                try:
                    return cast(object, self._hedera.PrivateKey.fromString(cleaned).getPublicKey())
                except Exception:
                    return None
        return None

    def _resolve_private_key(self, raw_key: object | None) -> object | None:
        if raw_key is None:
            return None
        if raw_key is True:
            return self._operator_key
        if raw_key is False:
            return None
        if self._hedera is None:
            return None
        if isinstance(raw_key, str):
            cleaned = raw_key.strip()
            if not cleaned:
                return None
            try:
                return cast(object, self._hedera.PrivateKey.fromString(cleaned))
            except Exception:
                return None
        return raw_key

    def _validate_message(self, message: Hcs7Message) -> None:
        if message.p != "hcs-7":
            raise ValidationError("message p must be hcs-7", ErrorContext())
        if message.m is not None and len(message.m.strip()) > 500:
            raise ValidationError("message memo exceeds 500 characters", ErrorContext())
        if message.op == Hcs7Operation.REGISTER_CONFIG:
            if message.t not in {Hcs7ConfigType.EVM, Hcs7ConfigType.WASM}:
                raise ValidationError(
                    "register-config requires t to be evm or wasm", ErrorContext()
                )
            if message.t == Hcs7ConfigType.EVM:
                if not isinstance(message.c, dict):
                    raise ValidationError("evm config payload is invalid", ErrorContext())
                evm_payload = EvmConfigPayload.model_validate(message.c)
                if not _EVM_ADDRESS_PATTERN.fullmatch(evm_payload.contract_address.strip()):
                    raise ValidationError(
                        "evm contractAddress must be a 0x-prefixed 40-byte address",
                        ErrorContext(),
                    )
                if not evm_payload.abi.name.strip():
                    raise ValidationError("evm abi.name is required", ErrorContext())
            if message.t == Hcs7ConfigType.WASM:
                if not isinstance(message.c, dict):
                    raise ValidationError("wasm config payload is invalid", ErrorContext())
                wasm_payload = WasmConfigPayload.model_validate(message.c)
                _validate_topic_id(wasm_payload.wasm_topic_id, "wasmTopicId")
                if (
                    wasm_payload.output_type.type != "string"
                    or wasm_payload.output_type.format != "topic-id"
                ):
                    raise ValidationError(
                        "wasm outputType must be {type:string, format:topic-id}",
                        ErrorContext(),
                    )
        elif message.op == Hcs7Operation.REGISTER:
            _validate_topic_id(message.t_id or "", "t_id")
            if not isinstance(message.d, dict):
                raise ValidationError("register requires d object", ErrorContext())
            weight = message.d.get("weight")
            if not isinstance(weight, int | float):
                raise ValidationError("register d.weight must be numeric", ErrorContext())
            tags = message.d.get("tags")
            if (
                not isinstance(tags, list)
                or not tags
                or not all(isinstance(tag, str) for tag in tags)
            ):
                raise ValidationError("register d.tags must be an array of strings", ErrorContext())
        else:
            raise ValidationError(f"unsupported operation {message.op!s}", ErrorContext())

    def createRegistry(self, *args: object, **kwargs: object) -> JsonValue:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(
                "on-chain operator credentials are not configured", ErrorContext()
            )
        payload = self._parse_single_options(args, kwargs, "createRegistry")
        options = Hcs7CreateRegistryOptions.model_validate(payload)

        ttl = options.ttl if options.ttl > 0 else _DEFAULT_TTL
        if ttl < _MIN_TTL:
            raise ValidationError("TTL must be at least 3600 seconds", ErrorContext())
        tx = self._hedera.TopicCreateTransaction().setTopicMemo(f"hcs-7:indexed:{ttl}")
        admin_key = self._resolve_public_key(options.admin_key, options.use_operator_as_admin)
        submit_key = self._resolve_public_key(options.submit_key, options.use_operator_as_submit)
        if admin_key is not None:
            tx.setAdminKey(admin_key)
        if submit_key is not None:
            tx.setSubmitKey(submit_key)
        try:
            response = tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to execute create topic transaction",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc
        topic_id = _to_string(getattr(receipt, "topicId", None))
        if not topic_id:
            raise ParseError("topic ID missing in create topic receipt", ErrorContext())
        result = Hcs7CreateRegistryResult(
            success=True,
            topicId=topic_id,
            transactionId=_to_string(getattr(response, "transactionId", None)) or None,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def registerConfig(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs7RegisterConfigOptions.model_validate(
            self._parse_single_options(args, kwargs, "registerConfig")
        )
        registry_topic_id = _validate_topic_id(options.registry_topic_id, "registryTopicId")
        if options.type == Hcs7ConfigType.EVM:
            if options.evm is None:
                raise ValidationError("EVM config is required", ErrorContext())
            config_payload = options.evm.model_dump(by_alias=True, exclude_none=True)
        else:
            if options.wasm is None:
                raise ValidationError("WASM config is required", ErrorContext())
            config_payload = options.wasm.model_dump(by_alias=True, exclude_none=True)
        message = Hcs7Message(
            op=Hcs7Operation.REGISTER_CONFIG,
            t=options.type,
            c=config_payload,
            m=options.memo,
        )
        analytics_memo = options.analytics_memo or "hcs-7:op:0:0"
        return self._submit_message(
            registry_topic_id,
            message,
            submit_key=options.submit_key,
            transaction_memo=analytics_memo,
        )

    def registerMetadata(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs7RegisterMetadataOptions.model_validate(
            self._parse_single_options(args, kwargs, "registerMetadata")
        )
        registry_topic_id = _validate_topic_id(options.registry_topic_id, "registryTopicId")
        metadata_topic_id = _validate_topic_id(options.metadata_topic_id, "metadataTopicId")
        if not options.tags:
            raise ValidationError("tags are required", ErrorContext())
        data = dict(options.data)
        data["weight"] = options.weight
        data["tags"] = options.tags
        message = Hcs7Message(
            op=Hcs7Operation.REGISTER,
            t_id=metadata_topic_id,
            d=data,
            m=options.memo,
        )
        analytics_memo = options.analytics_memo or "hcs-7:op:1:0"
        return self._submit_message(
            registry_topic_id,
            message,
            submit_key=options.submit_key,
            transaction_memo=analytics_memo,
        )

    def getRegistry(self, *args: object, **kwargs: object) -> JsonValue:
        topic_id, query = self._parse_get_registry_inputs(args, kwargs)
        topic_info = self._mirror_client.get_topic_info(topic_id)
        raw_memo = topic_info.get("memo")
        if not isinstance(raw_memo, str):
            raise ValidationError(f"topic {topic_id} is not an HCS-7 registry", ErrorContext())
        memo_match = _TOPIC_MEMO_PATTERN.fullmatch(raw_memo.strip())
        if memo_match is None:
            raise ValidationError(f"topic {topic_id} is not an HCS-7 registry", ErrorContext())
        ttl = int(memo_match.group(1))
        sequence = f"gt:{query.skip}" if query.skip > 0 else None
        topic_messages = self._mirror_client.get_topic_messages(
            topic_id,
            sequence_number=sequence,
            limit=query.limit,
            order=query.order,
        )

        entries: list[Hcs7RegistryEntry] = []
        for item in topic_messages.messages:
            decoded = self._decode_message(item.message)
            if decoded is None:
                continue
            try:
                message = Hcs7Message.model_validate(decoded)
                self._validate_message(message)
            except (PydanticValidationError, ValidationError):
                continue
            entries.append(
                Hcs7RegistryEntry(
                    sequenceNumber=int(item.sequence_number or 0),
                    timestamp=item.consensus_timestamp,
                    payer=str(getattr(item, "payer_account_id", "") or ""),
                    message=message,
                )
            )
        registry = Hcs7RegistryTopic(topicId=topic_id, ttl=ttl, entries=entries)
        return cast(JsonValue, registry.model_dump(by_alias=True, exclude_none=True))

    def _submit_message(
        self,
        topic_id: str,
        message: Hcs7Message,
        *,
        submit_key: object | None,
        transaction_memo: str,
    ) -> JsonValue:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(
                "on-chain operator credentials are not configured", ErrorContext()
            )
        self._validate_message(message)
        tx = self._hedera.TopicMessageSubmitTransaction().setTopicId(
            self._hedera.TopicId.fromString(topic_id)
        )
        tx.setMessage(
            json.dumps(message.model_dump(by_alias=True, exclude_none=True)).encode("utf-8")
        )
        if transaction_memo.strip():
            tx.setTransactionMemo(transaction_memo.strip())
        resolved_submit_key = self._resolve_private_key(submit_key)
        try:
            if resolved_submit_key is None:
                response = tx.execute(self._hedera_client)
            else:
                frozen_tx = tx.freezeWith(self._hedera_client)
                frozen_tx.sign(resolved_submit_key)
                response = frozen_tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to execute HCS-7 submit message transaction",
                ErrorContext(details={"reason": str(exc), "topic_id": topic_id}),
            ) from exc
        result = Hcs7RegistryOperationResult(
            success=True,
            transactionId=_to_string(getattr(response, "transactionId", None)) or None,
            sequenceNumber=int(_to_string(getattr(receipt, "topicSequenceNumber", 0)) or 0),
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def close(self, *args: object, **kwargs: object) -> JsonValue:
        _ = (args, kwargs)
        try:
            close_fn = getattr(self._hedera_client, "close", None)
            if self._hedera_client is not None and callable(close_fn):
                close_fn()
        except Exception as exc:
            raise TransportError(
                "failed to close HCS-7 Hedera client",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc
        return None

    def getKeyType(self, *args: object, **kwargs: object) -> JsonValue:
        _ = (args, kwargs)
        if self._key_type is None:
            raise ParseError("operator key type is unavailable", ErrorContext())
        return self._key_type

    def _parse_single_options(
        self, args: tuple[object, ...], kwargs: Mapping[str, object], method_name: str
    ) -> dict[str, object]:
        if len(args) > 1:
            raise ValidationError(
                f"{method_name} expects at most one positional argument", ErrorContext()
            )
        payload: dict[str, object] = {}
        if args:
            payload.update(_coerce_mapping(args[0], "options"))
        payload.update(kwargs)
        return payload

    def _parse_get_registry_inputs(
        self, args: tuple[object, ...], kwargs: Mapping[str, object]
    ) -> tuple[str, Hcs7QueryRegistryOptions]:
        if len(args) > 2:
            raise ValidationError(
                "getRegistry expects at most two positional arguments", ErrorContext()
            )
        if not args and not kwargs.get("topicId") and not kwargs.get("topic_id"):
            raise ValidationError("topicId is required", ErrorContext())
        if args and not isinstance(args[0], str):
            raise ValidationError("topicId must be a string", ErrorContext())
        topic_id = _validate_topic_id(
            cast(str, args[0] if args else kwargs.get("topicId", kwargs.get("topic_id"))),
            "topicId",
        )
        options_payload: dict[str, object] = {}
        if len(args) >= 2:
            options_payload.update(_coerce_mapping(args[1], "options"))
        for key, value in kwargs.items():
            if key in {"topicId", "topic_id"}:
                continue
            options_payload[key] = value
        return topic_id, Hcs7QueryRegistryOptions.model_validate(options_payload)

    def _decode_message(self, encoded: str) -> dict[str, object] | None:
        try:
            decoded = base64.b64decode(encoded).decode("utf-8")
            payload = json.loads(decoded)
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return {str(k): v for k, v in payload.items()}

    register_config = registerConfig
    register_metadata = registerMetadata
    create_registry = createRegistry
    get_registry = getRegistry
    get_key_type = getKeyType


class AsyncHcs7Client(AsyncHcsModuleClient):
    """Asynchronous HCS-7 client."""

    def __init__(
        self,
        transport: AsyncHttpTransport | None = None,
        *,
        operator_id: str,
        operator_key: str,
        hedera_client: object | None = None,
        network: str = "testnet",
        mirror_base_url: str | None = None,
        key_type: str | None = None,
    ) -> None:
        config = SdkConfig.from_env()
        resolved_transport = transport or AsyncHttpTransport(
            base_url=config.network.registry_broker_base_url or _DEFAULT_REGISTRY_BROKER_BASE_URL,
        )
        super().__init__("hcs7", resolved_transport)
        self._sync_client = Hcs7Client(
            transport=SyncHttpTransport(
                base_url=resolved_transport.base_url,
                headers=dict(resolved_transport.headers or {}),
            ),
            operator_id=operator_id,
            operator_key=operator_key,
            hedera_client=hedera_client,
            network=network,
            mirror_base_url=mirror_base_url,
            key_type=key_type,
        )

    async def createRegistry(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.createRegistry, *args, **kwargs)

    async def registerConfig(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.registerConfig, *args, **kwargs)

    async def registerMetadata(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.registerMetadata, *args, **kwargs)

    async def getRegistry(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.getRegistry, *args, **kwargs)

    async def getKeyType(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.getKeyType, *args, **kwargs)

    async def close(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.close, *args, **kwargs)

    register_config = registerConfig
    register_metadata = registerMetadata
    create_registry = createRegistry
    get_registry = getRegistry
    get_key_type = getKeyType
