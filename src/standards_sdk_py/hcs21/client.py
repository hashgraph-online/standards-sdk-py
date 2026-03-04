"""HCS-21 client with direct on-chain execution parity."""

# ruff: noqa: N802

from __future__ import annotations

import asyncio
import base64
import importlib
import json
import re
import time
from collections.abc import Mapping
from typing import Any, Literal, cast

from standards_sdk_py.exceptions import ErrorContext, ParseError, TransportError, ValidationError
from standards_sdk_py.hcs2 import Hcs2Client, Hcs2RegistryType
from standards_sdk_py.hcs21.models import (
    Hcs21AdapterDeclaration,
    Hcs21BuildDeclarationParams,
    Hcs21CreateAdapterCategoryTopicOptions,
    Hcs21CreateAdapterVersionPointerTopicOptions,
    Hcs21CreateRegistryDiscoveryTopicOptions,
    Hcs21CreateRegistryTopicOptions,
    Hcs21CreateTopicResult,
    Hcs21InscribeMetadataOptions,
    Hcs21ManifestPointer,
    Hcs21PublishCategoryEntryOptions,
    Hcs21PublishDeclarationOptions,
    Hcs21PublishResult,
    Hcs21PublishVersionPointerOptions,
    Hcs21RegisterCategoryTopicOptions,
    Hcs21TopicType,
    Hcs21VersionPointerResolution,
)
from standards_sdk_py.inscriber import (
    InscribeViaRegistryBrokerOptions,
    InscriptionInput,
    inscribe,
)
from standards_sdk_py.mirror import HederaMirrorNode
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.hcs_module import AsyncHcsModuleClient, HcsModuleClient
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.types import JsonValue

_DEFAULT_REGISTRY_BROKER_BASE_URL = "https://registry.hashgraphonline.com"
_DEFAULT_INSCRIBER_BASE_URL = "https://hol.org/registry/api/v1"
_DEFAULT_INSCRIBER_TIMEOUT_MS = 120000
_DEFAULT_INSCRIBER_POLL_INTERVAL_MS = 2000
_MANIFEST_POINTER_PATTERN = re.compile(
    r"^(?:hcs:\/\/1\/0\.0\.\d+|ipfs:\/\/\S+|ar:\/\/\S+|oci:\/\/\S+|https?:\/\/\S+)$"
)
_METADATA_POINTER_PATTERN = re.compile(
    r"^(?:0\.0\.\d+|hcs:\/\/1\/0\.0\.\d+(?:\/\d+)?|ipfs:\/\/\S+|ar:\/\/\S+|oci:\/\/\S+|https?:\/\/\S+)$"
)
_TOPIC_ID_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_ONCHAIN_CREDS_ERROR = "on-chain operator credentials are not configured"


def _clean(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _to_string(value: object | None) -> str:
    if value is None:
        return ""
    to_string = getattr(value, "toString", None)
    if callable(to_string):
        rendered = to_string()
        if isinstance(rendered, str):
            return rendered
    return str(value)


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


def _validate_topic_id(value: str, field_name: str = "topicId") -> str:
    cleaned = value.strip()
    if not _TOPIC_ID_PATTERN.fullmatch(cleaned):
        raise ValidationError(
            f"{field_name} must be a Hedera topic ID (e.g. 0.0.12345)",
            ErrorContext(details={"field": field_name, "value": value}),
        )
    return cleaned


def _normalize_indexed(value: int | bool) -> int:
    if isinstance(value, bool):
        return 0 if value else 1
    if value not in {0, 1}:
        raise ValidationError(
            "indexed must be 0 or 1 (or boolean)",
            ErrorContext(details={"indexed": value}),
        )
    return value


def _coerce_int(value: object, *, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except Exception:
            return default
    return default


def _merge_inscription_options(
    raw: dict[str, object] | None,
    document: dict[str, object],
) -> dict[str, object]:
    payload = dict(raw or {})
    mapped: dict[str, object] = {}
    for key, value in payload.items():
        if key == "waitForConfirmation":
            mapped["wait_for_confirmation"] = value
        elif key == "waitTimeoutMs":
            mapped["wait_timeout_ms"] = value
        elif key == "pollIntervalMs":
            mapped["poll_interval_ms"] = value
        elif key == "fileStandard":
            mapped["file_standard"] = value
        elif key == "chunkSize":
            mapped["chunk_size"] = value
        elif key == "baseUrl":
            mapped["base_url"] = value
        elif key == "apiKey":
            mapped["api_key"] = value
        else:
            mapped[key] = value

    merged_metadata: dict[str, object] = dict(document)
    existing_metadata = mapped.get("metadata")
    if isinstance(existing_metadata, dict):
        for key, value in existing_metadata.items():
            if isinstance(key, str):
                merged_metadata[key] = value
    mapped["metadata"] = merged_metadata
    if "wait_for_confirmation" not in mapped:
        mapped["wait_for_confirmation"] = True
    return mapped


def _coerce_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _coerce_int_opt(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except Exception:
            return None
    return None


def _coerce_bool(value: object, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _build_inscription_options(
    raw: dict[str, object] | None,
    document: dict[str, object],
) -> InscribeViaRegistryBrokerOptions:
    payload = _merge_inscription_options(raw, document)
    mode: Literal["file", "upload", "hashinal", "hashinal-collection", "bulk-files"] = "file"
    raw_mode = payload.get("mode")
    if isinstance(raw_mode, str):
        normalized_mode = raw_mode.strip()
        if normalized_mode in {"file", "upload", "hashinal", "hashinal-collection", "bulk-files"}:
            mode = cast(
                Literal["file", "upload", "hashinal", "hashinal-collection", "bulk-files"],
                normalized_mode,
            )

    metadata_value = payload.get("metadata")
    metadata: dict[str, object] | None = None
    if isinstance(metadata_value, dict):
        metadata = {str(key): value for key, value in metadata_value.items()}

    tags_value = payload.get("tags")
    tags: list[str] | None = None
    if isinstance(tags_value, list):
        collected = [item.strip() for item in tags_value if isinstance(item, str) and item.strip()]
        if collected:
            tags = collected

    return InscribeViaRegistryBrokerOptions(
        base_url=_coerce_str(payload.get("base_url")) or _DEFAULT_INSCRIBER_BASE_URL,
        api_key=_coerce_str(payload.get("api_key")),
        ledger_api_key=_coerce_str(payload.get("ledger_api_key")),
        ledger_account_id=_coerce_str(payload.get("ledger_account_id")),
        ledger_private_key=_coerce_str(payload.get("ledger_private_key")),
        ledger_network=_coerce_str(payload.get("ledger_network")) or "testnet",
        ledger_expires_in_minutes=_coerce_int_opt(payload.get("ledger_expires_in_minutes")),
        mode=mode,
        metadata=metadata,
        tags=tags,
        file_standard=_coerce_str(payload.get("file_standard")),
        chunk_size=_coerce_int_opt(payload.get("chunk_size")),
        wait_for_confirmation=_coerce_bool(payload.get("wait_for_confirmation"), default=True),
        wait_timeout_ms=_coerce_int_opt(payload.get("wait_timeout_ms"))
        or _DEFAULT_INSCRIBER_TIMEOUT_MS,
        poll_interval_ms=_coerce_int_opt(payload.get("poll_interval_ms"))
        or _DEFAULT_INSCRIBER_POLL_INTERVAL_MS,
    )


class Hcs21Client(HcsModuleClient):
    """Synchronous HCS-21 client."""

    def __init__(
        self,
        transport: SyncHttpTransport | None = None,
        *,
        operator_id: str,
        operator_key: str,
        network: str = "testnet",
        mirror_base_url: str | None = None,
        key_type: str | None = None,
    ) -> None:
        config = SdkConfig.from_env()
        resolved_transport = transport or SyncHttpTransport(
            base_url=config.network.registry_broker_base_url or _DEFAULT_REGISTRY_BROKER_BASE_URL,
        )
        super().__init__("hcs21", resolved_transport)
        self._network = _normalize_network(network)
        self._hedera: Any | None = None
        self._hedera_client: Any | None = None
        self._operator_id: str | None = None
        self._operator_key: Any | None = None
        self._operator_key_string: str | None = None

        cleaned_operator_id = _clean(operator_id)
        cleaned_operator_key = _clean(operator_key)
        if not cleaned_operator_id:
            raise ValidationError("operator_id is required", ErrorContext())
        if not cleaned_operator_key:
            raise ValidationError("operator_key is required", ErrorContext())
        self._initialize_onchain(cleaned_operator_id, cleaned_operator_key, key_type=key_type)

        resolved_mirror_base_url = _clean(mirror_base_url) or config.network.mirror_node_base_url
        self._mirror_client = HederaMirrorNode(
            transport=SyncHttpTransport(base_url=resolved_mirror_base_url)
        )
        self._hcs2_client = Hcs2Client(
            transport=SyncHttpTransport(
                base_url=resolved_transport.base_url,
                headers=dict(resolved_transport.headers or {}),
            ),
            operator_id=cleaned_operator_id,
            operator_key=cleaned_operator_key,
            network=self._network,
            mirror_base_url=resolved_mirror_base_url,
        )

    def _initialize_onchain(
        self, operator_id: str, operator_key: str, *, key_type: str | None
    ) -> None:
        try:
            hedera = importlib.import_module("hedera")
        except ModuleNotFoundError as exc:
            raise ValidationError(
                "hedera-sdk-py is required for on-chain HCS-21 operations",
                ErrorContext(details={"dependency": "hedera-sdk-py"}),
            ) from exc

        try:
            account_id = hedera.AccountId.fromString(operator_id)
            private_key = hedera.PrivateKey.fromString(operator_key)
        except Exception as exc:
            raise ValidationError(
                "invalid operator credentials",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc

        client = (
            hedera.Client.forMainnet() if self._network == "mainnet" else hedera.Client.forTestnet()
        )
        client.setOperator(account_id, private_key)
        self._hedera = hedera
        self._hedera_client = client
        self._operator_id = operator_id
        self._operator_key = private_key
        self._operator_key_string = operator_key
        _ = key_type

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
                    private_key = self._hedera.PrivateKey.fromString(cleaned)
                    return cast(object, private_key.getPublicKey())
                except Exception:
                    return None
        return None

    def _options_payload(self, args: tuple[object, ...], kwargs: dict[str, object]) -> object:
        if kwargs:
            return kwargs
        if args:
            return args[0]
        return {}

    def _build_registry_memo(
        self,
        *,
        ttl: int,
        indexed: int | bool,
        topic_type: Hcs21TopicType,
        meta_topic_id: str | None,
    ) -> str:
        resolved_ttl = ttl if ttl > 0 else 86400
        indexed_segment = _normalize_indexed(indexed)
        memo = f"hcs-21:{indexed_segment}:{resolved_ttl}:{int(topic_type)}"
        meta = _clean(meta_topic_id)
        if meta:
            if not _METADATA_POINTER_PATTERN.fullmatch(meta):
                raise ValidationError(
                    (
                        "metaTopicId must be a short pointer "
                        "(topic ID, HRL, IPFS, Arweave, OCI, or HTTPS)"
                    ),
                    ErrorContext(details={"metaTopicId": meta}),
                )
            memo = f"{memo}:{meta}"
        return memo

    def _create_topic(
        self,
        *,
        topic_memo: str,
        admin_key: object | None,
        submit_key: object | None,
        transaction_memo: str | None,
    ) -> Hcs21CreateTopicResult:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(_ONCHAIN_CREDS_ERROR, ErrorContext())
        tx = self._hedera.TopicCreateTransaction().setTopicMemo(topic_memo)
        if admin_key is not None:
            tx.setAdminKey(admin_key)
        if submit_key is not None:
            tx.setSubmitKey(submit_key)
        if _clean(transaction_memo):
            tx.setTransactionMemo(_clean(transaction_memo))
        try:
            response = tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to create HCS-21 topic",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc
        topic_id = _to_string(getattr(receipt, "topicId", None))
        if not topic_id:
            raise ParseError("failed to create HCS-21 topic", ErrorContext())
        return Hcs21CreateTopicResult(
            topicId=topic_id,
            transactionId=_to_string(getattr(response, "transactionId", None)) or None,
        )

    def _publish_topic_message(
        self, topic_id: str, payload: Mapping[str, object], transaction_memo: str | None
    ) -> Hcs21PublishResult:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(_ONCHAIN_CREDS_ERROR, ErrorContext())
        validated_topic_id = _validate_topic_id(topic_id)
        tx = self._hedera.TopicMessageSubmitTransaction().setTopicId(
            self._hedera.TopicId.fromString(validated_topic_id)
        )
        tx.setMessage(
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        )
        if _clean(transaction_memo):
            tx.setTransactionMemo(_clean(transaction_memo))
        try:
            response = tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to submit HCS-21 topic message",
                ErrorContext(details={"reason": str(exc), "topic_id": topic_id}),
            ) from exc
        return Hcs21PublishResult(
            sequenceNumber=_coerce_int(getattr(receipt, "topicSequenceNumber", 0)),
            transactionId=_to_string(getattr(response, "transactionId", None)),
            topicId=validated_topic_id,
        )

    def _validate_declaration(
        self, declaration: Hcs21AdapterDeclaration
    ) -> Hcs21AdapterDeclaration:
        if declaration.p != "hcs-21":
            raise ValidationError("declaration p must be hcs-21", ErrorContext())
        if not _MANIFEST_POINTER_PATTERN.fullmatch(declaration.manifest):
            raise ValidationError(
                "manifest must be immutable pointer",
                ErrorContext(details={"manifest": declaration.manifest}),
            )
        config_type = declaration.config.get("type")
        if not isinstance(config_type, str) or not config_type.strip():
            raise ValidationError("config.type is required", ErrorContext())
        payload = declaration.model_dump(by_alias=True, exclude_none=True)
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        if len(encoded) > 1000:
            raise ValidationError(
                "payload exceeds safe limit of 1000 bytes",
                ErrorContext(details={"bytes": len(encoded)}),
            )
        if len(encoded) > 1024:
            raise ValidationError(
                "payload exceeds Hedera max 1024 bytes",
                ErrorContext(details={"bytes": len(encoded)}),
            )
        return declaration

    def _normalize_declaration_input(
        self, raw: Hcs21AdapterDeclaration | Hcs21BuildDeclarationParams | dict[str, object]
    ) -> Hcs21AdapterDeclaration:
        if isinstance(raw, Hcs21AdapterDeclaration):
            return self._validate_declaration(raw)
        if isinstance(raw, Hcs21BuildDeclarationParams):
            return self._validate_declaration(
                Hcs21AdapterDeclaration(
                    p="hcs-21",
                    op=raw.op,
                    adapter_id=raw.adapter_id,
                    entity=raw.entity,
                    package=raw.package,
                    manifest=raw.manifest,
                    manifest_sequence=raw.manifest_sequence,
                    config=raw.config,
                    state_model=raw.state_model,
                    signature=raw.signature,
                )
            )
        if "p" in raw:
            return self._validate_declaration(Hcs21AdapterDeclaration.model_validate(raw))
        params = Hcs21BuildDeclarationParams.model_validate(raw)
        return self._validate_declaration(
            Hcs21AdapterDeclaration(
                p="hcs-21",
                op=params.op,
                adapter_id=params.adapter_id,
                entity=params.entity,
                package=params.package,
                manifest=params.manifest,
                manifest_sequence=params.manifest_sequence,
                config=params.config,
                state_model=params.state_model,
                signature=params.signature,
            )
        )

    def _extract_topic_result(self, result: JsonValue, *, operation: str) -> Hcs21CreateTopicResult:
        if not isinstance(result, dict):
            raise ParseError(
                f"{operation} returned unexpected result type",
                ErrorContext(details={"type": type(result).__name__}),
            )
        topic_id = _clean(result.get("topicId")) if isinstance(result.get("topicId"), str) else ""
        if not topic_id:
            raise ParseError(
                f"{operation} did not return topicId",
                ErrorContext(details={"result": result}),
            )
        raw_transaction_id = result.get("transactionId")
        transaction_id = raw_transaction_id if isinstance(raw_transaction_id, str) else None
        return Hcs21CreateTopicResult(topicId=topic_id, transactionId=transaction_id)

    def _publish_hcs2_register(
        self,
        registry_topic_id: str,
        *,
        target_topic_id: str,
        metadata: str | None,
        memo: str | None,
        transaction_memo: str | None,
        registry_type: Hcs2RegistryType,
    ) -> Hcs21PublishResult:
        raw = self._hcs2_client.registerEntry(
            registry_topic_id,
            {
                "targetTopicId": target_topic_id,
                "metadata": metadata,
                "memo": memo,
                "analyticsMemo": transaction_memo,
                "registryType": registry_type,
            },
        )
        if not isinstance(raw, dict):
            raise ParseError("HCS-2 registerEntry returned unexpected response", ErrorContext())
        sequence = raw.get("sequenceNumber")
        transaction_id = raw.get("transactionId")
        if not isinstance(sequence, int):
            sequence = _coerce_int(sequence)
        if not isinstance(transaction_id, str) or not transaction_id.strip():
            raise ParseError(
                "HCS-2 registerEntry response missing transactionId",
                ErrorContext(details={"response": raw}),
            )
        return Hcs21PublishResult(
            sequenceNumber=sequence,
            transactionId=transaction_id,
            topicId=_validate_topic_id(registry_topic_id),
        )

    def _resolve_manifest_pointer(
        self, topic_id: str, sequence_number: int | None = None
    ) -> tuple[str, int]:
        resolved_topic_id = _validate_topic_id(topic_id)
        resolved_sequence = sequence_number if sequence_number and sequence_number > 0 else None
        if resolved_sequence is None:
            messages = self._mirror_client.get_topic_messages(
                resolved_topic_id, limit=1, order="desc"
            )
            if not messages.messages:
                raise ParseError(
                    "unable to resolve manifest sequence number",
                    ErrorContext(details={"topic_id": resolved_topic_id}),
                )
            resolved_sequence = messages.messages[0].sequence_number or 0
        if resolved_sequence <= 0:
            raise ParseError(
                "invalid manifest sequence number",
                ErrorContext(
                    details={"topic_id": resolved_topic_id, "sequence_number": resolved_sequence}
                ),
            )
        pointer = f"hcs://1/{resolved_topic_id}"
        if not _MANIFEST_POINTER_PATTERN.fullmatch(pointer):
            raise ValidationError("manifest pointer format is invalid", ErrorContext())
        return pointer, resolved_sequence

    def createRegistryTopic(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs21CreateRegistryTopicOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        memo = self._build_registry_memo(
            ttl=options.ttl,
            indexed=options.indexed,
            topic_type=options.topic_type,
            meta_topic_id=options.meta_topic_id,
        )
        result = self._create_topic(
            topic_memo=memo,
            admin_key=self._resolve_public_key(options.admin_key, options.use_operator_as_admin),
            submit_key=self._resolve_public_key(options.submit_key, options.use_operator_as_submit),
            transaction_memo=options.transaction_memo,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def createAdapterVersionPointerTopic(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs21CreateAdapterVersionPointerTopicOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        result = self._hcs2_client.createRegistry(
            {
                "registryType": Hcs2RegistryType.NON_INDEXED,
                "ttl": options.ttl,
                "adminKey": options.admin_key,
                "submitKey": options.submit_key,
                "useOperatorAsAdmin": options.use_operator_as_admin,
                "useOperatorAsSubmit": options.use_operator_as_submit,
                "memoOverride": options.memo_override,
                "transactionMemo": options.transaction_memo,
            }
        )
        extracted = self._extract_topic_result(result, operation="createAdapterVersionPointerTopic")
        return cast(JsonValue, extracted.model_dump(by_alias=True, exclude_none=True))

    def createRegistryDiscoveryTopic(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs21CreateRegistryDiscoveryTopicOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        result = self._hcs2_client.createRegistry(
            {
                "registryType": Hcs2RegistryType.INDEXED,
                "ttl": options.ttl,
                "adminKey": options.admin_key,
                "submitKey": options.submit_key,
                "useOperatorAsAdmin": options.use_operator_as_admin,
                "useOperatorAsSubmit": options.use_operator_as_submit,
                "memoOverride": options.memo_override,
                "transactionMemo": options.transaction_memo,
            }
        )
        extracted = self._extract_topic_result(result, operation="createRegistryDiscoveryTopic")
        return cast(JsonValue, extracted.model_dump(by_alias=True, exclude_none=True))

    def createAdapterCategoryTopic(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs21CreateAdapterCategoryTopicOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        return self.createRegistryTopic(
            {
                "ttl": options.ttl,
                "indexed": options.indexed,
                "type": Hcs21TopicType.ADAPTER_CATEGORY,
                "metaTopicId": options.meta_topic_id,
                "adminKey": options.admin_key,
                "submitKey": options.submit_key,
                "useOperatorAsAdmin": options.use_operator_as_admin,
                "useOperatorAsSubmit": options.use_operator_as_submit,
                "transactionMemo": options.transaction_memo,
            }
        )

    def publishDeclaration(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs21PublishDeclarationOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        declaration = self._normalize_declaration_input(options.declaration)
        result = self._publish_topic_message(
            options.topic_id,
            declaration.model_dump(by_alias=True, exclude_none=True),
            options.transaction_memo,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def publishVersionPointer(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs21PublishVersionPointerOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        result = self._publish_hcs2_register(
            options.version_topic_id,
            target_topic_id=options.declaration_topic_id,
            metadata=None,
            memo=options.memo,
            transaction_memo=options.transaction_memo,
            registry_type=Hcs2RegistryType.NON_INDEXED,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def registerCategoryTopic(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs21RegisterCategoryTopicOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        result = self._publish_hcs2_register(
            options.discovery_topic_id,
            target_topic_id=options.category_topic_id,
            metadata=options.metadata,
            memo=options.memo,
            transaction_memo=options.transaction_memo,
            registry_type=Hcs2RegistryType.INDEXED,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def publishCategoryEntry(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs21PublishCategoryEntryOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        memo = _clean(options.memo) or f"adapter:{_clean(options.adapter_id)}"
        result = self._publish_hcs2_register(
            options.category_topic_id,
            target_topic_id=options.version_topic_id,
            metadata=options.metadata,
            memo=memo,
            transaction_memo=options.transaction_memo,
            registry_type=Hcs2RegistryType.INDEXED,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def resolveVersionPointer(self, *args: object, **kwargs: object) -> JsonValue:
        payload = self._options_payload(args, dict(kwargs))
        topic_id = ""
        if isinstance(payload, str):
            topic_id = payload
        elif isinstance(payload, dict):
            raw = payload.get("versionTopicId")
            if isinstance(raw, str):
                topic_id = raw
        elif args and isinstance(args[0], str):
            topic_id = args[0]
        resolved_topic_id = _validate_topic_id(topic_id, "versionTopicId")
        messages = self._mirror_client.get_topic_messages(resolved_topic_id, limit=1, order="desc")
        if not messages.messages:
            raise ParseError(
                "version pointer topic has no messages",
                ErrorContext(details={"topic_id": resolved_topic_id}),
            )
        latest = messages.messages[0]
        try:
            decoded = base64.b64decode(latest.message).decode("utf-8")
            payload_message = json.loads(decoded)
        except Exception as exc:
            raise ParseError(
                "failed to decode version pointer message payload",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc
        if not isinstance(payload_message, dict):
            raise ParseError("version pointer payload is not an object", ErrorContext())
        raw_target_topic_id = payload_message.get("t_id")
        if not isinstance(raw_target_topic_id, str) or not raw_target_topic_id.strip():
            raise ParseError(
                "version pointer payload does not include declaration topic ID (`t_id`)",
                ErrorContext(details={"payload": payload_message}),
            )
        sequence_number = latest.sequence_number or _coerce_int(
            payload_message.get("sequence_number")
        )
        result = Hcs21VersionPointerResolution(
            versionTopicId=resolved_topic_id,
            declarationTopicId=_validate_topic_id(raw_target_topic_id, "declarationTopicId"),
            sequenceNumber=sequence_number,
            payer=cast(str | None, payload_message.get("payer")),
            memo=cast(str | None, payload_message.get("m")),
            op=cast(str | None, payload_message.get("op")),
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def inscribeMetadata(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs21InscribeMetadataOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        file_name = (
            _clean(options.file_name) or f"hcs21-adapter-manifest-{int(time.time() * 1000)}.json"
        )
        payload = json.dumps(options.document, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
        inscription_result = inscribe(
            InscriptionInput(
                type="buffer",
                buffer=payload,
                fileName=file_name,
                mimeType="application/json",
            ),
            _build_inscription_options(options.inscription_options, options.document),
        )
        if not inscription_result.confirmed:
            raise TransportError(
                "failed to inscribe HCS-21 metadata document",
                ErrorContext(
                    details={
                        "job_id": inscription_result.job_id,
                        "status": inscription_result.status,
                    }
                ),
            )
        topic_id = _clean(inscription_result.topic_id)
        if not topic_id and _clean(inscription_result.hrl).startswith("hcs://1/"):
            topic_id = _clean(inscription_result.hrl).removeprefix("hcs://1/").split("/")[0]
        if not topic_id:
            raise ParseError(
                "metadata inscription did not return a topic ID",
                ErrorContext(
                    details={"hrl": inscription_result.hrl, "job_id": inscription_result.job_id}
                ),
            )
        pointer, sequence_number = self._resolve_manifest_pointer(topic_id)
        result = Hcs21ManifestPointer(
            pointer=pointer,
            topicId=topic_id,
            sequenceNumber=sequence_number,
            manifestSequence=sequence_number,
            jobId=inscription_result.job_id,
            transactionId=None,
            totalCostHbar=None,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    create_registry_topic = createRegistryTopic
    create_adapter_version_pointer_topic = createAdapterVersionPointerTopic
    create_registry_discovery_topic = createRegistryDiscoveryTopic
    create_adapter_category_topic = createAdapterCategoryTopic
    publish_declaration = publishDeclaration
    publish_version_pointer = publishVersionPointer
    register_category_topic = registerCategoryTopic
    publish_category_entry = publishCategoryEntry
    resolve_version_pointer = resolveVersionPointer
    inscribe_metadata = inscribeMetadata


class AsyncHcs21Client(AsyncHcsModuleClient):
    """Asynchronous HCS-21 client."""

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
        super().__init__("hcs21", resolved_transport)
        self._sync_client = Hcs21Client(
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

    async def createRegistryTopic(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.createRegistryTopic, *args, **kwargs)

    async def createAdapterVersionPointerTopic(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(
            self._sync_client.createAdapterVersionPointerTopic, *args, **kwargs
        )

    async def createRegistryDiscoveryTopic(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(
            self._sync_client.createRegistryDiscoveryTopic, *args, **kwargs
        )

    async def createAdapterCategoryTopic(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(
            self._sync_client.createAdapterCategoryTopic, *args, **kwargs
        )

    async def publishDeclaration(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.publishDeclaration, *args, **kwargs)

    async def publishVersionPointer(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.publishVersionPointer, *args, **kwargs)

    async def registerCategoryTopic(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.registerCategoryTopic, *args, **kwargs)

    async def publishCategoryEntry(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.publishCategoryEntry, *args, **kwargs)

    async def resolveVersionPointer(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.resolveVersionPointer, *args, **kwargs)

    async def inscribeMetadata(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.inscribeMetadata, *args, **kwargs)

    create_registry_topic = createRegistryTopic
    create_adapter_version_pointer_topic = createAdapterVersionPointerTopic
    create_registry_discovery_topic = createRegistryDiscoveryTopic
    create_adapter_category_topic = createAdapterCategoryTopic
    publish_declaration = publishDeclaration
    publish_version_pointer = publishVersionPointer
    register_category_topic = registerCategoryTopic
    publish_category_entry = publishCategoryEntry
    resolve_version_pointer = resolveVersionPointer
    inscribe_metadata = inscribeMetadata
