"""HCS-27 client aligned to the published draft."""

# ruff: noqa: N802

from __future__ import annotations

import asyncio
import base64
import hashlib
import importlib
import json
import math
import re
import time
from collections.abc import Callable, Mapping, Sequence
from importlib import import_module
from typing import Any, cast
from urllib.parse import unquote_to_bytes

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from standards_sdk_py.exceptions import ErrorContext, ParseError, TransportError, ValidationError
from standards_sdk_py.hcs27.models import (
    Hcs27CheckpointMessage,
    Hcs27CheckpointMetadata,
    Hcs27CheckpointRecord,
    Hcs27ConsistencyProof,
    Hcs27CreateCheckpointTopicOptions,
    Hcs27CreateCheckpointTopicResult,
    Hcs27InclusionProof,
    Hcs27MetadataDigest,
    Hcs27PublishCheckpointResult,
    Hcs27TopicMemo,
)
from standards_sdk_py.inscriber import (
    InscribeViaRegistryBrokerOptions,
    InscriptionInput,
    inscribe,
)
from standards_sdk_py.mirror import MirrorNodeClient
from standards_sdk_py.mirror.models import MirrorTopicMessage, MirrorTopicMessagesResponse
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.hcs_module import AsyncHcsModuleClient, HcsModuleClient
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.types import JsonObject, JsonValue

_DEFAULT_REGISTRY_BROKER_BASE_URL = "https://registry.hashgraphonline.com"
_DEFAULT_MIRROR_BY_NETWORK = {
    "mainnet": "https://mainnet-public.mirrornode.hedera.com/api/v1",
    "testnet": "https://testnet.mirrornode.hedera.com/api/v1",
}
_ONCHAIN_CREDS_ERROR = "on-chain operator credentials are not configured"
_HCS1_URI_RE = re.compile(r"^hcs://1/(\d+\.\d+\.\d+)$")
_MAX_MESSAGE_MEMO_CHARS = 299
_brotli = import_module("brotli")


def _clean(value: object | None) -> str:
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
    to_string = getattr(value, "to_string", None)
    if callable(to_string):
        rendered = to_string()
        if isinstance(rendered, str):
            return rendered
    return str(value)


def _coerce_mapping(value: object, field_name: str) -> dict[str, object]:
    if isinstance(value, BaseModel):
        return cast(dict[str, object], value.model_dump(by_alias=True, exclude_none=True))
    if isinstance(value, Mapping):
        return {str(k): cast(object, v) for k, v in value.items()}
    raise ValidationError(
        f"{field_name} must be a mapping/object",
        ErrorContext(details={"field": field_name, "type": type(value).__name__}),
    )


def _encode_base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _decode_base64url(value: str, field_name: str) -> bytes:
    trimmed = value.strip()
    if not trimmed:
        raise ValidationError(f"{field_name} is required", ErrorContext())
    padding = "=" * ((4 - (len(trimmed) % 4)) % 4)
    try:
        return base64.urlsafe_b64decode(trimmed + padding)
    except Exception as exc:
        raise ValidationError(
            f"{field_name} must be base64url",
            ErrorContext(details={"field": field_name, "reason": str(exc)}),
        ) from exc


def _decode_base64(value: str, field_name: str) -> bytes:
    try:
        return base64.b64decode(value)
    except Exception as exc:
        raise ValidationError(
            f"{field_name} must be base64",
            ErrorContext(details={"field": field_name, "reason": str(exc)}),
        ) from exc


def _parse_canonical_uint(field_name: str, value: str) -> int:
    if value == "":
        raise ValidationError(f"{field_name} is required", ErrorContext())
    if value != value.strip():
        raise ValidationError(
            f"{field_name} must be a canonical base-10 string",
            ErrorContext(details={"field": field_name, "value": value}),
        )
    if value != "0" and value.startswith("0"):
        raise ValidationError(
            f"{field_name} must be a canonical base-10 string",
            ErrorContext(details={"field": field_name, "value": value}),
        )
    try:
        parsed = int(value, 10)
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be a canonical base-10 string",
            ErrorContext(details={"field": field_name, "value": value}),
        ) from exc
    if parsed < 0:
        raise ValidationError(
            f"{field_name} must be a canonical base-10 string",
            ErrorContext(details={"field": field_name, "value": value}),
        )
    return parsed


def _canonical_uint(value: int) -> str:
    return str(value)


def _coerce_int(value: object, *, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return default
        try:
            return int(trimmed)
        except ValueError:
            return default
    return default


def _normalize_json_value(value: object) -> object:
    if isinstance(value, BaseModel):
        return _normalize_json_value(value.model_dump(by_alias=True, exclude_none=True))
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationError("JSON float values must be finite", ErrorContext())
        return value
    if isinstance(value, Mapping):
        return {str(key): _normalize_json_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_normalize_json_value(item) for item in value]
    try:
        serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        parsed = json.loads(serialized)
    except Exception as exc:
        raise ValidationError(
            "failed to normalize JSON input",
            ErrorContext(details={"reason": str(exc), "type": type(value).__name__}),
        ) from exc
    return _normalize_json_value(parsed)


def _format_json_float(value: float) -> str:
    rendered = format(value, ".17g")
    if rendered == "-0":
        return "0"
    return rendered


def _write_canonical_json(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _format_json_float(value)
    if isinstance(value, list):
        return "[" + ",".join(_write_canonical_json(item) for item in value) + "]"
    if isinstance(value, dict):
        parts = [
            json.dumps(key, ensure_ascii=False) + ":" + _write_canonical_json(value[key])
            for key in sorted(value)
        ]
        return "{" + ",".join(parts) + "}"
    raise ValidationError(
        "unsupported JSON value type",
        ErrorContext(details={"type": type(value).__name__}),
    )


def _canonicalize_json(value: object) -> bytes:
    normalized = _normalize_json_value(value)
    return _write_canonical_json(normalized).encode("utf-8")


def _encode_json_bytes(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _largest_power_of_two_less_than(value: int) -> int:
    if value <= 1:
        return 0
    result = 1
    while result << 1 < value:
        result <<= 1
    return result


def _least_significant_bit(value: int) -> int:
    return value & 1


def _is_exact_power_of_two(value: int) -> bool:
    return value != 0 and (value & (value - 1)) == 0


def _hash_leaf_bytes(canonical_entry: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + canonical_entry).digest()


def _hash_node_bytes(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def _coerce_hash_bytes(value: object, field_name: str) -> bytes:
    if isinstance(value, bytes | bytearray):
        return bytes(value)
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            raise ValidationError(f"{field_name} is required", ErrorContext())
        try:
            return bytes.fromhex(trimmed)
        except ValueError:
            return _decode_base64(trimmed, field_name)
    raise ValidationError(
        f"{field_name} must be bytes or an encoded string",
        ErrorContext(details={"field": field_name, "type": type(value).__name__}),
    )


def _parse_model(model_cls: type[BaseModel], value: object, *, message: str) -> BaseModel:
    try:
        return model_cls.model_validate(value)
    except PydanticValidationError as exc:
        raise ValidationError(
            message,
            ErrorContext(details={"errors": exc.errors()}),
        ) from exc


class Hcs27Client(HcsModuleClient):
    """Synchronous HCS-27 client."""

    def __init__(
        self,
        transport: SyncHttpTransport | None = None,
        *,
        operator_id: str | None = None,
        operator_key: str | None = None,
        hedera_client: object | None = None,
        network: str = "testnet",
        mirror_base_url: str | None = None,
        mirror_client: MirrorNodeClient | None = None,
    ) -> None:
        config = SdkConfig.from_env()
        resolved_transport = transport or SyncHttpTransport(
            base_url=config.network.registry_broker_base_url or _DEFAULT_REGISTRY_BROKER_BASE_URL,
        )
        super().__init__("hcs27", resolved_transport)
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
        self._operator_id = _clean(operator_id)
        self._operator_key_raw = _clean(operator_key)
        self._operator_key: Any | None = None
        if hedera_client is not None or self._operator_id or self._operator_key_raw:
            self._initialize_onchain(
                operator_id=self._operator_id,
                operator_key=self._operator_key_raw,
                hedera_client=hedera_client,
            )

    def _initialize_onchain(
        self,
        *,
        operator_id: str,
        operator_key: str,
        hedera_client: object | None,
    ) -> None:
        try:
            hedera = importlib.import_module("hedera")
        except ModuleNotFoundError as exc:
            raise ValidationError(
                "hedera-sdk-py is required for on-chain HCS-27 operations",
                ErrorContext(details={"dependency": "hedera-sdk-py"}),
            ) from exc
        self._hedera = hedera
        private_key: Any | None = None
        account_id: Any | None = None
        if operator_id and operator_key:
            try:
                account_id = hedera.AccountId.fromString(operator_id)
                private_key = hedera.PrivateKey.fromString(operator_key)
            except Exception as exc:
                raise ValidationError(
                    "invalid operator credentials",
                    ErrorContext(details={"reason": str(exc)}),
                ) from exc
        client = hedera_client or (
            hedera.Client.forMainnet() if self._network == "mainnet" else hedera.Client.forTestnet()
        )
        if hedera_client is None:
            if account_id is None or private_key is None:
                raise ValidationError("operator_id and operator_key are required", ErrorContext())
            cast(Any, client).setOperator(account_id, private_key)
        self._hedera_client = client
        self._operator_key = private_key

    def _resolve_public_key(self, raw_key: object | None, use_operator: bool) -> object | None:
        if self._hedera is None:
            return None
        if use_operator or raw_key is True:
            if self._operator_key is None:
                raise ValidationError(
                    "operator public key is unavailable",
                    ErrorContext(details={"use_operator": True}),
                )
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
                except Exception as exc:
                    raise ValidationError(
                        "failed to parse admin/submit key",
                        ErrorContext(details={"reason": str(exc)}),
                    ) from exc
        raise ValidationError(
            "admin/submit key must be a string or boolean",
            ErrorContext(details={"type": type(raw_key).__name__}),
        )

    def buildTopicMemo(self, *args: object, **kwargs: object) -> str:
        options = self._parse_single_options(args, kwargs, "buildTopicMemo")
        ttl_raw = options.get("ttl", options.get("ttlSeconds", 86400))
        ttl = int(ttl_raw) if isinstance(ttl_raw, int | float | str) else 86400
        if ttl <= 0:
            ttl = 86400
        return f"hcs-27:0:{ttl}:0"

    def parseTopicMemo(self, *args: object, **kwargs: object) -> JsonValue:
        if len(args) > 1:
            raise ValidationError(
                "parseTopicMemo expects at most one positional argument",
                ErrorContext(),
            )
        raw_memo = args[0] if args else kwargs.get("memo", kwargs.get("topicMemo"))
        if not isinstance(raw_memo, str):
            return None
        parts = raw_memo.strip().split(":")
        if len(parts) != 4 or parts[0] != "hcs-27":
            return None
        try:
            parsed = Hcs27TopicMemo(
                indexedFlag=int(parts[1]),
                ttlSeconds=int(parts[2]),
                topicType=int(parts[3]),
            )
        except (ValueError, PydanticValidationError):
            return None
        return cast(JsonValue, parsed.model_dump(by_alias=True))

    def buildTransactionMemo(self, *args: object, **kwargs: object) -> str:
        _ = (args, kwargs)
        return "hcs-27:op:0:0"

    def validateCheckpointMessage(self, *args: object, **kwargs: object) -> JsonValue:
        message_payload = self._extract_message_payload(args, kwargs, "validateCheckpointMessage")
        resolver = self._extract_resolver(args, kwargs)
        message = cast(
            Hcs27CheckpointMessage,
            _parse_model(
                Hcs27CheckpointMessage,
                message_payload,
                message="invalid HCS-27 checkpoint message",
            ),
        )
        metadata_bytes: bytes | None = None
        if message.p != "hcs-27":
            raise ValidationError("p must be hcs-27", ErrorContext())
        if message.op != "register":
            raise ValidationError("op must be register", ErrorContext())
        if message.m is not None and len(message.m) > _MAX_MESSAGE_MEMO_CHARS:
            raise ValidationError(
                "message memo must be at most 299 characters",
                ErrorContext(),
            )
        if isinstance(message.metadata, str):
            reference = _clean(message.metadata)
            if not reference.startswith("hcs://1/"):
                raise ValidationError("metadata reference must be an hcs://1 URI", ErrorContext())
            metadata_bytes = resolver(reference)
            try:
                metadata = Hcs27CheckpointMetadata.model_validate_json(metadata_bytes)
            except PydanticValidationError as exc:
                raise ValidationError(
                    "resolved metadata is invalid",
                    ErrorContext(details={"errors": exc.errors()}),
                ) from exc
        else:
            metadata = cast(
                Hcs27CheckpointMetadata,
                _parse_model(
                    Hcs27CheckpointMetadata,
                    message.metadata,
                    message="invalid HCS-27 metadata payload",
                ),
            )
        self._validate_metadata(metadata)
        if message.metadata_digest is not None:
            if _clean(message.metadata_digest.alg) != "sha-256":
                raise ValidationError("metadata_digest.alg must be sha-256", ErrorContext())
            if metadata_bytes is None:
                raise ValidationError(
                    "metadata_digest requires metadata reference resolution",
                    ErrorContext(),
                )
            digest = _encode_base64url(hashlib.sha256(metadata_bytes).digest())
            if digest != _clean(message.metadata_digest.b64u):
                raise ValidationError(
                    "metadata digest does not match resolved payload",
                    ErrorContext(),
                )
        return cast(JsonValue, metadata.model_dump(by_alias=True, exclude_none=True))

    def validateCheckpointChain(self, *args: object, **kwargs: object) -> JsonValue:
        payload = self._extract_records_payload(args, kwargs)
        streams: dict[str, tuple[int, str]] = {}
        for item in payload:
            record = cast(
                Hcs27CheckpointRecord,
                _parse_model(
                    Hcs27CheckpointRecord,
                    item,
                    message="invalid HCS-27 checkpoint record",
                ),
            )
            stream_id = (
                f"{record.effective_metadata.stream.registry}"
                f"::{record.effective_metadata.stream.log_id}"
            )
            tree_size = _parse_canonical_uint(
                "metadata.root.treeSize",
                record.effective_metadata.root.tree_size,
            )
            root_hash = record.effective_metadata.root.root_hash_b64u
            previous = streams.get(stream_id)
            if previous is not None:
                if tree_size < previous[0]:
                    raise ValidationError(
                        "tree size decreased for stream",
                        ErrorContext(details={"stream": stream_id}),
                    )
                if record.effective_metadata.prev is None:
                    raise ValidationError(
                        "missing prev linkage for stream",
                        ErrorContext(details={"stream": stream_id}),
                    )
                previous_tree_size = _parse_canonical_uint(
                    "metadata.prev.treeSize",
                    record.effective_metadata.prev.tree_size,
                )
                if previous_tree_size != previous[0]:
                    raise ValidationError(
                        "prev.treeSize mismatch for stream",
                        ErrorContext(details={"stream": stream_id}),
                    )
                if record.effective_metadata.prev.root_hash_b64u != previous[1]:
                    raise ValidationError(
                        "prev.rootHashB64u mismatch for stream",
                        ErrorContext(details={"stream": stream_id}),
                    )
            streams[stream_id] = (tree_size, root_hash)
        return True

    def emptyRoot(self, *args: object, **kwargs: object) -> str:
        _ = (args, kwargs)
        return hashlib.sha256(b"").hexdigest()

    def hashLeaf(self, *args: object, **kwargs: object) -> str:
        entry = self._extract_value(args, kwargs, ("canonicalEntry", "canonical_entry", "entry"))
        canonical = entry if isinstance(entry, bytes | bytearray) else _canonicalize_json(entry)
        return _hash_leaf_bytes(bytes(canonical)).hex()

    def hashNode(self, *args: object, **kwargs: object) -> str:
        payload = self._parse_single_options(args, kwargs, "hashNode")
        left = _coerce_hash_bytes(payload.get("left"), "left")
        right = _coerce_hash_bytes(payload.get("right"), "right")
        return _hash_node_bytes(left, right).hex()

    def merkleRootFromCanonicalEntries(self, *args: object, **kwargs: object) -> str:
        entries = self._extract_entries(args, kwargs)
        canonical_entries = [
            bytes(entry) if isinstance(entry, bytes | bytearray) else str(entry).encode("utf-8")
            for entry in entries
        ]
        return self._merkle_root_from_canonical_entries(canonical_entries).hex()

    def merkleRootFromEntries(self, *args: object, **kwargs: object) -> str:
        entries = self._extract_entries(args, kwargs)
        canonical_entries = [_canonicalize_json(entry) for entry in entries]
        return self._merkle_root_from_canonical_entries(canonical_entries).hex()

    def leafHashHexFromEntry(self, *args: object, **kwargs: object) -> str:
        entry = self._extract_value(args, kwargs, ("entry",))
        return _hash_leaf_bytes(_canonicalize_json(entry)).hex()

    def verifyInclusionProof(self, *args: object, **kwargs: object) -> JsonValue:
        proof_payload = self._extract_proof_payload(args, kwargs, "proof")
        if proof_payload is not None:
            proof = cast(
                Hcs27InclusionProof,
                _parse_model(
                    Hcs27InclusionProof,
                    proof_payload,
                    message="invalid HCS-27 inclusion proof",
                ),
            )
            leaf_index = _parse_canonical_uint("leafIndex", proof.leaf_index)
            tree_size = _parse_canonical_uint("treeSize", proof.tree_size)
            leaf_hash_hex = proof.leaf_hash
            path = proof.path
            expected_root = proof.root_hash
            if proof.tree_version != 1:
                raise ValidationError("treeVersion must be 1", ErrorContext())
        else:
            payload = self._parse_single_options(args, kwargs, "verifyInclusionProof")
            leaf_index = _coerce_int(payload.get("leafIndex", payload.get("leaf_index", 0)))
            tree_size = _coerce_int(payload.get("treeSize", payload.get("tree_size", 0)))
            leaf_hash_hex = str(payload.get("leafHash", payload.get("leaf_hash", "")))
            path = [str(item) for item in cast(list[object], payload.get("path", []))]
            expected_root = str(
                payload.get(
                    "rootHash",
                    payload.get("expectedRootB64", payload.get("root_hash", "")),
                )
            )
        return self._verify_inclusion_proof(
            leaf_index=leaf_index,
            tree_size=tree_size,
            leaf_hash_hex=leaf_hash_hex,
            path=path,
            expected_root_b64=expected_root,
        )

    def verifyConsistencyProof(self, *args: object, **kwargs: object) -> JsonValue:
        proof_payload = self._extract_proof_payload(args, kwargs, "proof")
        if proof_payload is not None:
            proof = cast(
                Hcs27ConsistencyProof,
                _parse_model(
                    Hcs27ConsistencyProof,
                    proof_payload,
                    message="invalid HCS-27 consistency proof",
                ),
            )
            old_tree_size = _parse_canonical_uint("oldTreeSize", proof.old_tree_size)
            new_tree_size = _parse_canonical_uint("newTreeSize", proof.new_tree_size)
            old_root = proof.old_root_hash
            new_root = proof.new_root_hash
            path = proof.consistency_path
            if proof.tree_version != 1:
                raise ValidationError("treeVersion must be 1", ErrorContext())
        else:
            payload = self._parse_single_options(args, kwargs, "verifyConsistencyProof")
            old_tree_size = _coerce_int(payload.get("oldTreeSize", payload.get("old_tree_size", 0)))
            new_tree_size = _coerce_int(payload.get("newTreeSize", payload.get("new_tree_size", 0)))
            old_root = str(payload.get("oldRootHash", payload.get("old_root_hash", "")))
            new_root = str(payload.get("newRootHash", payload.get("new_root_hash", "")))
            path = [str(item) for item in cast(list[object], payload.get("consistencyPath", []))]
        return self._verify_consistency_proof(
            old_tree_size=old_tree_size,
            new_tree_size=new_tree_size,
            old_root_b64=old_root,
            new_root_b64=new_root,
            consistency_path=path,
        )

    def createCheckpointTopic(self, *args: object, **kwargs: object) -> JsonValue:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(_ONCHAIN_CREDS_ERROR, ErrorContext())
        options = cast(
            Hcs27CreateCheckpointTopicOptions,
            _parse_model(
                Hcs27CreateCheckpointTopicOptions,
                self._parse_single_options(args, kwargs, "createCheckpointTopic"),
                message="invalid HCS-27 create checkpoint topic options",
            ),
        )
        tx = self._hedera.TopicCreateTransaction().setTopicMemo(
            self.buildTopicMemo({"ttl": options.ttl})
        )
        admin_key = self._resolve_public_key(options.admin_key, options.use_operator_as_admin)
        submit_key = self._resolve_public_key(options.submit_key, options.use_operator_as_submit)
        if admin_key is not None:
            tx.setAdminKey(admin_key)
        if submit_key is not None:
            tx.setSubmitKey(submit_key)
        if options.transaction_memo:
            tx.setTransactionMemo(options.transaction_memo)
        try:
            response = tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to create HCS-27 checkpoint topic",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc
        result = Hcs27CreateCheckpointTopicResult(
            topicId=_to_string(getattr(receipt, "topicId", None)),
            transactionId=_to_string(getattr(response, "transactionId", None)),
        )
        if not result.topic_id:
            raise ParseError("failed to parse HCS-27 topic creation receipt", ErrorContext())
        return cast(JsonValue, result.model_dump(by_alias=True))

    def publishCheckpoint(self, *args: object, **kwargs: object) -> JsonValue:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(_ONCHAIN_CREDS_ERROR, ErrorContext())
        topic_id, metadata_payload, message_memo, transaction_memo = self._parse_publish_inputs(
            args,
            kwargs,
        )
        metadata = cast(
            Hcs27CheckpointMetadata,
            _parse_model(
                Hcs27CheckpointMetadata,
                metadata_payload,
                message="invalid HCS-27 checkpoint metadata",
            ),
        )
        self._validate_metadata(metadata)
        message_payload, inline_resolved_metadata = self._prepare_checkpoint_payload(
            metadata,
            message_memo=message_memo,
        )
        validation_kwargs: dict[str, object] = {"message": message_payload}
        if inline_resolved_metadata is not None:
            reference = cast(str, message_payload["metadata"])
            validation_kwargs["resolver"] = lambda hcs1_reference: (
                inline_resolved_metadata
                if hcs1_reference == reference
                else self.resolveHCS1Reference(hcs1_reference)
            )
        self.validateCheckpointMessage(**validation_kwargs)
        try:
            topic = self._hedera.TopicId.fromString(topic_id)
            tx = self._hedera.TopicMessageSubmitTransaction().setTopicId(topic)
            tx.setMessage(_encode_json_bytes(message_payload))
            tx.setTransactionMemo(transaction_memo or self.buildTransactionMemo())
            response = tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to publish HCS-27 checkpoint",
                ErrorContext(details={"reason": str(exc), "topic_id": topic_id}),
            ) from exc
        result = Hcs27PublishCheckpointResult(
            transactionId=_to_string(getattr(response, "transactionId", None)),
            sequenceNumber=int(_to_string(getattr(receipt, "topicSequenceNumber", 0)) or 0),
        )
        return cast(JsonValue, result.model_dump(by_alias=True))

    def getCheckpoints(self, *args: object, **kwargs: object) -> JsonValue:
        if len(args) > 2:
            raise ValidationError(
                "getCheckpoints expects at most two positional arguments",
                ErrorContext(),
            )
        topic_id = _clean(args[0] if args else kwargs.get("topicId", kwargs.get("topic_id")))
        if not topic_id:
            raise ValidationError("topicId is required", ErrorContext())
        resolver = self._extract_resolver(args, kwargs)
        try:
            items = self._fetch_topic_messages(topic_id)
        except Exception as exc:
            raise TransportError(
                "failed to fetch HCS-27 checkpoints from the mirror node",
                ErrorContext(details={"reason": str(exc), "topic_id": topic_id}),
            ) from exc
        records: list[JsonObject] = []
        for item in items:
            try:
                payload = base64.b64decode(item.message).decode("utf-8")
                raw_message = json.loads(payload)
                metadata_payload = cast(
                    dict[str, object],
                    self.validateCheckpointMessage(message=raw_message, resolver=resolver),
                )
            except Exception:
                continue
            effective_metadata = Hcs27CheckpointMetadata.model_validate(metadata_payload)
            record = Hcs27CheckpointRecord(
                topicId=topic_id,
                sequence=int(item.sequence_number or 0),
                consensusTimestamp=item.consensus_timestamp,
                payer=self._coerce_extra_string(item, ("payer_account_id", "payer")),
                message=raw_message,
                effectiveMetadata=effective_metadata,
            )
            records.append(cast(JsonObject, record.model_dump(by_alias=True, exclude_none=True)))
        return cast(JsonValue, records)

    def resolveHCS1Reference(self, *args: object, **kwargs: object) -> JsonValue:
        if len(args) > 1:
            raise ValidationError(
                "resolveHCS1Reference expects at most one positional argument",
                ErrorContext(),
            )
        reference = _clean(
            args[0] if args else kwargs.get("hcs1Reference", kwargs.get("reference"))
        )
        match = _HCS1_URI_RE.fullmatch(reference)
        if match is None:
            raise ValidationError(
                "invalid HCS-1 reference",
                ErrorContext(details={"reference": reference}),
            )
        topic_id = match.group(1)
        response = self._mirror_client.get_topic_messages(topic_id, order="asc")
        if not response.messages:
            raise ParseError(
                "no HCS-1 payload found",
                ErrorContext(details={"reference": reference}),
            )
        return cast(
            JsonValue,
            self._decode_hcs1_payload_from_messages(
                reference,
                response.messages[0],
                response.messages,
            ),
        )

    def _validate_metadata(self, metadata: Hcs27CheckpointMetadata) -> None:
        if metadata.type != "ans-checkpoint-v1":
            raise ValidationError("metadata.type must be ans-checkpoint-v1", ErrorContext())
        if not _clean(metadata.stream.registry):
            raise ValidationError("metadata.stream.registry is required", ErrorContext())
        if not _clean(metadata.stream.log_id):
            raise ValidationError("metadata.stream.log_id is required", ErrorContext())
        if metadata.log is None:
            raise ValidationError("metadata.log is required", ErrorContext())
        if _clean(metadata.log.alg) != "sha-256":
            raise ValidationError("metadata.log.alg must be sha-256", ErrorContext())
        if not _clean(metadata.log.leaf):
            raise ValidationError("metadata.log.leaf is required", ErrorContext())
        if _clean(metadata.log.merkle) != "rfc9162":
            raise ValidationError("metadata.log.merkle must be rfc9162", ErrorContext())
        root_tree_size = _parse_canonical_uint("metadata.root.treeSize", metadata.root.tree_size)
        _decode_base64url(metadata.root.root_hash_b64u, "metadata.root.rootHashB64u")
        if metadata.prev is not None:
            previous_tree_size = _parse_canonical_uint(
                "metadata.prev.treeSize",
                metadata.prev.tree_size,
            )
            _decode_base64url(metadata.prev.root_hash_b64u, "metadata.prev.rootHashB64u")
            if previous_tree_size > root_tree_size:
                raise ValidationError(
                    "metadata.prev.treeSize must be <= metadata.root.treeSize",
                    ErrorContext(),
                )
        if metadata.sig is not None:
            if not _clean(metadata.sig.alg):
                raise ValidationError("metadata.sig.alg is required", ErrorContext())
            if not _clean(metadata.sig.kid):
                raise ValidationError("metadata.sig.kid is required", ErrorContext())
            _decode_base64url(metadata.sig.b64u, "metadata.sig.b64u")

    def _prepare_checkpoint_payload(
        self,
        metadata: Hcs27CheckpointMetadata,
        *,
        message_memo: str | None,
    ) -> tuple[JsonObject, bytes | None]:
        message = Hcs27CheckpointMessage(
            metadata=metadata.model_dump(by_alias=True, exclude_none=True),
            m=message_memo,
        )
        payload = cast(JsonObject, message.model_dump(by_alias=True, exclude_none=True))
        encoded = _encode_json_bytes(payload)
        if len(encoded) <= 1024:
            return payload, None
        reference, digest = self._publish_metadata_hcs1(
            _encode_json_bytes(metadata.model_dump(by_alias=True, exclude_none=True))
        )
        overflow_message = Hcs27CheckpointMessage(
            metadata=reference,
            metadata_digest=Hcs27MetadataDigest(alg="sha-256", b64u=digest),
            m=message_memo,
        )
        overflow_payload = cast(
            JsonObject,
            overflow_message.model_dump(by_alias=True, exclude_none=True),
        )
        overflow_encoded = _encode_json_bytes(overflow_payload)
        if len(overflow_encoded) > 1024:
            raise ValidationError(
                "checkpoint overflow pointer message exceeds 1024 bytes",
                ErrorContext(details={"size": len(overflow_encoded)}),
            )
        inline_metadata = _encode_json_bytes(metadata.model_dump(by_alias=True, exclude_none=True))
        return overflow_payload, inline_metadata

    def _fetch_topic_messages(self, topic_id: str) -> list[MirrorTopicMessage]:
        collect_items = getattr(self._mirror_client, "_collect_items", None)
        if callable(collect_items):
            raw_items = collect_items(
                f"/topics/{topic_id}/messages",
                query={"order": "asc"},
                item_key="messages",
            )
            return [MirrorTopicMessage.model_validate(item) for item in raw_items]

        response = self._mirror_client.get_topic_messages(topic_id, order="asc")
        validated = MirrorTopicMessagesResponse.model_validate(response)
        return validated.messages

    def _publish_metadata_hcs1(self, metadata_bytes: bytes) -> tuple[str, str]:
        if not self._operator_id or not self._operator_key_raw:
            raise ValidationError(
                "operator credentials are required for HCS-1 overflow publication",
                ErrorContext(),
            )
        result = inscribe(
            InscriptionInput(
                type="buffer",
                buffer=metadata_bytes,
                fileName=f"hcs27-checkpoint-{time.time_ns()}.json",
                mimeType="application/json",
            ),
            InscribeViaRegistryBrokerOptions(
                ledger_account_id=self._operator_id,
                ledger_private_key=self._operator_key_raw,
                ledger_network=self._network,
                file_standard="hcs-1",
            ),
        )
        topic_id = _clean(getattr(result, "topic_id", None))
        if not topic_id or not getattr(result, "confirmed", False):
            raise ValidationError("failed to inscribe HCS-1 metadata", ErrorContext())
        return f"hcs://1/{topic_id}", _encode_base64url(hashlib.sha256(metadata_bytes).digest())

    def _merkle_root_from_canonical_entries(self, entries: list[bytes]) -> bytes:
        if not entries:
            return hashlib.sha256(b"").digest()
        if len(entries) == 1:
            return _hash_leaf_bytes(entries[0])
        split = _largest_power_of_two_less_than(len(entries))
        left = self._merkle_root_from_canonical_entries(entries[:split])
        right = self._merkle_root_from_canonical_entries(entries[split:])
        return _hash_node_bytes(left, right)

    def _verify_inclusion_proof(
        self,
        *,
        leaf_index: int,
        tree_size: int,
        leaf_hash_hex: str,
        path: list[str],
        expected_root_b64: str,
    ) -> bool:
        if tree_size <= 0:
            raise ValidationError("treeSize must be greater than zero", ErrorContext())
        if leaf_index < 0 or leaf_index >= tree_size:
            raise ValidationError("leafIndex must be less than treeSize", ErrorContext())
        try:
            current = bytes.fromhex(leaf_hash_hex.strip())
        except ValueError as exc:
            raise ValidationError("leafHash must be valid hex", ErrorContext()) from exc
        fn = leaf_index
        sn = tree_size - 1
        for index, node in enumerate(path):
            if sn == 0:
                return False
            sibling = _decode_base64(node, f"path[{index}]")
            if _least_significant_bit(fn) == 1 or fn == sn:
                current = _hash_node_bytes(sibling, current)
                if _least_significant_bit(fn) == 0:
                    while _least_significant_bit(fn) == 0 and fn != 0:
                        fn //= 2
                        sn //= 2
            else:
                current = _hash_node_bytes(current, sibling)
            fn //= 2
            sn //= 2
        return sn == 0 and base64.b64encode(current).decode("utf-8") == expected_root_b64

    def _verify_consistency_proof(
        self,
        *,
        old_tree_size: int,
        new_tree_size: int,
        old_root_b64: str,
        new_root_b64: str,
        consistency_path: list[str],
    ) -> bool:
        if old_tree_size == 0:
            return True
        if old_tree_size == new_tree_size:
            return old_root_b64 == new_root_b64 and len(consistency_path) == 0
        if old_tree_size > new_tree_size or not consistency_path:
            return False
        path = list(consistency_path)
        if _is_exact_power_of_two(old_tree_size):
            path = [old_root_b64] + path
        fn = old_tree_size - 1
        sn = new_tree_size - 1
        while _least_significant_bit(fn) == 1:
            fn //= 2
            sn //= 2
        first_hash = _decode_base64(path[0], "consistencyPath[0]")
        fr = first_hash
        sr = first_hash
        for index, node in enumerate(path[1:], start=1):
            node_hash = _decode_base64(node, f"consistencyPath[{index}]")
            if sn == 0:
                return False
            if _least_significant_bit(fn) == 1 or fn == sn:
                fr = _hash_node_bytes(node_hash, fr)
                sr = _hash_node_bytes(node_hash, sr)
                if _least_significant_bit(fn) == 0:
                    while _least_significant_bit(fn) == 0 and fn != 0:
                        fn //= 2
                        sn //= 2
            else:
                sr = _hash_node_bytes(sr, node_hash)
            fn //= 2
            sn //= 2
        return (
            sn == 0
            and base64.b64encode(fr).decode("utf-8") == old_root_b64
            and base64.b64encode(sr).decode("utf-8") == new_root_b64
        )

    def _decode_hcs1_payload_from_messages(
        self,
        reference: str,
        message: MirrorTopicMessage,
        topic_messages: list[MirrorTopicMessage],
    ) -> bytes:
        payload = self._decode_message_data(message)
        chunk_info = self._chunk_info(message)
        if chunk_info is None or _coerce_int(chunk_info.get("total", 0)) <= 1:
            return self._normalize_hcs1_payload(payload)
        chunk_total = _coerce_int(chunk_info.get("total", 0))
        chunk_transaction_id = self._extract_chunk_transaction_id(
            chunk_info.get("initial_transaction_id")
        )
        if not chunk_transaction_id:
            raise ParseError(
                "chunked HCS-1 payload is missing initial transaction ID",
                ErrorContext(details={"reference": reference}),
            )
        chunks: dict[int, bytes] = {}
        for topic_message in topic_messages:
            topic_chunk_info = self._chunk_info(topic_message)
            if topic_chunk_info is None:
                continue
            if _coerce_int(topic_chunk_info.get("total", 0)) != chunk_total:
                continue
            if (
                self._extract_chunk_transaction_id(topic_chunk_info.get("initial_transaction_id"))
                != chunk_transaction_id
            ):
                continue
            chunk_number = _coerce_int(topic_chunk_info.get("number", 0))
            if chunk_number <= 0:
                continue
            chunks[chunk_number] = self._decode_message_data(topic_message)
        if len(chunks) != chunk_total:
            raise ParseError(
                "chunked HCS-1 payload is incomplete",
                ErrorContext(
                    details={
                        "reference": reference,
                        "expected": chunk_total,
                        "found": len(chunks),
                    }
                ),
            )
        combined = bytearray()
        for expected in range(1, chunk_total + 1):
            if expected not in chunks:
                raise ParseError(
                    "chunked HCS-1 payload is missing a chunk",
                    ErrorContext(details={"reference": reference, "chunk": expected}),
                )
            combined.extend(chunks[expected])
        return self._normalize_hcs1_payload(bytes(combined))

    def _decode_message_data(self, message: MirrorTopicMessage) -> bytes:
        try:
            return base64.b64decode(message.message)
        except Exception as exc:
            raise ParseError(
                "failed to decode mirror topic message",
                ErrorContext(
                    details={
                        "sequence_number": message.sequence_number,
                        "reason": str(exc),
                    }
                ),
            ) from exc

    def _chunk_info(self, message: MirrorTopicMessage) -> dict[str, object] | None:
        extras = message.model_extra or {}
        chunk_info = extras.get("chunk_info")
        if isinstance(chunk_info, dict):
            return {str(key): cast(object, value) for key, value in chunk_info.items()}
        return None

    def _normalize_hcs1_payload(self, payload: bytes) -> bytes:
        trimmed = payload.strip()
        if not trimmed.startswith(b"{") or b'"c"' not in trimmed:
            return payload
        try:
            wrapped = json.loads(trimmed.decode("utf-8"))
        except Exception:
            return payload
        content = wrapped.get("c")
        if not isinstance(content, str) or not content.strip().startswith("data:"):
            return payload
        decoded = self._decode_data_url_payload(content)
        try:
            decompressed = cast(bytes, _brotli.decompress(decoded))
        except Exception:
            return decoded
        return decompressed or decoded

    def _decode_data_url_payload(self, value: str) -> bytes:
        header, sep, data = value.partition(",")
        if sep != ",":
            raise ParseError("invalid wrapped HCS-1 data URL", ErrorContext())
        if ";base64" in header.lower():
            try:
                return base64.b64decode(data)
            except Exception as exc:
                raise ParseError(
                    "failed to decode wrapped HCS-1 base64 payload",
                    ErrorContext(details={"reason": str(exc)}),
                ) from exc
        return unquote_to_bytes(data)

    def _extract_chunk_transaction_id(self, value: object) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, Mapping):
            account_id = _clean(value.get("account_id"))
            valid_start = _clean(
                value.get("transaction_valid_start", value.get("valid_start_timestamp"))
            )
            if account_id and valid_start:
                return f"{account_id}@{valid_start}"
        return ""

    def _coerce_extra_string(
        self,
        message: MirrorTopicMessage,
        names: tuple[str, ...],
    ) -> str | None:
        extras = message.model_extra or {}
        for name in names:
            value = extras.get(name)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _parse_single_options(
        self,
        args: tuple[object, ...],
        kwargs: Mapping[str, object],
        method_name: str,
    ) -> dict[str, object]:
        if len(args) > 1:
            raise ValidationError(
                f"{method_name} expects at most one positional argument",
                ErrorContext(),
            )
        payload: dict[str, object] = {}
        if args:
            if isinstance(args[0], str | int | float | bool | bytes | bytearray):
                payload["value"] = args[0]
            else:
                payload.update(_coerce_mapping(args[0], "options"))
        payload.update(dict(kwargs))
        return payload

    def _extract_message_payload(
        self,
        args: tuple[object, ...],
        kwargs: Mapping[str, object],
        method_name: str,
    ) -> object:
        if len(args) > 1:
            raise ValidationError(
                f"{method_name} expects at most one positional argument",
                ErrorContext(),
            )
        if args:
            if isinstance(args[0], Mapping) and "message" in args[0]:
                return cast(Mapping[str, object], args[0])["message"]
            return args[0]
        if "message" in kwargs:
            return kwargs["message"]
        return dict(kwargs)

    def _extract_resolver(
        self,
        args: tuple[object, ...],
        kwargs: Mapping[str, object],
    ) -> Callable[[str], bytes]:
        resolver: object | None = kwargs.get("resolver", kwargs.get("hcs1Resolver"))
        if resolver is None and args and isinstance(args[0], Mapping):
            resolver = cast(Mapping[str, object], args[0]).get(
                "resolver",
                cast(Mapping[str, object], args[0]).get("hcs1Resolver"),
            )
        if resolver is None:
            return lambda reference: cast(bytes, self.resolveHCS1Reference(reference))
        if not callable(resolver):
            raise ValidationError("resolver must be callable", ErrorContext())
        return cast(Callable[[str], bytes], resolver)

    def _extract_records_payload(
        self,
        args: tuple[object, ...],
        kwargs: Mapping[str, object],
    ) -> list[object]:
        if len(args) > 1:
            raise ValidationError(
                "validateCheckpointChain expects at most one positional argument",
                ErrorContext(),
            )
        raw = args[0] if args else kwargs.get("records", kwargs.get("checkpoints"))
        if not isinstance(raw, list):
            raise ValidationError("records must be a list", ErrorContext())
        return cast(list[object], raw)

    def _extract_value(
        self,
        args: tuple[object, ...],
        kwargs: Mapping[str, object],
        names: tuple[str, ...],
    ) -> object:
        if args:
            return args[0]
        for name in names:
            if name in kwargs:
                return kwargs[name]
        raise ValidationError(f"{names[0]} is required", ErrorContext())

    def _extract_entries(
        self,
        args: tuple[object, ...],
        kwargs: Mapping[str, object],
    ) -> list[object]:
        if len(args) > 1:
            raise ValidationError(
                "entries method expects at most one positional argument",
                ErrorContext(),
            )
        raw = args[0] if args else kwargs.get("entries")
        if not isinstance(raw, list):
            raise ValidationError("entries must be a list", ErrorContext())
        return cast(list[object], raw)

    def _extract_proof_payload(
        self,
        args: tuple[object, ...],
        kwargs: Mapping[str, object],
        key: str,
    ) -> object | None:
        if len(args) == 1 and not isinstance(args[0], int):
            if isinstance(args[0], Mapping) and key in args[0]:
                return cast(Mapping[str, object], args[0])[key]
            if isinstance(args[0], BaseModel | Mapping):
                return args[0]
        return kwargs.get(key)

    def _parse_publish_inputs(
        self,
        args: tuple[object, ...],
        kwargs: Mapping[str, object],
    ) -> tuple[str, object, str | None, str | None]:
        if len(args) > 4:
            raise ValidationError(
                "publishCheckpoint expects at most four positional arguments",
                ErrorContext(),
            )
        topic_id = _clean(args[0] if args else kwargs.get("topicId", kwargs.get("topic_id")))
        if not topic_id:
            raise ValidationError("topicId is required", ErrorContext())
        metadata_payload: object | None = None
        if len(args) >= 2:
            metadata_payload = args[1]
        elif "metadata" in kwargs:
            metadata_payload = kwargs["metadata"]
        if metadata_payload is None:
            raise ValidationError("metadata is required", ErrorContext())
        message_memo = (
            cast(str | None, args[2]) if len(args) >= 3 and isinstance(args[2], str) else None
        )
        transaction_memo = (
            cast(str | None, args[3]) if len(args) >= 4 and isinstance(args[3], str) else None
        )
        if isinstance(kwargs.get("messageMemo"), str):
            message_memo = cast(str, kwargs["messageMemo"])
        if isinstance(kwargs.get("message_memo"), str):
            message_memo = cast(str, kwargs["message_memo"])
        if isinstance(kwargs.get("transactionMemo"), str):
            transaction_memo = cast(str, kwargs["transactionMemo"])
        if isinstance(kwargs.get("transaction_memo"), str):
            transaction_memo = cast(str, kwargs["transaction_memo"])
        return topic_id, metadata_payload, message_memo, transaction_memo

    build_topic_memo = buildTopicMemo
    parse_topic_memo = parseTopicMemo
    build_transaction_memo = buildTransactionMemo
    validate_checkpoint_message = validateCheckpointMessage
    validate_checkpoint_chain = validateCheckpointChain
    empty_root = emptyRoot
    hash_leaf = hashLeaf
    hash_node = hashNode
    merkle_root_from_canonical_entries = merkleRootFromCanonicalEntries
    merkle_root_from_entries = merkleRootFromEntries
    leaf_hash_hex_from_entry = leafHashHexFromEntry
    verify_inclusion_proof = verifyInclusionProof
    verify_consistency_proof = verifyConsistencyProof
    create_checkpoint_topic = createCheckpointTopic
    publish_checkpoint = publishCheckpoint
    get_checkpoints = getCheckpoints
    resolve_h_c_s1_reference = resolveHCS1Reference


class AsyncHcs27Client(AsyncHcsModuleClient):
    """Asynchronous HCS-27 client."""

    def __init__(
        self,
        transport: AsyncHttpTransport | None = None,
        *,
        operator_id: str | None = None,
        operator_key: str | None = None,
        hedera_client: object | None = None,
        network: str = "testnet",
        mirror_base_url: str | None = None,
        mirror_client: MirrorNodeClient | None = None,
    ) -> None:
        config = SdkConfig.from_env()
        resolved_transport = transport or AsyncHttpTransport(
            base_url=config.network.registry_broker_base_url or _DEFAULT_REGISTRY_BROKER_BASE_URL,
        )
        super().__init__("hcs27", resolved_transport)
        self._sync_client = Hcs27Client(
            transport=SyncHttpTransport(
                base_url=resolved_transport.base_url,
                headers=dict(resolved_transport.headers or {}),
            ),
            operator_id=operator_id,
            operator_key=operator_key,
            hedera_client=hedera_client,
            network=network,
            mirror_base_url=mirror_base_url,
            mirror_client=mirror_client,
        )

    async def buildTopicMemo(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.buildTopicMemo, *args, **kwargs)

    async def parseTopicMemo(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.parseTopicMemo, *args, **kwargs)

    async def buildTransactionMemo(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.buildTransactionMemo, *args, **kwargs)

    async def validateCheckpointMessage(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.validateCheckpointMessage, *args, **kwargs)

    async def validateCheckpointChain(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.validateCheckpointChain, *args, **kwargs)

    async def emptyRoot(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.emptyRoot, *args, **kwargs)

    async def hashLeaf(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.hashLeaf, *args, **kwargs)

    async def hashNode(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.hashNode, *args, **kwargs)

    async def merkleRootFromCanonicalEntries(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(
            self._sync_client.merkleRootFromCanonicalEntries,
            *args,
            **kwargs,
        )

    async def merkleRootFromEntries(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.merkleRootFromEntries, *args, **kwargs)

    async def leafHashHexFromEntry(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.leafHashHexFromEntry, *args, **kwargs)

    async def verifyInclusionProof(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.verifyInclusionProof, *args, **kwargs)

    async def verifyConsistencyProof(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.verifyConsistencyProof, *args, **kwargs)

    async def createCheckpointTopic(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.createCheckpointTopic, *args, **kwargs)

    async def publishCheckpoint(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.publishCheckpoint, *args, **kwargs)

    async def getCheckpoints(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.getCheckpoints, *args, **kwargs)

    async def resolveHCS1Reference(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.resolveHCS1Reference, *args, **kwargs)

    build_topic_memo = buildTopicMemo
    parse_topic_memo = parseTopicMemo
    build_transaction_memo = buildTransactionMemo
    validate_checkpoint_message = validateCheckpointMessage
    validate_checkpoint_chain = validateCheckpointChain
    empty_root = emptyRoot
    hash_leaf = hashLeaf
    hash_node = hashNode
    merkle_root_from_canonical_entries = merkleRootFromCanonicalEntries
    merkle_root_from_entries = merkleRootFromEntries
    leaf_hash_hex_from_entry = leafHashHexFromEntry
    verify_inclusion_proof = verifyInclusionProof
    verify_consistency_proof = verifyConsistencyProof
    create_checkpoint_topic = createCheckpointTopic
    publish_checkpoint = publishCheckpoint
    get_checkpoints = getCheckpoints
    resolve_h_c_s1_reference = resolveHCS1Reference
