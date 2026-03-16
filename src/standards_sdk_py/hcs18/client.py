"""HCS-18 client with direct on-chain execution parity."""

# ruff: noqa: N802

from __future__ import annotations

import asyncio
import importlib
import json
from collections.abc import Mapping
from typing import Any, cast

from pydantic import BaseModel

from standards_sdk_py.exceptions import ErrorContext, ParseError, TransportError, ValidationError
from standards_sdk_py.hcs18.models import (
    Hcs18CreateDiscoveryTopicOptions,
    Hcs18CreateDiscoveryTopicResult,
    Hcs18DiscoveryMessage,
    Hcs18DiscoveryOperation,
    Hcs18OperationResult,
)
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.hcs_module import AsyncHcsModuleClient, HcsModuleClient
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.types import JsonValue

_DEFAULT_REGISTRY_BROKER_BASE_URL = "https://registry.hashgraphonline.com"
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


class Hcs18Client(HcsModuleClient):
    """Synchronous HCS-18 client."""

    def __init__(
        self,
        transport: SyncHttpTransport | None = None,
        *,
        operator_id: str,
        operator_key: str,
        hedera_client: object | None = None,
        network: str = "testnet",
        key_type: str | None = None,
    ) -> None:
        config = SdkConfig.from_env()
        resolved_transport = transport or SyncHttpTransport(
            base_url=config.network.registry_broker_base_url or _DEFAULT_REGISTRY_BROKER_BASE_URL,
        )
        super().__init__("hcs18", resolved_transport)

        self._network = _normalize_network(network)
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
                "hedera-sdk-py is required for on-chain HCS-18 operations",
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
                    private_key = self._hedera.PrivateKey.fromString(cleaned)
                    return cast(object, private_key.getPublicKey())
                except Exception:
                    return None
        return None

    def createDiscoveryTopic(self, *args: object, **kwargs: object) -> JsonValue:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(_ONCHAIN_CREDS_ERROR, ErrorContext())
        options = Hcs18CreateDiscoveryTopicOptions.model_validate(
            self._parse_single_options(args, kwargs, "createDiscoveryTopic")
        )
        ttl = options.ttl_seconds if options.ttl_seconds > 0 else 86400
        memo = _clean(options.memo_override) or f"hcs-18:0:{ttl}"
        tx = self._hedera.TopicCreateTransaction().setTopicMemo(memo)

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
                "failed to execute discovery topic create transaction",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc
        topic_id = _to_string(getattr(receipt, "topicId", None))
        if not topic_id:
            raise ParseError("failed to create discovery topic", ErrorContext())

        result = Hcs18CreateDiscoveryTopicResult(
            topicId=topic_id,
            transactionId=_to_string(getattr(response, "transactionId", None)) or None,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def _submit_discovery_message(
        self,
        topic_id: str,
        operation: Hcs18DiscoveryOperation,
        data: dict[str, object],
        memo: str | None = None,
    ) -> JsonValue:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(_ONCHAIN_CREDS_ERROR, ErrorContext())
        message = Hcs18DiscoveryMessage(op=operation, data=data)
        tx = self._hedera.TopicMessageSubmitTransaction().setTopicId(
            self._hedera.TopicId.fromString(_clean(topic_id))
        )
        encoded_payload = json.dumps(message.model_dump(by_alias=True, exclude_none=True)).encode(
            "utf-8"
        )
        tx.setMessage(encoded_payload)
        if _clean(memo):
            tx.setTransactionMemo(_clean(memo))
        try:
            response = tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to execute discovery message transaction",
                ErrorContext(details={"reason": str(exc), "topic_id": topic_id}),
            ) from exc
        result = Hcs18OperationResult(
            success=True,
            transactionId=_to_string(getattr(response, "transactionId", None)) or None,
            sequenceNumber=int(_to_string(getattr(receipt, "topicSequenceNumber", 0)) or 0),
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def announce(self, *args: object, **kwargs: object) -> JsonValue:
        topic_id, data, memo = self._parse_operation_inputs(args, kwargs, method_name="announce")
        return self._submit_discovery_message(
            topic_id, Hcs18DiscoveryOperation.ANNOUNCE, data, memo
        )

    def propose(self, *args: object, **kwargs: object) -> JsonValue:
        topic_id, data, memo = self._parse_operation_inputs(args, kwargs, method_name="propose")
        return self._submit_discovery_message(topic_id, Hcs18DiscoveryOperation.PROPOSE, data, memo)

    def respond(self, *args: object, **kwargs: object) -> JsonValue:
        topic_id, data, memo = self._parse_operation_inputs(args, kwargs, method_name="respond")
        return self._submit_discovery_message(topic_id, Hcs18DiscoveryOperation.RESPOND, data, memo)

    def complete(self, *args: object, **kwargs: object) -> JsonValue:
        topic_id, data, memo = self._parse_operation_inputs(args, kwargs, method_name="complete")
        return self._submit_discovery_message(
            topic_id, Hcs18DiscoveryOperation.COMPLETE, data, memo
        )

    def withdraw(self, *args: object, **kwargs: object) -> JsonValue:
        topic_id, data, memo = self._parse_operation_inputs(args, kwargs, method_name="withdraw")
        return self._submit_discovery_message(
            topic_id, Hcs18DiscoveryOperation.WITHDRAW, data, memo
        )

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

    def _parse_operation_inputs(
        self, args: tuple[object, ...], kwargs: Mapping[str, object], *, method_name: str
    ) -> tuple[str, dict[str, object], str | None]:
        if len(args) > 3:
            raise ValidationError(
                f"{method_name} expects at most three positional arguments",
                ErrorContext(),
            )
        if not args and "discoveryTopicId" not in kwargs and "topicId" not in kwargs:
            raise ValidationError("discoveryTopicId is required", ErrorContext())
        if args and not isinstance(args[0], str):
            raise ValidationError("discoveryTopicId must be a string", ErrorContext())

        topic_id = _clean(
            args[0]
            if args
            else kwargs.get("discoveryTopicId", kwargs.get("topicId", kwargs.get("topic_id")))
        )
        if not topic_id:
            raise ValidationError("discoveryTopicId is required", ErrorContext())

        data: dict[str, object] = {}
        memo: str | None = None
        if len(args) >= 2:
            data.update(_coerce_mapping(args[1], "data"))
        if len(args) >= 3 and isinstance(args[2], str):
            memo = args[2]
        if kwargs.get("data") is not None:
            data.update(_coerce_mapping(kwargs["data"], "data"))
        if isinstance(kwargs.get("memo"), str):
            memo = cast(str, kwargs["memo"])
        for key, value in kwargs.items():
            if key in {"discoveryTopicId", "topicId", "topic_id", "data", "memo"}:
                continue
            if not data:
                data[key] = value
        return topic_id, data, memo

    announce_flow = announce
    create_discovery_topic = createDiscoveryTopic


class AsyncHcs18Client(AsyncHcsModuleClient):
    """Asynchronous HCS-18 client."""

    def __init__(
        self,
        transport: AsyncHttpTransport | None = None,
        *,
        operator_id: str,
        operator_key: str,
        hedera_client: object | None = None,
        network: str = "testnet",
        key_type: str | None = None,
    ) -> None:
        config = SdkConfig.from_env()
        resolved_transport = transport or AsyncHttpTransport(
            base_url=config.network.registry_broker_base_url or _DEFAULT_REGISTRY_BROKER_BASE_URL,
        )
        super().__init__("hcs18", resolved_transport)
        self._sync_client = Hcs18Client(
            transport=SyncHttpTransport(
                base_url=resolved_transport.base_url,
                headers=dict(resolved_transport.headers or {}),
            ),
            operator_id=operator_id,
            operator_key=operator_key,
            hedera_client=hedera_client,
            network=network,
            key_type=key_type,
        )

    async def createDiscoveryTopic(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.createDiscoveryTopic, *args, **kwargs)

    async def announce(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.announce, *args, **kwargs)

    async def propose(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.propose, *args, **kwargs)

    async def respond(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.respond, *args, **kwargs)

    async def complete(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.complete, *args, **kwargs)

    async def withdraw(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.withdraw, *args, **kwargs)

    create_discovery_topic = createDiscoveryTopic
