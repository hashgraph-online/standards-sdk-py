"""HCS-16 client with direct on-chain execution parity."""

# ruff: noqa: N802

from __future__ import annotations

import asyncio
import importlib
import json
import re
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol, cast

from standards_sdk_py.exceptions import ErrorContext, ParseError, TransportError, ValidationError
from standards_sdk_py.hcs16.models import (
    FloraOperation,
    FloraTopicType,
    Hcs16AssembleKeyListOptions,
    Hcs16CreateFloraAccountOptions,
    Hcs16CreateFloraAccountResult,
    Hcs16CreateFloraAccountWithTopicsOptions,
    Hcs16CreateFloraAccountWithTopicsResult,
    Hcs16CreateFloraProfileOptions,
    Hcs16CreateFloraProfileResult,
    Hcs16CreateFloraTopicOptions,
    Hcs16FloraTopics,
    Hcs16KeyList,
    Hcs16SendFloraCreatedOptions,
    Hcs16SendFloraJoinAcceptedOptions,
    Hcs16SendFloraJoinRequestOptions,
    Hcs16SendFloraJoinVoteOptions,
    Hcs16SendStateUpdateOptions,
    Hcs16SendTransactionOptions,
    Hcs16SignScheduleOptions,
    Hcs16TransactionResult,
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
_TOPIC_ID_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_ACCOUNT_ID_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_TOPIC_MEMO_PATTERN = re.compile(r"^hcs-16:([0-9.]+):(\d)$")
_ONCHAIN_CREDS_ERROR = "on-chain operator credentials are not configured"
_HCS16_FLORA_ACCOUNT_CREATE_TRANSACTION_MEMO = "hcs-16:op:0:0"
_HCS17_STATE_HASH_TRANSACTION_MEMO = "hcs-17:op:6:2"
_HCS16_OPERATION_ENUM_BY_OPERATION: dict[FloraOperation, int] = {
    FloraOperation.FLORA_CREATED: 0,
    FloraOperation.TRANSACTION: 1,
    FloraOperation.STATE_UPDATE: 2,
    FloraOperation.FLORA_JOIN_REQUEST: 3,
    FloraOperation.FLORA_JOIN_VOTE: 4,
    FloraOperation.FLORA_JOIN_ACCEPTED: 5,
}
_HCS16_TOPIC_TYPE_BY_OPERATION: dict[FloraOperation, FloraTopicType] = {
    FloraOperation.FLORA_CREATED: FloraTopicType.COMMUNICATION,
    FloraOperation.TRANSACTION: FloraTopicType.TRANSACTION,
    FloraOperation.STATE_UPDATE: FloraTopicType.STATE,
    FloraOperation.FLORA_JOIN_REQUEST: FloraTopicType.COMMUNICATION,
    FloraOperation.FLORA_JOIN_VOTE: FloraTopicType.COMMUNICATION,
    FloraOperation.FLORA_JOIN_ACCEPTED: FloraTopicType.STATE,
}


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


def _validate_account_id(value: str, field_name: str = "accountId") -> str:
    cleaned = value.strip()
    if not _ACCOUNT_ID_PATTERN.fullmatch(cleaned):
        raise ValidationError(
            f"{field_name} must be a Hedera account ID (e.g. 0.0.12345)",
            ErrorContext(details={"field": field_name, "value": value}),
        )
    return cleaned


def _coerce_int(value: object | None, *, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except Exception:
            return default
    return default


def _normalize_memo(value: str | None, fallback: str) -> str:
    cleaned = _clean(value)
    return cleaned or fallback


def _encode_topic_memo(flora_account_id: str, topic_type: FloraTopicType) -> str:
    return f"hcs-16:{_clean(flora_account_id)}:{int(topic_type)}"


def _encode_topic_create_transaction_memo(topic_type: FloraTopicType) -> str:
    operation_code = _HCS16_OPERATION_ENUM_BY_OPERATION[FloraOperation.FLORA_CREATED]
    return f"hcs-16:op:{operation_code}:{int(topic_type)}"


def _encode_message_transaction_memo(operation: FloraOperation) -> str:
    return (
        "hcs-16:op:"
        f"{_HCS16_OPERATION_ENUM_BY_OPERATION[operation]}:"
        f"{int(_HCS16_TOPIC_TYPE_BY_OPERATION[operation])}"
    )


def _merge_inscription_options(
    raw: dict[str, object] | None,
    profile_document: dict[str, object],
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
    metadata_value = mapped.get("metadata")
    merged_metadata = dict(profile_document)
    if isinstance(metadata_value, dict):
        for key, value in metadata_value.items():
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
    profile_document: dict[str, object],
) -> InscribeViaRegistryBrokerOptions:
    payload = _merge_inscription_options(raw, profile_document)
    mode: str = "file"
    raw_mode = payload.get("mode")
    if isinstance(raw_mode, str):
        normalized_mode = raw_mode.strip()
        if normalized_mode in {"file", "upload", "hashinal", "hashinal-collection", "bulk-files"}:
            mode = normalized_mode
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
        mode=cast(Any, mode),
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


class _HederaTransactionResponse(Protocol):
    def getReceipt(self, client: object) -> object: ...


class _HederaSignableTransaction(Protocol):
    def freezeWith(self, client: object) -> _HederaSignableTransaction: ...

    def sign(self, signer: object) -> _HederaSignableTransaction: ...

    def execute(self, client: object) -> _HederaTransactionResponse: ...


class Hcs16Client(HcsModuleClient):
    """Synchronous HCS-16 client."""

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
    ) -> None:
        config = SdkConfig.from_env()
        resolved_transport = transport or SyncHttpTransport(
            base_url=config.network.registry_broker_base_url or _DEFAULT_REGISTRY_BROKER_BASE_URL,
        )
        super().__init__("hcs16", resolved_transport)
        self._network = _normalize_network(network)
        self._hedera: Any | None = None
        self._hedera_client: object | None = None
        self._operator_id: str | None = None
        self._operator_key: Any | None = None

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

        resolved_mirror_base_url = _clean(mirror_base_url) or config.network.mirror_node_base_url
        self._mirror_client = HederaMirrorNode(
            transport=SyncHttpTransport(base_url=resolved_mirror_base_url)
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
                "hedera-sdk-py is required for on-chain HCS-16 operations",
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
        self._operator_id = operator_id
        self._operator_key = private_key
        _ = key_type

    def _require_onchain(self) -> None:
        if self._hedera is None or self._hedera_client is None or self._operator_id is None:
            raise ValidationError(_ONCHAIN_CREDS_ERROR, ErrorContext())

    def _options_payload(self, args: tuple[object, ...], kwargs: dict[str, object]) -> object:
        if kwargs:
            return kwargs
        if args:
            return args[0]
        return {}

    def _public_key_from_string(self, raw_key: str) -> object:
        self._require_onchain()
        assert self._hedera is not None
        cleaned = _clean(raw_key)
        if not cleaned:
            raise ValidationError("public key is required", ErrorContext())
        try:
            return cast(object, self._hedera.PublicKey.fromString(cleaned))
        except Exception:
            try:
                private_key = self._hedera.PrivateKey.fromString(cleaned)
                return cast(object, private_key.getPublicKey())
            except Exception as exc:
                raise ValidationError(
                    "invalid key string",
                    ErrorContext(details={"reason": str(exc), "key": cleaned}),
                ) from exc

    def _private_key_from_string(self, raw_key: str) -> object:
        self._require_onchain()
        assert self._hedera is not None
        cleaned = _clean(raw_key)
        if not cleaned:
            raise ValidationError("private key is required", ErrorContext())
        try:
            return cast(object, self._hedera.PrivateKey.fromString(cleaned))
        except Exception as exc:
            raise ValidationError(
                "invalid private key string",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc

    def _extract_public_key_string_from_account(self, account_id: str) -> str:
        key = self._mirror_client.get_public_key(_validate_account_id(account_id))
        if not key:
            raise ParseError(
                "mirror node did not return a public key for account",
                ErrorContext(details={"account_id": account_id}),
            )
        return key

    def _build_key_list_from_public_key_strings(
        self, key_strings: list[str], threshold: int
    ) -> tuple[object, Hcs16KeyList]:
        self._require_onchain()
        assert self._hedera is not None
        cleaned_keys = [item.strip() for item in key_strings if item.strip()]
        if not cleaned_keys:
            raise ValidationError("keys are required", ErrorContext())
        if threshold <= 0:
            raise ValidationError("threshold must be positive", ErrorContext())
        key_list = self._hedera.KeyList.withThreshold(threshold)
        normalized_keys: list[str] = []
        for raw_key in cleaned_keys:
            public_key = self._public_key_from_string(raw_key)
            key_list.add(public_key)
            normalized_keys.append(raw_key)
        return cast(object, key_list), Hcs16KeyList(keys=normalized_keys, threshold=threshold)

    def _coerce_key_list_input(
        self, raw: Hcs16KeyList | list[str] | dict[str, object]
    ) -> tuple[object, Hcs16KeyList]:
        if isinstance(raw, Hcs16KeyList):
            return self._build_key_list_from_public_key_strings(raw.keys, raw.threshold)
        if isinstance(raw, list):
            return self._build_key_list_from_public_key_strings(
                [item for item in raw if isinstance(item, str)], 1
            )
        parsed = Hcs16KeyList.model_validate(raw)
        return self._build_key_list_from_public_key_strings(parsed.keys, parsed.threshold)

    def _resolve_key_input(self, raw: object | None) -> object | None:
        self._require_onchain()
        if raw is None or raw is False:
            return None
        if raw is True:
            assert self._operator_key is not None
            return cast(object, self._operator_key.getPublicKey())
        if isinstance(raw, str):
            return self._public_key_from_string(raw)
        if isinstance(raw, Hcs16KeyList):
            return self._coerce_key_list_input(raw)[0]
        if isinstance(raw, dict):
            return self._coerce_key_list_input(raw)[0]
        raise ValidationError(
            "invalid key input",
            ErrorContext(details={"type": type(raw).__name__}),
        )

    def _execute_topic_create(
        self, transaction: _HederaSignableTransaction, signer_keys: list[object] | None = None
    ) -> tuple[str, str]:
        self._require_onchain()
        assert self._hedera_client is not None
        tx = transaction
        try:
            if signer_keys:
                tx = tx.freezeWith(self._hedera_client)
                for signer in signer_keys:
                    tx = tx.sign(signer)
            response = tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to create Flora topic",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc
        topic_id = _to_string(getattr(receipt, "topicId", None))
        if not topic_id:
            raise ParseError("failed to create Flora topic", ErrorContext())
        transaction_id = _to_string(getattr(response, "transactionId", None))
        return topic_id, transaction_id

    def _submit_message(
        self,
        topic_id: str,
        payload: Mapping[str, object],
        transaction_memo: str,
        signer_keys: list[object] | None = None,
    ) -> Hcs16TransactionResult:
        self._require_onchain()
        assert self._hedera is not None
        assert self._hedera_client is not None
        validated_topic_id = _validate_topic_id(topic_id)
        tx = self._hedera.TopicMessageSubmitTransaction().setTopicId(
            self._hedera.TopicId.fromString(validated_topic_id)
        )
        tx.setMessage(
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        )
        tx.setTransactionMemo(transaction_memo)
        try:
            if signer_keys:
                tx = tx.freezeWith(self._hedera_client)
                for signer in signer_keys:
                    tx = tx.sign(signer)
            response = tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to submit HCS-16 topic message",
                ErrorContext(details={"reason": str(exc), "topic_id": topic_id}),
            ) from exc
        return Hcs16TransactionResult(
            transactionId=_to_string(getattr(response, "transactionId", None)),
            sequenceNumber=_coerce_int(getattr(receipt, "topicSequenceNumber", None), default=0),
            topicId=validated_topic_id,
        )

    def parseTopicMemo(self, *args: object, **kwargs: object) -> JsonValue:
        payload = self._options_payload(args, dict(kwargs))
        memo = (
            payload
            if isinstance(payload, str)
            else _clean(cast(dict[str, object], payload).get("memo"))
        )
        match = _TOPIC_MEMO_PATTERN.fullmatch(_clean(memo))
        if not match:
            return None
        topic_type_raw = _coerce_int(match.group(2), default=-1)
        if topic_type_raw not in {0, 1, 2}:
            return None
        return {
            "protocol": "hcs-16",
            "floraAccountId": match.group(1),
            "topicType": topic_type_raw,
        }

    def assembleKeyList(self, *args: object, **kwargs: object) -> JsonValue:
        if len(args) == 2 and isinstance(args[0], list) and isinstance(args[1], int):
            options = Hcs16AssembleKeyListOptions(
                members=cast(list[str], args[0]), threshold=args[1]
            )
        else:
            options = Hcs16AssembleKeyListOptions.model_validate(
                self._options_payload(args, dict(kwargs))
            )
        if not options.members:
            raise ValidationError("members are required", ErrorContext())
        key_strings: list[str] = []
        for member in options.members:
            key_strings.append(self._extract_public_key_string_from_account(member))
        _, normalized = self._build_key_list_from_public_key_strings(key_strings, options.threshold)
        return cast(JsonValue, normalized.model_dump(by_alias=True))

    def createFloraAccount(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs16CreateFloraAccountOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        self._require_onchain()
        assert self._hedera is not None
        assert self._hedera_client is not None
        key_list, _normalized = self._coerce_key_list_input(options.key_list)
        initial_balance = (
            options.initial_balance_hbar
            if options.initial_balance_hbar is not None and options.initial_balance_hbar > 0
            else 1.0
        )
        max_associations = (
            options.max_automatic_token_associations
            if options.max_automatic_token_associations is not None
            else -1
        )
        tx = (
            self._hedera.AccountCreateTransaction()
            .setKey(key_list)
            .setInitialBalance(self._hedera.Hbar(initial_balance))
            .setMaxAutomaticTokenAssociations(max_associations)
            .setTransactionMemo(_HCS16_FLORA_ACCOUNT_CREATE_TRANSACTION_MEMO)
        )
        try:
            response = tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to create Flora account",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc
        account_id = _to_string(getattr(receipt, "accountId", None))
        if not account_id:
            raise ParseError("failed to create Flora account", ErrorContext())
        result = Hcs16CreateFloraAccountResult(
            accountId=account_id,
            transactionId=_to_string(getattr(response, "transactionId", None)),
        )
        return cast(JsonValue, result.model_dump(by_alias=True))

    def createFloraTopic(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs16CreateFloraTopicOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        self._require_onchain()
        assert self._hedera is not None
        topic_memo = _encode_topic_memo(options.flora_account_id, options.topic_type)
        transaction_memo = _normalize_memo(
            options.transaction_memo,
            _encode_topic_create_transaction_memo(options.topic_type),
        )
        tx = (
            self._hedera.TopicCreateTransaction()
            .setTopicMemo(topic_memo)
            .setTransactionMemo(transaction_memo)
        )
        admin_key = self._resolve_key_input(options.admin_key)
        submit_key = self._resolve_key_input(options.submit_key)
        if admin_key is not None:
            tx.setAdminKey(admin_key)
        if submit_key is not None:
            tx.setSubmitKey(submit_key)
        auto_renew_account_id = _clean(options.auto_renew_account_id)
        if auto_renew_account_id:
            tx.setAutoRenewAccountId(
                self._hedera.AccountId.fromString(_validate_account_id(auto_renew_account_id))
            )
        signer_keys: list[object] = []
        for raw_key in options.signer_keys or []:
            signer_keys.append(self._private_key_from_string(raw_key))
        topic_id, transaction_id = self._execute_topic_create(
            tx, signer_keys=signer_keys if signer_keys else None
        )
        return cast(JsonValue, {"topicId": topic_id, "transactionId": transaction_id})

    def createFloraAccountWithTopics(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs16CreateFloraAccountWithTopicsOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        key_list = cast(
            dict[str, object],
            self.assembleKeyList({"members": options.members, "threshold": options.threshold}),
        )
        submit_key_list = cast(
            dict[str, object],
            self.assembleKeyList({"members": options.members, "threshold": 1}),
        )
        initial_balance = (
            options.initial_balance_hbar
            if options.initial_balance_hbar is not None and options.initial_balance_hbar > 0
            else 5.0
        )
        account_result = cast(
            dict[str, object],
            self.createFloraAccount(
                {
                    "keyList": key_list,
                    "initialBalanceHbar": initial_balance,
                    "maxAutomaticTokenAssociations": -1,
                }
            ),
        )
        flora_account_id = str(account_result.get("accountId") or "")
        if not flora_account_id:
            raise ParseError("createFloraAccount did not return accountId", ErrorContext())
        communication = cast(
            dict[str, object],
            self.createFloraTopic(
                {
                    "floraAccountId": flora_account_id,
                    "topicType": FloraTopicType.COMMUNICATION,
                    "adminKey": key_list,
                    "submitKey": submit_key_list,
                    "autoRenewAccountId": options.auto_renew_account_id,
                }
            ),
        )
        transaction_topic = cast(
            dict[str, object],
            self.createFloraTopic(
                {
                    "floraAccountId": flora_account_id,
                    "topicType": FloraTopicType.TRANSACTION,
                    "adminKey": key_list,
                    "submitKey": submit_key_list,
                    "autoRenewAccountId": options.auto_renew_account_id,
                }
            ),
        )
        state = cast(
            dict[str, object],
            self.createFloraTopic(
                {
                    "floraAccountId": flora_account_id,
                    "topicType": FloraTopicType.STATE,
                    "adminKey": key_list,
                    "submitKey": submit_key_list,
                    "autoRenewAccountId": options.auto_renew_account_id,
                }
            ),
        )
        topics = Hcs16FloraTopics(
            communication=str(communication.get("topicId") or ""),
            transaction=str(transaction_topic.get("topicId") or ""),
            state=str(state.get("topicId") or ""),
        )
        result = Hcs16CreateFloraAccountWithTopicsResult(
            floraAccountId=flora_account_id, topics=topics
        )
        return cast(JsonValue, result.model_dump(by_alias=True))

    def sendFloraCreated(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs16SendFloraCreatedOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        payload = {
            "p": "hcs-16",
            "op": FloraOperation.FLORA_CREATED.value,
            "operator_id": _validate_account_id(options.operator_id, "operatorId"),
            "flora_account_id": _validate_account_id(options.flora_account_id, "floraAccountId"),
            "topics": options.topics.model_dump(by_alias=True),
        }
        result = self._submit_message(
            options.topic_id,
            payload,
            _encode_message_transaction_memo(FloraOperation.FLORA_CREATED),
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def publishFloraCreated(self, *args: object, **kwargs: object) -> JsonValue:
        payload = self._options_payload(args, dict(kwargs))
        if (
            isinstance(payload, dict)
            and "communicationTopicId" in payload
            and "topicId" not in payload
        ):
            payload = dict(payload)
            payload["topicId"] = payload.pop("communicationTopicId")
        return self.sendFloraCreated(payload)

    def sendTransaction(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs16SendTransactionOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        payload = {
            "p": "hcs-16",
            "op": FloraOperation.TRANSACTION.value,
            "operator_id": _validate_account_id(options.operator_id, "operatorId"),
            "schedule_id": _clean(options.schedule_id),
            "data": options.data,
            "m": options.data,
        }
        result = self._submit_message(
            options.topic_id,
            payload,
            _encode_message_transaction_memo(FloraOperation.TRANSACTION),
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def sendStateUpdate(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs16SendStateUpdateOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        payload: dict[str, object] = {
            "p": "hcs-17",
            "op": "state_hash",
            "state_hash": _clean(options.hash),
            "topics": options.topics or [],
            "account_id": _validate_account_id(
                options.account_id or options.operator_id, "accountId"
            ),
            "timestamp": datetime.now(UTC).isoformat(),
            "m": options.memo,
        }
        if options.epoch is not None:
            payload["epoch"] = options.epoch
        signer_keys = [self._private_key_from_string(item) for item in options.signer_keys or []]
        result = self._submit_message(
            options.topic_id,
            payload,
            _normalize_memo(options.transaction_memo, _HCS17_STATE_HASH_TRANSACTION_MEMO),
            signer_keys=signer_keys if signer_keys else None,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def sendFloraJoinRequest(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs16SendFloraJoinRequestOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        payload = {
            "p": "hcs-16",
            "op": FloraOperation.FLORA_JOIN_REQUEST.value,
            "operator_id": _validate_account_id(options.operator_id, "operatorId"),
            "account_id": _validate_account_id(options.account_id, "accountId"),
            "connection_request_id": options.connection_request_id,
            "connection_topic_id": _validate_topic_id(
                options.connection_topic_id, "connectionTopicId"
            ),
            "connection_seq": options.connection_seq,
        }
        signer_key = _clean(options.signer_key)
        signer_keys = [self._private_key_from_string(signer_key)] if signer_key else None
        result = self._submit_message(
            options.topic_id,
            payload,
            _encode_message_transaction_memo(FloraOperation.FLORA_JOIN_REQUEST),
            signer_keys=signer_keys,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def sendFloraJoinVote(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs16SendFloraJoinVoteOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        payload = {
            "p": "hcs-16",
            "op": FloraOperation.FLORA_JOIN_VOTE.value,
            "operator_id": _validate_account_id(options.operator_id, "operatorId"),
            "account_id": _validate_account_id(options.account_id, "accountId"),
            "approve": options.approve,
            "connection_request_id": options.connection_request_id,
            "connection_seq": options.connection_seq,
        }
        signer_key = _clean(options.signer_key)
        signer_keys = [self._private_key_from_string(signer_key)] if signer_key else None
        result = self._submit_message(
            options.topic_id,
            payload,
            _encode_message_transaction_memo(FloraOperation.FLORA_JOIN_VOTE),
            signer_keys=signer_keys,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def sendFloraJoinAccepted(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs16SendFloraJoinAcceptedOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        payload: dict[str, object] = {
            "p": "hcs-16",
            "op": FloraOperation.FLORA_JOIN_ACCEPTED.value,
            "operator_id": _validate_account_id(options.operator_id, "operatorId"),
            "members": [_validate_account_id(member, "members") for member in options.members],
        }
        if options.epoch is not None:
            payload["epoch"] = options.epoch
        signer_keys = [self._private_key_from_string(item) for item in options.signer_keys or []]
        result = self._submit_message(
            options.topic_id,
            payload,
            _encode_message_transaction_memo(FloraOperation.FLORA_JOIN_ACCEPTED),
            signer_keys=signer_keys if signer_keys else None,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def signSchedule(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs16SignScheduleOptions.model_validate(self._options_payload(args, dict(kwargs)))
        self._require_onchain()
        assert self._hedera is not None
        assert self._hedera_client is not None
        signer_key = self._private_key_from_string(options.signer_key)
        try:
            schedule_id = self._hedera.ScheduleId.fromString(_clean(options.schedule_id))
            tx = self._hedera.ScheduleSignTransaction().setScheduleId(schedule_id)
            tx = tx.freezeWith(self._hedera_client)
            tx = tx.sign(signer_key)
            response = tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to sign schedule",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc
        result = Hcs16TransactionResult(
            transactionId=_to_string(getattr(response, "transactionId", None)),
            sequenceNumber=_coerce_int(getattr(receipt, "topicSequenceNumber", None), default=0)
            or None,
            topicId=None,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def createFloraProfile(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs16CreateFloraProfileOptions.model_validate(
            self._options_payload(args, dict(kwargs))
        )
        if not options.signer_keys:
            raise ValidationError("createFloraProfile requires signerKeys", ErrorContext())
        profile_payload: dict[str, object] = {
            "version": "1.0",
            "type": 3,
            "display_name": options.display_name,
            "members": [
                member.model_dump(by_alias=True, exclude_none=True) for member in options.members
            ],
            "threshold": options.threshold,
            "topics": options.topics.model_dump(by_alias=True),
            "inboundTopicId": options.inbound_topic_id or options.topics.communication,
            "outboundTopicId": options.outbound_topic_id or options.topics.transaction,
            "bio": options.bio,
            "metadata": options.metadata,
            "policies": options.policies,
        }
        content = json.dumps(profile_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        profile_name = options.display_name.strip().lower().replace(" ", "-") or "flora-profile"
        inscription_result = inscribe(
            InscriptionInput(
                type="buffer",
                buffer=content,
                fileName=f"profile-{profile_name}-{int(time.time() * 1000)}.json",
                mimeType="application/json",
            ),
            _build_inscription_options(options.inscription_options, profile_payload),
        )
        if not inscription_result.confirmed:
            raise TransportError(
                "failed to inscribe Flora profile",
                ErrorContext(
                    details={
                        "job_id": inscription_result.job_id,
                        "status": inscription_result.status,
                    }
                ),
            )
        profile_topic_id = _clean(inscription_result.topic_id)
        if not profile_topic_id and _clean(inscription_result.hrl).startswith("hcs://1/"):
            profile_topic_id = _clean(inscription_result.hrl).removeprefix("hcs://1/").split("/")[0]
        if not profile_topic_id:
            raise ParseError(
                "profile inscription did not return a topic ID",
                ErrorContext(
                    details={"job_id": inscription_result.job_id, "hrl": inscription_result.hrl}
                ),
            )
        self._require_onchain()
        assert self._hedera is not None
        assert self._hedera_client is not None
        memo_value = f"hcs-11:hcs://1/{_validate_topic_id(profile_topic_id, 'profileTopicId')}"
        account_id = self._hedera.AccountId.fromString(
            _validate_account_id(options.flora_account_id)
        )
        tx = (
            self._hedera.AccountUpdateTransaction()
            .setAccountId(account_id)
            .setAccountMemo(memo_value)
        )
        signer_keys = [self._private_key_from_string(item) for item in options.signer_keys]
        try:
            tx = tx.freezeWith(self._hedera_client)
            for signer in signer_keys:
                tx = tx.sign(signer)
            response = tx.execute(self._hedera_client)
            response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to update Flora account memo with profile topic",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc
        result = Hcs16CreateFloraProfileResult(
            profileTopicId=profile_topic_id,
            transactionId=_to_string(getattr(response, "transactionId", None)),
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    assemble_key_list = assembleKeyList
    create_flora_account = createFloraAccount
    create_flora_account_with_topics = createFloraAccountWithTopics
    create_flora_profile = createFloraProfile
    create_flora_topic = createFloraTopic
    publish_flora_created = publishFloraCreated
    send_flora_created = sendFloraCreated
    send_flora_join_accepted = sendFloraJoinAccepted
    send_flora_join_request = sendFloraJoinRequest
    send_flora_join_vote = sendFloraJoinVote
    send_state_update = sendStateUpdate
    send_transaction = sendTransaction
    sign_schedule = signSchedule


class AsyncHcs16Client(AsyncHcsModuleClient):
    """Asynchronous HCS-16 client."""

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
        super().__init__("hcs16", resolved_transport)
        self._sync_client = Hcs16Client(
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

    async def assembleKeyList(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.assembleKeyList, *args, **kwargs)

    async def createFloraAccount(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.createFloraAccount, *args, **kwargs)

    async def createFloraAccountWithTopics(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(
            self._sync_client.createFloraAccountWithTopics, *args, **kwargs
        )

    async def createFloraProfile(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.createFloraProfile, *args, **kwargs)

    async def createFloraTopic(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.createFloraTopic, *args, **kwargs)

    async def publishFloraCreated(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.publishFloraCreated, *args, **kwargs)

    async def sendFloraCreated(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.sendFloraCreated, *args, **kwargs)

    async def sendFloraJoinAccepted(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.sendFloraJoinAccepted, *args, **kwargs)

    async def sendFloraJoinRequest(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.sendFloraJoinRequest, *args, **kwargs)

    async def sendFloraJoinVote(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.sendFloraJoinVote, *args, **kwargs)

    async def sendStateUpdate(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.sendStateUpdate, *args, **kwargs)

    async def sendTransaction(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.sendTransaction, *args, **kwargs)

    async def signSchedule(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.signSchedule, *args, **kwargs)

    assemble_key_list = assembleKeyList
    create_flora_account = createFloraAccount
    create_flora_account_with_topics = createFloraAccountWithTopics
    create_flora_profile = createFloraProfile
    create_flora_topic = createFloraTopic
    publish_flora_created = publishFloraCreated
    send_flora_created = sendFloraCreated
    send_flora_join_accepted = sendFloraJoinAccepted
    send_flora_join_request = sendFloraJoinRequest
    send_flora_join_vote = sendFloraJoinVote
    send_state_update = sendStateUpdate
    send_transaction = sendTransaction
    sign_schedule = signSchedule
