"""HCS-17 client with direct on-chain execution parity."""

# ruff: noqa: N802

from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, cast

from pydantic import BaseModel

from standards_sdk_py.exceptions import ErrorContext, ParseError, TransportError, ValidationError
from standards_sdk_py.hcs17.models import (
    Hcs17ComputeAndPublishOptions,
    Hcs17ComputeAndPublishResult,
    Hcs17CreateTopicOptions,
    Hcs17StateHashMessage,
    Hcs17SubmitMessageResult,
)
from standards_sdk_py.mirror import MirrorNodeClient
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.hcs_module import AsyncHcsModuleClient, HcsModuleClient
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.types import JsonValue

_DEFAULT_REGISTRY_BROKER_BASE_URL = "https://registry.hashgraphonline.com"
_DEFAULT_MIRROR_BY_NETWORK = {
    "mainnet": "https://mainnet-public.mirrornode.hedera.com/api/v1",
    "testnet": "https://testnet.mirrornode.hedera.com/api/v1",
}
_ONCHAIN_CREDS_ERROR = "on-chain operator credentials are not configured"


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


def _coerce_mapping(value: object, field_name: str) -> dict[str, object]:
    if isinstance(value, BaseModel):
        return cast(dict[str, object], value.model_dump(by_alias=True, exclude_none=True))
    if isinstance(value, Mapping):
        return {str(k): v for k, v in value.items()}
    raise ValidationError(
        f"{field_name} must be a mapping/object",
        ErrorContext(details={"field": field_name, "type": type(value).__name__}),
    )


class Hcs17Client(HcsModuleClient):
    """Synchronous HCS-17 client."""

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
        super().__init__("hcs17", resolved_transport)

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
        self._hedera_client: Any | None = None
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
                "hedera-sdk-py is required for on-chain HCS-17 operations",
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
                    private_key = self._hedera.PrivateKey.fromString(cleaned)
                    return cast(object, private_key.getPublicKey())
                except Exception:
                    return None
        return None

    def _validate_message(self, message: Hcs17StateHashMessage) -> None:
        if message.p != "hcs-17":
            raise ValidationError("p must be hcs-17", ErrorContext())
        if message.op != "state_hash":
            raise ValidationError("op must be state_hash", ErrorContext())
        if not _clean(message.state_hash):
            raise ValidationError("state_hash is required", ErrorContext())
        if not _clean(message.account_id):
            raise ValidationError("account_id is required", ErrorContext())
        if message.topics is None:
            raise ValidationError("topics is required", ErrorContext())
        if message.epoch is not None and message.epoch < 0:
            raise ValidationError("epoch must be non-negative", ErrorContext())

    def createStateTopic(self, *args: object, **kwargs: object) -> JsonValue:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(_ONCHAIN_CREDS_ERROR, ErrorContext())
        options = Hcs17CreateTopicOptions.model_validate(
            self._parse_single_options(args, kwargs, "createStateTopic")
        )
        ttl = options.ttl if options.ttl > 0 else 86400
        tx = self._hedera.TopicCreateTransaction().setTopicMemo(f"hcs-17:0:{ttl}")

        admin_key = self._resolve_public_key(options.admin_key, options.use_operator_as_admin)
        submit_key = self._resolve_public_key(options.submit_key, options.use_operator_as_submit)
        if admin_key is not None:
            tx.setAdminKey(admin_key)
        if submit_key is not None:
            tx.setSubmitKey(submit_key)
        if _clean(options.transaction_memo):
            tx.setTransactionMemo(_clean(options.transaction_memo))

        try:
            response = tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to execute HCS-17 create topic transaction",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc
        topic_id = _to_string(getattr(receipt, "topicId", None))
        if not topic_id:
            raise ParseError("failed to create HCS-17 topic", ErrorContext())
        return topic_id

    def submitMessage(self, *args: object, **kwargs: object) -> JsonValue:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(_ONCHAIN_CREDS_ERROR, ErrorContext())
        topic_id, message_payload, transaction_memo = self._parse_submit_inputs(args, kwargs)
        message = Hcs17StateHashMessage.model_validate(message_payload)
        self._validate_message(message)

        tx = self._hedera.TopicMessageSubmitTransaction().setTopicId(
            self._hedera.TopicId.fromString(topic_id)
        )
        payload = message.model_copy(
            update={"timestamp": message.timestamp or datetime.now(UTC).isoformat()}
        )
        encoded_payload = json.dumps(payload.model_dump(by_alias=True, exclude_none=True)).encode(
            "utf-8"
        )
        tx.setMessage(encoded_payload)
        if _clean(transaction_memo):
            tx.setTransactionMemo(_clean(transaction_memo))

        try:
            response = tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to execute HCS-17 message transaction",
                ErrorContext(details={"reason": str(exc), "topic_id": topic_id}),
            ) from exc

        result = Hcs17SubmitMessageResult(
            success=True,
            transactionId=_to_string(getattr(response, "transactionId", None)) or None,
            sequenceNumber=int(_to_string(getattr(receipt, "topicSequenceNumber", 0)) or 0),
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def computeAndPublish(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs17ComputeAndPublishOptions.model_validate(
            self._parse_single_options(args, kwargs, "computeAndPublish")
        )
        topic_states: list[tuple[str, str]] = []
        for topic_id in options.topics:
            response = self._mirror_client.get_topic_messages(topic_id, limit=1, order="desc")
            running_hash = ""
            if response.messages:
                raw_running_hash = getattr(response.messages[0], "running_hash", "") or ""
                running_hash = str(raw_running_hash)
            topic_states.append((topic_id, running_hash))

        concatenated = "".join(
            f"{topic_id}{running_hash}" for topic_id, running_hash in sorted(topic_states)
        )
        concatenated += options.account_public_key
        state_hash = hashlib.sha384(concatenated.encode("utf-8")).hexdigest()

        message = Hcs17StateHashMessage(
            state_hash=state_hash,
            account_id=options.account_id,
            topics=options.topics,
            timestamp=datetime.now(UTC).isoformat(),
            m=options.memo,
        )
        submitted = cast(
            dict[str, object],
            self.submitMessage(
                options.publish_topic_id,
                message.model_dump(by_alias=True, exclude_none=True),
            ),
        )

        result = Hcs17ComputeAndPublishResult(
            stateHash=state_hash,
            transactionId=cast(str | None, submitted.get("transactionId")),
            sequenceNumber=cast(int | None, submitted.get("sequenceNumber")),
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

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
                f"{method_name} expects at most one positional argument",
                ErrorContext(),
            )
        payload: dict[str, object] = {}
        if args:
            payload.update(_coerce_mapping(args[0], "options"))
        payload.update(kwargs)
        return payload

    def _parse_submit_inputs(
        self, args: tuple[object, ...], kwargs: Mapping[str, object]
    ) -> tuple[str, dict[str, object], str | None]:
        if len(args) > 3:
            raise ValidationError(
                "submitMessage expects at most three positional arguments",
                ErrorContext(),
            )
        if not args and not kwargs.get("topicId") and not kwargs.get("topic_id"):
            raise ValidationError("topicId is required", ErrorContext())
        if args and not isinstance(args[0], str):
            raise ValidationError("topicId must be a string", ErrorContext())

        topic_id = _clean(args[0] if args else kwargs.get("topicId", kwargs.get("topic_id")))
        if not topic_id:
            raise ValidationError("topicId is required", ErrorContext())

        payload: dict[str, object] = {}
        transaction_memo: str | None = None
        if len(args) >= 2:
            payload.update(_coerce_mapping(args[1], "message"))
        if len(args) >= 3 and isinstance(args[2], str):
            transaction_memo = args[2]
        if kwargs.get("message") is not None:
            payload.update(_coerce_mapping(kwargs["message"], "message"))
        if isinstance(kwargs.get("transactionMemo"), str):
            transaction_memo = cast(str, kwargs["transactionMemo"])
        if isinstance(kwargs.get("transaction_memo"), str):
            transaction_memo = cast(str, kwargs["transaction_memo"])
        if not payload:
            for key, value in kwargs.items():
                if key in {"topicId", "topic_id", "message", "transactionMemo", "transaction_memo"}:
                    continue
                payload[key] = value
        return topic_id, payload, transaction_memo

    create_state_topic = createStateTopic
    submit_message = submitMessage
    compute_and_publish = computeAndPublish
    get_key_type = getKeyType


class AsyncHcs17Client(AsyncHcsModuleClient):
    """Asynchronous HCS-17 client."""

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
        super().__init__("hcs17", resolved_transport)
        self._sync_client = Hcs17Client(
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

    async def createStateTopic(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.createStateTopic, *args, **kwargs)

    async def submitMessage(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.submitMessage, *args, **kwargs)

    async def computeAndPublish(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.computeAndPublish, *args, **kwargs)

    async def getKeyType(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.getKeyType, *args, **kwargs)

    create_state_topic = createStateTopic
    submit_message = submitMessage
    compute_and_publish = computeAndPublish
    get_key_type = getKeyType
