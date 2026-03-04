"""HCS-2 client with direct on-chain execution parity."""

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
from standards_sdk_py.hcs2.models import (
    CreateRegistryOptions,
    CreateRegistryResult,
    DeleteEntryOptions,
    Hcs2DeleteMessage,
    Hcs2Message,
    Hcs2MigrateMessage,
    Hcs2Operation,
    Hcs2RegisterMessage,
    Hcs2RegistryType,
    Hcs2UpdateMessage,
    MigrateRegistryOptions,
    OperationResult,
    QueryRegistryOptions,
    RegisterEntryOptions,
    RegistryEntry,
    TopicRegistry,
    UpdateEntryOptions,
)
from standards_sdk_py.mirror import MirrorNodeClient
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.hcs_module import AsyncHcsModuleClient, HcsModuleClient
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.types import JsonValue

_TOPIC_ID_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_HCS_PROTOCOL_PATTERN = re.compile(r"^hcs-\d+$")
_HCS1_REFERENCE_PATTERN = re.compile(r"^hcs://1/(\d+\.\d+\.\d+)$")
_DEFAULT_MIRROR_BY_NETWORK = {
    "mainnet": "https://mainnet-public.mirrornode.hedera.com/api/v1",
    "testnet": "https://testnet.mirrornode.hedera.com/api/v1",
}
_DEFAULT_REGISTRY_BROKER_BASE_URL = "https://registry.hashgraphonline.com"
_MAX_MESSAGE_BYTES = 1024


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


def _coerce_int(value: object | None, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(cast(Any, value))
    except (TypeError, ValueError):
        return default


def _coerce_mapping(value: object, field_name: str) -> dict[str, object]:
    if isinstance(value, BaseModel):
        return cast(dict[str, object], value.model_dump(by_alias=True, exclude_none=True))
    if isinstance(value, Mapping):
        payload: dict[str, object] = {}
        for key, item in value.items():
            payload[str(key)] = item
        return payload
    raise ValidationError(
        f"{field_name} must be a mapping/object",
        ErrorContext(details={"field": field_name, "type": type(value).__name__}),
    )


def _validate_topic_id(topic_id: str, field_name: str) -> str:
    normalized = topic_id.strip()
    if not _TOPIC_ID_PATTERN.fullmatch(normalized):
        raise ValidationError(
            f"{field_name} must be a Hedera topic ID (e.g. 0.0.12345)",
            ErrorContext(details={"field": field_name, "value": topic_id}),
        )
    return normalized


def _parse_topic_memo(memo: object) -> tuple[Hcs2RegistryType, int] | None:
    if not isinstance(memo, str):
        return None
    parts = memo.strip().split(":")
    if len(parts) != 3:
        return None
    if parts[0] != "hcs-2":
        return None
    try:
        registry_value = int(parts[1])
        ttl = int(parts[2])
    except ValueError:
        return None
    if registry_value not in (int(Hcs2RegistryType.INDEXED), int(Hcs2RegistryType.NON_INDEXED)):
        return None
    return Hcs2RegistryType(registry_value), ttl


def _build_topic_memo(registry_type: Hcs2RegistryType, ttl: int) -> str:
    return f"hcs-2:{int(registry_type)}:{ttl}"


def _build_transaction_memo(operation: Hcs2Operation, registry_type: Hcs2RegistryType) -> str:
    operation_code: dict[Hcs2Operation, int] = {
        Hcs2Operation.REGISTER: 0,
        Hcs2Operation.UPDATE: 1,
        Hcs2Operation.DELETE: 2,
        Hcs2Operation.MIGRATE: 3,
    }
    return f"hcs-2:op:{operation_code[operation]}:{int(registry_type)}"


class Hcs2Client(HcsModuleClient):
    """Synchronous HCS-2 client."""

    def __init__(
        self,
        transport: SyncHttpTransport | None = None,
        *,
        operator_id: str,
        operator_key: str,
        network: str = "testnet",
        mirror_base_url: str | None = None,
        key_type: str | None = None,
        mirror_client: MirrorNodeClient | None = None,
    ) -> None:
        config = SdkConfig.from_env()
        resolved_transport = transport or SyncHttpTransport(
            base_url=config.network.registry_broker_base_url or _DEFAULT_REGISTRY_BROKER_BASE_URL,
        )
        super().__init__("hcs2", resolved_transport)

        self._network = _normalize_network(network)
        resolved_mirror_base = (
            mirror_base_url.strip()
            if isinstance(mirror_base_url, str) and mirror_base_url.strip()
            else _DEFAULT_MIRROR_BY_NETWORK[self._network]
        )
        self._mirror_client = mirror_client or MirrorNodeClient(
            transport=SyncHttpTransport(base_url=resolved_mirror_base),
        )
        self._registry_type_cache: dict[str, Hcs2RegistryType] = {}

        self._hedera: Any | None = None
        self._hedera_client: Any | None = None
        self._operator_id: str | None = None
        self._operator_key: Any | None = None
        self._key_type: str | None = None

        cleaned_operator_id = _clean(operator_id)
        cleaned_operator_key = _clean(operator_key)
        if not cleaned_operator_id:
            raise ValidationError("operator_id is required", ErrorContext())
        if not cleaned_operator_key:
            raise ValidationError("operator_key is required", ErrorContext())
        self._initialize_onchain(cleaned_operator_id, cleaned_operator_key, key_type=key_type)

    def _initialize_onchain(
        self, operator_id: str, operator_key: str, *, key_type: str | None
    ) -> None:
        try:
            hedera = importlib.import_module("hedera")
        except ModuleNotFoundError as exc:
            raise ValidationError(
                "hedera-sdk-py is required for on-chain HCS-2 operations",
                ErrorContext(details={"dependency": "hedera-sdk-py"}),
            ) from exc

        try:
            account_id = hedera.AccountId.fromString(operator_id)
        except Exception as exc:
            raise ValidationError(
                "invalid operator account ID",
                ErrorContext(details={"operator_id": operator_id, "reason": str(exc)}),
            ) from exc
        try:
            private_key = hedera.PrivateKey.fromString(operator_key)
        except Exception as exc:
            raise ValidationError(
                "invalid operator private key",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc

        client = (
            hedera.Client.forMainnet() if self._network == "mainnet" else hedera.Client.forTestnet()
        )
        client.setOperator(account_id, private_key)

        resolved_key_type = _clean(key_type).lower()
        if resolved_key_type:
            if resolved_key_type not in {"ed25519", "ecdsa"}:
                raise ValidationError(
                    "key_type must be 'ed25519' or 'ecdsa'",
                    ErrorContext(details={"key_type": key_type}),
                )
            self._key_type = resolved_key_type
        elif callable(getattr(private_key, "isECDSA", None)) and bool(private_key.isECDSA()):
            self._key_type = "ecdsa"
        else:
            self._key_type = "ed25519"

        self._hedera = hedera
        self._hedera_client = client
        self._operator_id = operator_id
        self._operator_key = private_key

    def _validate_message(self, message: Hcs2Message) -> None:
        if not _HCS_PROTOCOL_PATTERN.fullmatch(message.p):
            raise ValidationError("protocol must be in format hcs-N", ErrorContext())
        if message.m is not None and len(message.m) > 500:
            raise ValidationError("memo must not exceed 500 characters", ErrorContext())
        if message.ttl is not None and message.ttl < 0:
            raise ValidationError("ttl cannot be negative", ErrorContext())

        if message.op == Hcs2Operation.REGISTER:
            _validate_topic_id(message.t_id or "", "t_id")
        elif message.op == Hcs2Operation.UPDATE:
            if not _clean(message.uid):
                raise ValidationError("update requires uid", ErrorContext())
            _validate_topic_id(message.t_id or "", "t_id")
        elif message.op == Hcs2Operation.DELETE:
            if not _clean(message.uid):
                raise ValidationError("delete requires uid", ErrorContext())
        elif message.op == Hcs2Operation.MIGRATE:
            _validate_topic_id(message.t_id or "", "t_id")

    def _resolve_public_key(self, raw_key: object | None, use_operator: bool) -> object | None:
        if self._hedera is None or self._operator_key is None:
            raise ValidationError(
                "on-chain operator credentials are not configured", ErrorContext()
            )

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
                except Exception as exc:
                    raise ValidationError(
                        "failed to parse key as public or private key",
                        ErrorContext(details={"reason": str(exc)}),
                    ) from exc

        get_public_key = getattr(raw_key, "getPublicKey", None)
        if callable(get_public_key):
            try:
                return cast(object, get_public_key())
            except Exception as exc:
                raise ValidationError(
                    "failed to derive public key from provided key object",
                    ErrorContext(details={"reason": str(exc)}),
                ) from exc

        raise ValidationError(
            "admin/submit key must be bool, string, or key object",
            ErrorContext(details={"type": type(raw_key).__name__}),
        )

    def _resolve_registry_type(
        self, topic_id: str, override: Hcs2RegistryType | None
    ) -> Hcs2RegistryType:
        if override is not None:
            return override
        cached = self._registry_type_cache.get(topic_id)
        if cached is not None:
            return cached

        topic_info = self._mirror_client.get_topic_info(topic_id)
        parsed = _parse_topic_memo(topic_info.get("memo"))
        if parsed is None:
            raise ValidationError(
                f"topic {topic_id} is not an HCS-2 registry",
                ErrorContext(details={"topic_id": topic_id}),
            )
        registry_type, _ttl = parsed
        self._registry_type_cache[topic_id] = registry_type
        return registry_type

    def _submit_message(
        self, registry_topic_id: str, message: Hcs2Message, analytics_memo: str | None
    ) -> OperationResult:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(
                "on-chain operator credentials are not configured", ErrorContext()
            )

        self._validate_message(message)
        topic_id = _validate_topic_id(registry_topic_id, "registryTopicId")

        payload = message.model_dump(by_alias=True, exclude_none=True)
        message_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        if len(message_bytes) > _MAX_MESSAGE_BYTES:
            raise ValidationError(
                (
                    f"HCS-2 payload exceeds {_MAX_MESSAGE_BYTES} bytes; "
                    "overflow inscription is required"
                ),
                ErrorContext(details={"bytes": len(message_bytes), "limit": _MAX_MESSAGE_BYTES}),
            )

        topic = self._hedera.TopicId.fromString(topic_id)
        transaction = (
            self._hedera.TopicMessageSubmitTransaction().setTopicId(topic).setMessage(message_bytes)
        )
        if isinstance(analytics_memo, str) and analytics_memo.strip():
            transaction.setTransactionMemo(analytics_memo.strip())

        try:
            response = transaction.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to submit HCS-2 topic message",
                ErrorContext(details={"reason": str(exc), "topic_id": topic_id}),
            ) from exc

        return OperationResult(
            success=True,
            transactionId=_to_string(getattr(response, "transactionId", None)) or None,
            sequenceNumber=_coerce_int(getattr(receipt, "topicSequenceNumber", None), default=0),
        )

    def createRegistry(self, *args: object, **kwargs: object) -> JsonValue:
        if len(args) > 1:
            raise ValidationError(
                "createRegistry expects at most one options object", ErrorContext()
            )
        payload: dict[str, object] = {}
        if len(args) == 1:
            payload.update(_coerce_mapping(args[0], "options"))
        payload.update(kwargs)
        try:
            options = CreateRegistryOptions.model_validate(payload)
        except PydanticValidationError as exc:
            raise ValidationError(
                "invalid createRegistry options",
                ErrorContext(details={"errors": exc.errors()}),
            ) from exc

        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(
                "on-chain operator credentials are not configured", ErrorContext()
            )

        registry_type = options.registry_type
        ttl = options.ttl if options.ttl > 0 else 86400
        memo_override = _clean(options.memo_override)
        topic_memo = memo_override or _build_topic_memo(registry_type, ttl)
        transaction = self._hedera.TopicCreateTransaction().setTopicMemo(topic_memo)

        admin_key = self._resolve_public_key(options.admin_key, options.use_operator_as_admin)
        if admin_key is not None:
            transaction.setAdminKey(admin_key)
        submit_key = self._resolve_public_key(options.submit_key, options.use_operator_as_submit)
        if submit_key is not None:
            transaction.setSubmitKey(submit_key)
        if _clean(options.transaction_memo):
            transaction.setTransactionMemo(_clean(options.transaction_memo))

        try:
            response = transaction.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to execute create topic transaction",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc

        topic_id = _to_string(getattr(receipt, "topicId", None))
        if not topic_id:
            raise ParseError("topic ID missing in create topic receipt", ErrorContext())
        self._registry_type_cache[topic_id] = registry_type

        result = CreateRegistryResult(
            success=True,
            topicId=topic_id,
            transactionId=_to_string(getattr(response, "transactionId", None)) or None,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def registerEntry(self, *args: object, **kwargs: object) -> JsonValue:
        parsed = self._parse_registry_operation_inputs(args, kwargs, allow_protocol=True)
        registry_topic_id, options_payload, protocol = parsed
        options = RegisterEntryOptions.model_validate(options_payload)

        message = Hcs2RegisterMessage(
            p=protocol,
            t_id=_validate_topic_id(options.target_topic_id, "targetTopicId"),
            metadata=options.metadata,
            m=options.memo,
        )
        registry_type = self._resolve_registry_type(registry_topic_id, options.registry_type)
        self._registry_type_cache[registry_topic_id] = registry_type
        analytics_memo = options.analytics_memo or _build_transaction_memo(
            Hcs2Operation.REGISTER, registry_type
        )

        result = self._submit_message(registry_topic_id, message, analytics_memo)
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def updateEntry(self, *args: object, **kwargs: object) -> JsonValue:
        registry_topic_id, options_payload, _protocol = self._parse_registry_operation_inputs(
            args, kwargs, allow_protocol=False
        )
        options = UpdateEntryOptions.model_validate(options_payload)
        registry_type = self._resolve_registry_type(registry_topic_id, options.registry_type)
        if registry_type != Hcs2RegistryType.INDEXED:
            raise ValidationError("update is only valid for indexed registries", ErrorContext())

        message = Hcs2UpdateMessage(
            p="hcs-2",
            uid=options.uid.strip(),
            t_id=_validate_topic_id(options.target_topic_id, "targetTopicId"),
            metadata=options.metadata,
            m=options.memo,
        )
        analytics_memo = options.analytics_memo or _build_transaction_memo(
            Hcs2Operation.UPDATE, registry_type
        )
        result = self._submit_message(registry_topic_id, message, analytics_memo)
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def deleteEntry(self, *args: object, **kwargs: object) -> JsonValue:
        registry_topic_id, options_payload, _protocol = self._parse_registry_operation_inputs(
            args, kwargs, allow_protocol=False
        )
        options = DeleteEntryOptions.model_validate(options_payload)
        registry_type = self._resolve_registry_type(registry_topic_id, options.registry_type)
        if registry_type != Hcs2RegistryType.INDEXED:
            raise ValidationError("delete is only valid for indexed registries", ErrorContext())

        message = Hcs2DeleteMessage(
            p="hcs-2",
            uid=options.uid.strip(),
            m=options.memo,
        )
        analytics_memo = options.analytics_memo or _build_transaction_memo(
            Hcs2Operation.DELETE, registry_type
        )
        result = self._submit_message(registry_topic_id, message, analytics_memo)
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def migrateRegistry(self, *args: object, **kwargs: object) -> JsonValue:
        registry_topic_id, options_payload, _protocol = self._parse_registry_operation_inputs(
            args, kwargs, allow_protocol=False
        )
        options = MigrateRegistryOptions.model_validate(options_payload)
        registry_type = self._resolve_registry_type(registry_topic_id, options.registry_type)

        message = Hcs2MigrateMessage(
            p="hcs-2",
            t_id=_validate_topic_id(options.target_topic_id, "targetTopicId"),
            metadata=options.metadata,
            m=options.memo,
        )
        analytics_memo = options.analytics_memo or _build_transaction_memo(
            Hcs2Operation.MIGRATE, registry_type
        )
        result = self._submit_message(registry_topic_id, message, analytics_memo)
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def getRegistry(self, *args: object, **kwargs: object) -> JsonValue:
        topic_id, options = self._parse_get_registry_inputs(args, kwargs)
        registry_topic_id = _validate_topic_id(topic_id, "topicId")
        topic_info = self._mirror_client.get_topic_info(registry_topic_id)
        parsed_memo = _parse_topic_memo(topic_info.get("memo"))
        if parsed_memo is None:
            raise ValidationError(
                f"topic {registry_topic_id} is not an HCS-2 registry",
                ErrorContext(details={"topic_id": registry_topic_id}),
            )
        registry_type, ttl = parsed_memo

        sequence = f"gt:{options.skip}" if options.skip > 0 else None
        topic_messages = self._mirror_client.get_topic_messages(
            registry_topic_id,
            sequence_number=sequence,
            limit=options.limit,
            order=options.order,
        )

        entries: list[RegistryEntry] = []
        latest_entry: RegistryEntry | None = None
        for item in topic_messages.messages:
            raw_item = item.model_dump(by_alias=True)
            decoded = self._decode_message_dict(item.message)
            if decoded is None:
                continue
            if (
                options.resolve_overflow
                and isinstance(decoded.get("metadata"), str)
                and _HCS1_REFERENCE_PATTERN.fullmatch(str(decoded.get("metadata")))
            ):
                resolved = self._resolve_hcs1_reference(str(decoded.get("metadata")))
                if resolved is not None:
                    decoded = resolved

            try:
                message = Hcs2Message.model_validate(decoded)
                self._validate_message(message)
            except (PydanticValidationError, ValidationError):
                continue

            entry = RegistryEntry(
                topicId=registry_topic_id,
                sequence=_coerce_int(raw_item.get("sequence_number"), default=0),
                timestamp=str(raw_item.get("consensus_timestamp") or ""),
                payer=str(raw_item.get("payer_account_id") or raw_item.get("payer") or ""),
                message=message,
                consensus_timestamp=str(raw_item.get("consensus_timestamp") or ""),
                registry_type=registry_type,
            )
            entries.append(entry)
            if latest_entry is None or entry.timestamp > latest_entry.timestamp:
                latest_entry = entry

        if registry_type == Hcs2RegistryType.NON_INDEXED:
            entries = [latest_entry] if latest_entry is not None else []

        self._registry_type_cache[registry_topic_id] = registry_type
        registry = TopicRegistry(
            topicId=registry_topic_id,
            registryType=registry_type,
            ttl=ttl,
            entries=entries,
            latestEntry=latest_entry,
        )
        return cast(JsonValue, registry.model_dump(by_alias=True, exclude_none=True))

    def submitMessage(self, *args: object, **kwargs: object) -> JsonValue:
        topic_id, payload, analytics_memo = self._parse_submit_message_inputs(args, kwargs)
        message = Hcs2Message.model_validate(payload)
        result = self._submit_message(topic_id, message, analytics_memo)
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def getTopicInfo(self, *args: object, **kwargs: object) -> JsonValue:
        topic_id = self._extract_topic_id(args, kwargs, method_name="getTopicInfo")
        return cast(JsonValue, self._mirror_client.get_topic_info(topic_id))

    def getKeyType(self, *args: object, **kwargs: object) -> JsonValue:
        _ = (args, kwargs)
        if self._key_type is None:
            raise ParseError("operator key type is unavailable", ErrorContext())
        return self._key_type

    def getOperatorKey(self, *args: object, **kwargs: object) -> JsonValue:
        _ = (args, kwargs)
        if self._operator_key is None:
            raise ParseError("operator key is unavailable", ErrorContext())
        return _to_string(self._operator_key.toString())

    def close(self, *args: object, **kwargs: object) -> JsonValue:
        _ = (args, kwargs)
        try:
            close_fn = getattr(self._hedera_client, "close", None)
            if self._hedera_client is not None and callable(close_fn):
                self._hedera_client.close()
        except Exception as exc:
            raise TransportError(
                "failed to close HCS-2 Hedera client",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc
        return None

    def _decode_message_dict(self, encoded: object) -> dict[str, object] | None:
        if not isinstance(encoded, str):
            return None
        try:
            decoded = base64.b64decode(encoded).decode("utf-8")
            payload = json.loads(decoded)
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        result: dict[str, object] = {}
        for key, value in payload.items():
            result[str(key)] = value
        return result

    def _resolve_hcs1_reference(self, metadata: str) -> dict[str, object] | None:
        match = _HCS1_REFERENCE_PATTERN.fullmatch(metadata.strip())
        if match is None:
            return None
        ref_topic_id = match.group(1)
        try:
            response = self._mirror_client.get_topic_messages(ref_topic_id, order="asc", limit=1)
        except Exception:
            return None
        if not response.messages:
            return None
        return self._decode_message_dict(response.messages[0].message)

    def _extract_topic_id(
        self, args: tuple[object, ...], kwargs: Mapping[str, object], *, method_name: str
    ) -> str:
        if args:
            first = args[0]
            if isinstance(first, str):
                return _validate_topic_id(first, "topicId")
            raise ValidationError(f"{method_name} requires topicId as string", ErrorContext())
        topic_value = kwargs.get("topicId", kwargs.get("topic_id"))
        if isinstance(topic_value, str):
            return _validate_topic_id(topic_value, "topicId")
        raise ValidationError(f"{method_name} requires topicId", ErrorContext())

    def _parse_registry_operation_inputs(
        self, args: tuple[object, ...], kwargs: Mapping[str, object], *, allow_protocol: bool
    ) -> tuple[str, dict[str, object], str]:
        if not args and "registryTopicId" not in kwargs and "registry_topic_id" not in kwargs:
            raise ValidationError("registryTopicId is required", ErrorContext())

        index = 0
        if args:
            if not isinstance(args[0], str):
                raise ValidationError("registryTopicId must be a string", ErrorContext())
            registry_topic_id = _validate_topic_id(args[0], "registryTopicId")
            index = 1
        else:
            topic_value = kwargs.get("registryTopicId", kwargs.get("registry_topic_id"))
            if not isinstance(topic_value, str):
                raise ValidationError("registryTopicId must be a string", ErrorContext())
            registry_topic_id = _validate_topic_id(topic_value, "registryTopicId")

        protocol = "hcs-2"
        if allow_protocol and len(args) > index + 1:
            protocol_arg = args[index + 1]
            if not isinstance(protocol_arg, str):
                raise ValidationError("protocol must be a string", ErrorContext())
            protocol = protocol_arg.strip() or "hcs-2"
        if allow_protocol and isinstance(kwargs.get("protocol"), str):
            protocol = cast(str, kwargs["protocol"]).strip() or "hcs-2"

        options_payload: dict[str, object] = {}
        if len(args) > index:
            options_payload.update(_coerce_mapping(args[index], "options"))
        if len(args) > index + (2 if allow_protocol else 1):
            raise ValidationError("too many positional arguments", ErrorContext())
        for key, value in kwargs.items():
            if key in {"registryTopicId", "registry_topic_id", "protocol"}:
                continue
            options_payload[key] = value
        return registry_topic_id, options_payload, protocol

    def _parse_get_registry_inputs(
        self, args: tuple[object, ...], kwargs: Mapping[str, object]
    ) -> tuple[str, QueryRegistryOptions]:
        topic_id = self._extract_topic_id(args, kwargs, method_name="getRegistry")
        options_payload: dict[str, object] = {}
        if len(args) >= 2:
            options_payload.update(_coerce_mapping(args[1], "options"))
        if len(args) > 2:
            raise ValidationError(
                "getRegistry expects at most two positional arguments",
                ErrorContext(),
            )
        for key, value in kwargs.items():
            if key in {"topicId", "topic_id"}:
                continue
            options_payload[key] = value
        try:
            options = QueryRegistryOptions.model_validate(options_payload)
        except PydanticValidationError as exc:
            raise ValidationError(
                "invalid getRegistry options",
                ErrorContext(details={"errors": exc.errors()}),
            ) from exc
        return topic_id, options

    def _parse_submit_message_inputs(
        self, args: tuple[object, ...], kwargs: Mapping[str, object]
    ) -> tuple[str, dict[str, object], str | None]:
        topic_id = self._extract_topic_id(args, kwargs, method_name="submitMessage")
        payload: dict[str, object] = {}
        analytics_memo: str | None = None

        if len(args) >= 2:
            payload.update(_coerce_mapping(args[1], "payload"))
        if len(args) >= 3:
            analytics_arg = args[2]
            analytics_memo = analytics_arg if isinstance(analytics_arg, str) else None
        if len(args) > 3:
            raise ValidationError(
                "submitMessage expects at most three positional arguments",
                ErrorContext(),
            )

        payload_value = kwargs.get("payload")
        if payload_value is not None:
            payload.update(_coerce_mapping(payload_value, "payload"))
        if isinstance(kwargs.get("analyticsMemo"), str):
            analytics_memo = cast(str, kwargs["analyticsMemo"])
        if isinstance(kwargs.get("analytics_memo"), str):
            analytics_memo = cast(str, kwargs["analytics_memo"])
        if not payload:
            for key, value in kwargs.items():
                if key in {"topicId", "topic_id", "payload", "analyticsMemo", "analytics_memo"}:
                    continue
                payload[key] = value
        if not payload:
            raise ValidationError("submitMessage requires payload", ErrorContext())
        return topic_id, payload, analytics_memo

    create_registry = createRegistry
    register_entry = registerEntry
    update_entry = updateEntry
    delete_entry = deleteEntry
    migrate_registry = migrateRegistry
    get_registry = getRegistry
    submit_message = submitMessage
    get_topic_info = getTopicInfo
    get_key_type = getKeyType
    get_operator_key = getOperatorKey


class AsyncHcs2Client(AsyncHcsModuleClient):
    """Asynchronous HCS-2 client."""

    def __init__(
        self,
        transport: AsyncHttpTransport | None = None,
        *,
        operator_id: str,
        operator_key: str,
        network: str = "testnet",
        mirror_base_url: str | None = None,
        key_type: str | None = None,
    ) -> None:
        config = SdkConfig.from_env()
        resolved_transport = transport or AsyncHttpTransport(
            base_url=config.network.registry_broker_base_url or _DEFAULT_REGISTRY_BROKER_BASE_URL,
        )
        super().__init__("hcs2", resolved_transport)

        self._sync_onchain = Hcs2Client(
            transport=SyncHttpTransport(
                base_url=resolved_transport.base_url,
                headers=dict(resolved_transport.headers or {}),
            ),
            operator_id=operator_id,
            operator_key=operator_key,
            network=network,
            mirror_base_url=mirror_base_url,
            key_type=key_type,
        )

    async def createRegistry(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_onchain.createRegistry, *args, **kwargs)

    async def registerEntry(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_onchain.registerEntry, *args, **kwargs)

    async def updateEntry(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_onchain.updateEntry, *args, **kwargs)

    async def deleteEntry(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_onchain.deleteEntry, *args, **kwargs)

    async def migrateRegistry(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_onchain.migrateRegistry, *args, **kwargs)

    async def getRegistry(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_onchain.getRegistry, *args, **kwargs)

    async def submitMessage(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_onchain.submitMessage, *args, **kwargs)

    async def getTopicInfo(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_onchain.getTopicInfo, *args, **kwargs)

    async def getKeyType(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_onchain.getKeyType, *args, **kwargs)

    async def getOperatorKey(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_onchain.getOperatorKey, *args, **kwargs)

    async def close(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_onchain.close, *args, **kwargs)

    create_registry = createRegistry
    register_entry = registerEntry
    update_entry = updateEntry
    delete_entry = deleteEntry
    migrate_registry = migrateRegistry
    get_registry = getRegistry
    submit_message = submitMessage
    get_topic_info = getTopicInfo
    get_key_type = getKeyType
    get_operator_key = getOperatorKey
