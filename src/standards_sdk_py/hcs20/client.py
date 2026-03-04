"""HCS-20 client with direct on-chain execution parity."""

# ruff: noqa: N802

from __future__ import annotations

import asyncio
import importlib
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, cast

from standards_sdk_py.exceptions import ErrorContext, ParseError, TransportError, ValidationError
from standards_sdk_py.hcs2 import Hcs2Client, Hcs2RegistryType
from standards_sdk_py.hcs20.models import (
    Hcs20BurnPointsOptions,
    Hcs20CreateTopicOptions,
    Hcs20DeployPointsOptions,
    Hcs20MintPointsOptions,
    Hcs20PointsInfo,
    Hcs20PointsTransaction,
    Hcs20RegisterTopicOptions,
    Hcs20TransferPointsOptions,
)
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.hcs_module import AsyncHcsModuleClient, HcsModuleClient
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.types import JsonValue

_DEFAULT_REGISTRY_BROKER_BASE_URL = "https://registry.hashgraphonline.com"
_DEFAULT_PUBLIC_TOPIC_ID = "0.0.4350190"
_DEFAULT_REGISTRY_TOPIC_ID = "0.0.4362300"
_ONCHAIN_CREDS_ERROR = "on-chain operator credentials are not configured"
_TOPIC_ID_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_NUMBER_PATTERN = re.compile(r"^\d+$")


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


def _normalize_tick(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValidationError("tick is required", ErrorContext())
    return normalized


def _require_number_string(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not _NUMBER_PATTERN.fullmatch(cleaned):
        raise ValidationError(
            f"{field_name} must be a numeric string",
            ErrorContext(details={"field": field_name, "value": value}),
        )
    return cleaned


def _validate_topic_id(value: str, field_name: str = "topicId") -> str:
    cleaned = value.strip()
    if not _TOPIC_ID_PATTERN.fullmatch(cleaned):
        raise ValidationError(
            f"{field_name} must be a Hedera topic ID (e.g. 0.0.12345)",
            ErrorContext(details={"field": field_name, "value": value}),
        )
    return cleaned


class Hcs20Client(HcsModuleClient):
    """Synchronous HCS-20 client."""

    def __init__(
        self,
        transport: SyncHttpTransport | None = None,
        *,
        operator_id: str,
        operator_key: str,
        network: str = "testnet",
        public_topic_id: str | None = None,
        registry_topic_id: str | None = None,
        key_type: str | None = None,
    ) -> None:
        config = SdkConfig.from_env()
        resolved_transport = transport or SyncHttpTransport(
            base_url=config.network.registry_broker_base_url or _DEFAULT_REGISTRY_BROKER_BASE_URL,
        )
        super().__init__("hcs20", resolved_transport)

        self._network = _normalize_network(network)
        self._hedera: Any | None = None
        self._hedera_client: Any | None = None
        self._operator_id: str | None = None
        self._operator_key: Any | None = None
        self._operator_key_string: str | None = None
        self.public_topic_id = _clean(public_topic_id) or _DEFAULT_PUBLIC_TOPIC_ID
        self.registry_topic_id = _clean(registry_topic_id) or _DEFAULT_REGISTRY_TOPIC_ID

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
                "hedera-sdk-py is required for on-chain HCS-20 operations",
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

    def _submit_message(
        self, topic_id: str, payload: Mapping[str, object], memo: str | None
    ) -> Hcs20PointsTransaction:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(_ONCHAIN_CREDS_ERROR, ErrorContext())
        topic = _validate_topic_id(topic_id)
        tx = self._hedera.TopicMessageSubmitTransaction().setTopicId(
            self._hedera.TopicId.fromString(topic)
        )
        tx.setMessage(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        if _clean(memo):
            tx.setTransactionMemo(_clean(memo))

        try:
            response = tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to submit HCS-20 topic message",
                ErrorContext(details={"reason": str(exc), "topic_id": topic_id}),
            ) from exc

        transaction_id = _to_string(getattr(response, "transactionId", None))
        sequence_number = int(_to_string(getattr(receipt, "topicSequenceNumber", 0)) or 0)
        consensus_timestamp = (
            _to_string(getattr(receipt, "consensusTimestamp", None))
            or datetime.now(UTC).isoformat()
        )

        return Hcs20PointsTransaction.model_validate(
            {
                "id": f"{topic}:{sequence_number}",
                "operation": str(payload.get("op") or ""),
                "tick": str(payload.get("tick") or ""),
                "amount": cast(str | None, payload.get("amt")),
                "from": cast(str | None, payload.get("from")),
                "to": cast(str | None, payload.get("to")),
                "timestamp": consensus_timestamp,
                "sequenceNumber": sequence_number,
                "topicId": topic,
                "transactionId": transaction_id,
                "memo": cast(str | None, payload.get("m")),
            }
        )

    def _options_payload(self, args: tuple[object, ...], kwargs: dict[str, object]) -> object:
        if kwargs:
            return kwargs
        if args:
            return args[0]
        return {}

    def createPublicTopic(self, *args: object, **kwargs: object) -> JsonValue:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(_ONCHAIN_CREDS_ERROR, ErrorContext())
        options = Hcs20CreateTopicOptions.model_validate(self._options_payload(args, dict(kwargs)))
        tx = self._hedera.TopicCreateTransaction().setTopicMemo(
            _clean(options.memo) or "HCS-20 Public Topic"
        )
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
                "failed to create HCS-20 public topic",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc
        topic_id = _to_string(getattr(receipt, "topicId", None))
        if not topic_id:
            raise ParseError("failed to create public topic", ErrorContext())
        self.public_topic_id = topic_id
        return {
            "topicId": topic_id,
            "transactionId": _to_string(getattr(response, "transactionId", None)),
        }

    def createRegistryTopic(self, *args: object, **kwargs: object) -> JsonValue:
        _ = (args, kwargs)
        if not self._operator_id or not self._operator_key_string:
            raise ValidationError(_ONCHAIN_CREDS_ERROR, ErrorContext())
        hcs2_client = Hcs2Client(
            operator_id=self._operator_id,
            operator_key=self._operator_key_string,
            network=self._network,
        )
        created = cast(
            dict[str, object],
            hcs2_client.createRegistry(
                {
                    "registryType": Hcs2RegistryType.INDEXED,
                    "useOperatorAsAdmin": True,
                    "useOperatorAsSubmit": True,
                }
            ),
        )
        topic_id = str(created.get("topicId") or "")
        if not topic_id:
            raise ParseError("failed to create registry topic", ErrorContext())
        self.registry_topic_id = topic_id
        raw_transaction_id = created.get("transactionId")
        transaction_id = str(raw_transaction_id) if raw_transaction_id is not None else None
        return {"topicId": topic_id, "transactionId": transaction_id}

    def deployPoints(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs20DeployPointsOptions.model_validate(self._options_payload(args, dict(kwargs)))
        target_topic_id = _clean(options.topic_id) or self.public_topic_id
        if options.use_private_topic:
            created = cast(
                dict[str, object],
                self.createPublicTopic({"memo": options.topic_memo or f"hcs-20:{options.tick}"}),
            )
            target_topic_id = str(created.get("topicId") or "")
        message = {
            "p": "hcs-20",
            "op": "deploy",
            "name": _clean(options.name),
            "tick": _normalize_tick(options.tick),
            "max": _require_number_string(options.max_supply, "maxSupply"),
        }
        if _clean(options.limit_per_mint):
            message["lim"] = _require_number_string(options.limit_per_mint or "", "limitPerMint")
        if _clean(options.metadata):
            message["metadata"] = _clean(options.metadata)
        if _clean(options.memo):
            message["m"] = _clean(options.memo)

        tx = self._submit_message(target_topic_id, message, _clean(options.memo))
        info = Hcs20PointsInfo(
            name=_clean(options.name),
            tick=_normalize_tick(options.tick),
            maxSupply=_require_number_string(options.max_supply, "maxSupply"),
            limitPerMint=_clean(options.limit_per_mint) or None,
            metadata=_clean(options.metadata) or None,
            topicId=target_topic_id,
            deployerAccountId=self._operator_id or "",
            currentSupply="0",
            deploymentTimestamp=tx.timestamp,
            isPrivate=options.use_private_topic,
        )
        return cast(JsonValue, info.model_dump(by_alias=True, exclude_none=True))

    def mintPoints(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs20MintPointsOptions.model_validate(self._options_payload(args, dict(kwargs)))
        topic_id = _clean(options.topic_id) or self.public_topic_id
        payload = {
            "p": "hcs-20",
            "op": "mint",
            "tick": _normalize_tick(options.tick),
            "amt": _require_number_string(options.amount, "amount"),
            "to": _validate_topic_id(options.to, "to"),
            "m": _clean(options.memo) or None,
        }
        result = self._submit_message(topic_id, payload, _clean(options.memo))
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def transferPoints(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs20TransferPointsOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        topic_id = _clean(options.topic_id) or self.public_topic_id
        payload = {
            "p": "hcs-20",
            "op": "transfer",
            "tick": _normalize_tick(options.tick),
            "amt": _require_number_string(options.amount, "amount"),
            "from": _validate_topic_id(options.from_account, "from"),
            "to": _validate_topic_id(options.to, "to"),
            "m": _clean(options.memo) or None,
        }
        result = self._submit_message(topic_id, payload, _clean(options.memo))
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def burnPoints(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs20BurnPointsOptions.model_validate(self._options_payload(args, dict(kwargs)))
        topic_id = _clean(options.topic_id) or self.public_topic_id
        payload = {
            "p": "hcs-20",
            "op": "burn",
            "tick": _normalize_tick(options.tick),
            "amt": _require_number_string(options.amount, "amount"),
            "from": _validate_topic_id(options.from_account, "from"),
            "m": _clean(options.memo) or None,
        }
        result = self._submit_message(topic_id, payload, _clean(options.memo))
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def registerTopic(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs20RegisterTopicOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        payload = {
            "p": "hcs-20",
            "op": "register",
            "name": _clean(options.name),
            "metadata": _clean(options.metadata) or None,
            "private": bool(options.is_private),
            "t_id": _validate_topic_id(options.topic_id, "topicId"),
            "m": _clean(options.memo) or None,
        }
        result = self._submit_message(self.registry_topic_id, payload, _clean(options.memo))
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    create_public_topic = createPublicTopic
    create_registry_topic = createRegistryTopic
    deploy_points = deployPoints
    mint_points = mintPoints
    transfer_points = transferPoints
    burn_points = burnPoints
    register_topic = registerTopic


class AsyncHcs20Client(AsyncHcsModuleClient):
    """Asynchronous HCS-20 client."""

    def __init__(
        self,
        transport: AsyncHttpTransport | None = None,
        *,
        operator_id: str,
        operator_key: str,
        network: str = "testnet",
        public_topic_id: str | None = None,
        registry_topic_id: str | None = None,
        key_type: str | None = None,
    ) -> None:
        config = SdkConfig.from_env()
        resolved_transport = transport or AsyncHttpTransport(
            base_url=config.network.registry_broker_base_url or _DEFAULT_REGISTRY_BROKER_BASE_URL,
        )
        super().__init__("hcs20", resolved_transport)
        self._sync_client = Hcs20Client(
            transport=SyncHttpTransport(
                base_url=resolved_transport.base_url,
                headers=dict(resolved_transport.headers or {}),
            ),
            operator_id=operator_id,
            operator_key=operator_key,
            network=network,
            public_topic_id=public_topic_id,
            registry_topic_id=registry_topic_id,
            key_type=key_type,
        )

    async def createPublicTopic(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.createPublicTopic, *args, **kwargs)

    async def createRegistryTopic(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.createRegistryTopic, *args, **kwargs)

    async def deployPoints(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.deployPoints, *args, **kwargs)

    async def mintPoints(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.mintPoints, *args, **kwargs)

    async def transferPoints(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.transferPoints, *args, **kwargs)

    async def burnPoints(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.burnPoints, *args, **kwargs)

    async def registerTopic(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.registerTopic, *args, **kwargs)

    create_public_topic = createPublicTopic
    create_registry_topic = createRegistryTopic
    deploy_points = deployPoints
    mint_points = mintPoints
    transfer_points = transferPoints
    burn_points = burnPoints
    register_topic = registerTopic
