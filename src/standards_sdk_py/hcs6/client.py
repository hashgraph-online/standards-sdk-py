"""HCS-6 client with direct on-chain execution parity."""

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
from standards_sdk_py.hcs6.models import (
    Hcs6CreateHashinalOptions,
    Hcs6CreateHashinalResponse,
    Hcs6CreateRegistryOptions,
    Hcs6InscribeAndMintOptions,
    Hcs6Message,
    Hcs6MintOptions,
    Hcs6MintResponse,
    Hcs6Operation,
    Hcs6QueryRegistryOptions,
    Hcs6RegisterEntryOptions,
    Hcs6RegisterOptions,
    Hcs6RegistryEntry,
    Hcs6RegistryOperationResponse,
    Hcs6RegistryType,
    Hcs6TopicRegistrationResponse,
    Hcs6TopicRegistry,
    build_hcs6_hrl,
)
from standards_sdk_py.inscriber import (
    InscribeViaRegistryBrokerOptions,
    InscriptionInput,
    inscribe,
)
from standards_sdk_py.mirror import MirrorNodeClient
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.hcs_module import AsyncHcsModuleClient, HcsModuleClient
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.types import JsonValue

_TOPIC_ID_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_HCS6_TOPIC_MEMO_PATTERN = re.compile(r"^hcs-6:(\d):(\d+)$")
_DEFAULT_MIRROR_BY_NETWORK = {
    "mainnet": "https://mainnet-public.mirrornode.hedera.com/api/v1",
    "testnet": "https://testnet.mirrornode.hedera.com/api/v1",
}
_DEFAULT_REGISTRY_BROKER_BASE_URL = "https://registry.hashgraphonline.com"
_DEFAULT_INSCRIBER_BASE_URL = "https://v2-api.tier.bot/api"
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


def _parse_hcs6_topic_memo(memo: object) -> int | None:
    if not isinstance(memo, str):
        return None
    match = _HCS6_TOPIC_MEMO_PATTERN.fullmatch(memo.strip())
    if match is None:
        return None
    if match.group(1) != "1":
        return None
    try:
        ttl = int(match.group(2))
    except ValueError:
        return None
    if ttl <= 0:
        return None
    return ttl


def _build_hcs6_topic_memo(ttl: int) -> str:
    resolved_ttl = ttl if ttl > 0 else _DEFAULT_TTL
    return f"hcs-6:1:{resolved_ttl}"


class Hcs6Client(HcsModuleClient):
    """Synchronous HCS-6 client."""

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
        super().__init__("hcs6", resolved_transport)

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
        self._operator_id: str | None = None
        self._operator_key: Any | None = None
        self._operator_key_string: str | None = None
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
                "hedera-sdk-py is required for on-chain HCS-6 operations",
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

        client = hedera_client or (
            hedera.Client.forMainnet() if self._network == "mainnet" else hedera.Client.forTestnet()
        )
        if hedera_client is None:
            cast(Any, client).setOperator(account_id, private_key)

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
        self._operator_key_string = operator_key

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
                except Exception as exc:
                    raise ValidationError(
                        "failed to parse key as public or private key",
                        ErrorContext(details={"reason": str(exc)}),
                    ) from exc
        get_public_key = getattr(raw_key, "getPublicKey", None)
        if callable(get_public_key):
            return cast(object, get_public_key())
        return None

    def _resolve_private_key(self, raw_key: object | None) -> object | None:
        if raw_key is None:
            return None
        if raw_key is True:
            return self._operator_key
        if raw_key is False:
            return None
        if self._hedera is None:
            raise ValidationError(
                "on-chain operator credentials are not configured", ErrorContext()
            )
        if isinstance(raw_key, str):
            cleaned = raw_key.strip()
            if not cleaned:
                return None
            try:
                return cast(object, self._hedera.PrivateKey.fromString(cleaned))
            except Exception as exc:
                raise ValidationError(
                    "invalid private key",
                    ErrorContext(details={"reason": str(exc)}),
                ) from exc
        return raw_key

    def _validate_message(self, message: Hcs6Message) -> None:
        if message.p != "hcs-6":
            raise ValidationError("message p must be hcs-6", ErrorContext())
        if message.op != Hcs6Operation.REGISTER:
            raise ValidationError("message op must be register", ErrorContext())
        _validate_topic_id(message.t_id, "t_id")
        if message.m is not None and len(message.m.strip()) > 500:
            raise ValidationError("message memo exceeds 500 characters", ErrorContext())

    def _extract_serial_number(self, receipt: object) -> int | None:
        serial_candidates = (
            getattr(receipt, "serials", None),
            getattr(receipt, "serialNumbers", None),
            getattr(receipt, "serial_numbers", None),
        )
        for candidate in serial_candidates:
            if candidate is None:
                continue
            try:
                first = candidate[0]
            except Exception:
                try:
                    size = int(candidate.size())
                    if size <= 0:
                        continue
                    first = candidate.get(0)
                except Exception:
                    continue
            try:
                return int(_to_string(first))
            except ValueError:
                continue
        return None

    def createRegistry(self, *args: object, **kwargs: object) -> JsonValue:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(
                "on-chain operator credentials are not configured", ErrorContext()
            )

        payload = self._parse_single_options(args, kwargs, "createRegistry")
        options = Hcs6CreateRegistryOptions.model_validate(payload)
        ttl = options.ttl if options.ttl > 0 else _DEFAULT_TTL
        if ttl < _MIN_TTL:
            raise ValidationError("TTL must be at least 3600 seconds", ErrorContext())

        topic_memo = _clean(options.memo_override) or _build_hcs6_topic_memo(ttl)
        transaction = self._hedera.TopicCreateTransaction().setTopicMemo(topic_memo)

        admin_key = self._resolve_public_key(options.admin_key, options.use_operator_as_admin)
        if admin_key is not None:
            transaction.setAdminKey(admin_key)
        submit_key = self._resolve_public_key(options.submit_key, options.use_operator_as_submit)
        if submit_key is not None:
            transaction.setSubmitKey(submit_key)

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
        result = Hcs6TopicRegistrationResponse(
            success=True,
            topicId=topic_id,
            transactionId=_to_string(getattr(response, "transactionId", None)) or None,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def submitMessage(self, *args: object, **kwargs: object) -> JsonValue:
        topic_id, payload, _submit_key = self._parse_submit_inputs(
            args, kwargs, method="submitMessage"
        )
        return self._submit_message_with_key(topic_id, payload, None)

    def submitMessageWithKey(self, *args: object, **kwargs: object) -> JsonValue:
        topic_id, payload, submit_key = self._parse_submit_inputs(
            args, kwargs, method="submitMessageWithKey"
        )
        return self._submit_message_with_key(topic_id, payload, submit_key)

    def registerEntry(self, *args: object, **kwargs: object) -> JsonValue:
        return self._register_entry_with_key(*args, **kwargs, force_submit_key=None)

    def registerEntryWithKey(self, *args: object, **kwargs: object) -> JsonValue:
        return self._register_entry_with_key(*args, **kwargs, force_submit_key="__from_inputs__")

    def _register_entry_with_key(
        self,
        *args: object,
        force_submit_key: object | None,
        **kwargs: object,
    ) -> JsonValue:
        registry_topic_id, options_payload, submit_key = self._parse_register_inputs(args, kwargs)
        options = Hcs6RegisterEntryOptions.model_validate(options_payload)
        message = Hcs6Message(
            t_id=_validate_topic_id(options.target_topic_id, "targetTopicId"), m=options.memo
        )
        self._validate_message(message)

        analytics_memo = options.analytics_memo or "hcs-6:op:0:1"
        resolved_submit_key = (
            submit_key if force_submit_key == "__from_inputs__" else force_submit_key
        )
        return self._submit_message_with_key(
            registry_topic_id,
            message.model_dump(by_alias=True, exclude_none=True),
            resolved_submit_key,
            analytics_memo=analytics_memo,
        )

    def _submit_message_with_key(
        self,
        topic_id: str,
        payload: Mapping[str, object],
        submit_key: object | None,
        *,
        analytics_memo: str | None = None,
    ) -> JsonValue:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(
                "on-chain operator credentials are not configured", ErrorContext()
            )
        topic = _validate_topic_id(topic_id, "topicId")
        message = Hcs6Message.model_validate(dict(payload))
        self._validate_message(message)

        tx = self._hedera.TopicMessageSubmitTransaction().setTopicId(
            self._hedera.TopicId.fromString(topic)
        )
        message_bytes = json.dumps(
            message.model_dump(by_alias=True, exclude_none=True), separators=(",", ":")
        ).encode("utf-8")
        tx.setMessage(message_bytes)
        if analytics_memo and analytics_memo.strip():
            tx.setTransactionMemo(analytics_memo.strip())

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
                "failed to execute HCS-6 submit message transaction",
                ErrorContext(details={"reason": str(exc), "topic_id": topic}),
            ) from exc

        result = Hcs6RegistryOperationResponse(
            success=True,
            transactionId=_to_string(getattr(response, "transactionId", None)) or None,
            sequenceNumber=int(_to_string(getattr(receipt, "topicSequenceNumber", 0)) or 0),
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def getRegistry(self, *args: object, **kwargs: object) -> JsonValue:
        topic_id, options = self._parse_get_registry_inputs(args, kwargs)
        topic_info = self._mirror_client.get_topic_info(topic_id)
        ttl = _parse_hcs6_topic_memo(topic_info.get("memo"))
        if ttl is None:
            raise ValidationError(
                f"topic {topic_id} is not an HCS-6 registry",
                ErrorContext(details={"topic_id": topic_id}),
            )
        sequence = f"gt:{options.skip}" if options.skip > 0 else None
        topic_messages = self._mirror_client.get_topic_messages(
            topic_id,
            sequence_number=sequence,
            limit=options.limit,
            order=options.order,
        )
        latest_entry: Hcs6RegistryEntry | None = None
        for item in topic_messages.messages:
            decoded = self._decode_message_dict(item.message)
            if decoded is None:
                continue
            try:
                message = Hcs6Message.model_validate(decoded)
                self._validate_message(message)
            except (PydanticValidationError, ValidationError):
                continue
            entry = Hcs6RegistryEntry(
                topicId=topic_id,
                sequence=int(item.sequence_number or 0),
                timestamp=item.consensus_timestamp,
                payer=str(getattr(item, "payer_account_id", "") or ""),
                message=message,
                consensus_timestamp=item.consensus_timestamp,
                registry_type=Hcs6RegistryType.NON_INDEXED,
            )
            if latest_entry is None or entry.timestamp > latest_entry.timestamp:
                latest_entry = entry

        entries = [latest_entry] if latest_entry is not None else []
        registry = Hcs6TopicRegistry(
            topicId=topic_id,
            registryType=Hcs6RegistryType.NON_INDEXED,
            ttl=ttl,
            entries=entries,
            latestEntry=latest_entry,
        )
        return cast(JsonValue, registry.model_dump(by_alias=True, exclude_none=True))

    def mint(self, *args: object, **kwargs: object) -> JsonValue:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(
                "on-chain operator credentials are not configured", ErrorContext()
            )
        options_payload = self._parse_single_options(args, kwargs, "mint")
        options = Hcs6MintOptions.model_validate(options_payload)
        if not options.metadata_topic_id:
            return cast(
                JsonValue,
                Hcs6MintResponse(
                    success=False,
                    error="metadataTopicId is required for mint()",
                ).model_dump(by_alias=True, exclude_none=True),
            )

        hrl = build_hcs6_hrl(_validate_topic_id(options.metadata_topic_id, "metadataTopicId"))
        tx = self._hedera.TokenMintTransaction().setTokenId(
            self._hedera.TokenId.fromString(_clean(options.token_id))
        )
        tx.setMetadata([hrl.encode("utf-8")])
        if options.memo:
            tx.setTransactionMemo(options.memo)

        supply_key = self._resolve_private_key(options.supply_key)
        try:
            if supply_key is None:
                response = tx.execute(self._hedera_client)
            else:
                frozen_tx = tx.freezeWith(self._hedera_client)
                frozen_tx.sign(supply_key)
                response = frozen_tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            return cast(
                JsonValue,
                Hcs6MintResponse(success=False, error=str(exc)).model_dump(
                    by_alias=True, exclude_none=True
                ),
            )
        result = Hcs6MintResponse(
            success=True,
            serialNumber=self._extract_serial_number(receipt),
            transactionId=_to_string(getattr(response, "transactionId", None)) or None,
            metadata=hrl,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def inscribeAndMint(self, *args: object, **kwargs: object) -> JsonValue:
        options_payload = self._parse_single_options(args, kwargs, "inscribeAndMint")
        options = Hcs6InscribeAndMintOptions.model_validate(options_payload)
        inscription_topic_id = self._inscribe_input(
            options.inscription_input,
            metadata=None,
            inscription_options=options.inscription_options,
        )
        return self.mint(
            {
                "tokenId": options.token_id,
                "metadataTopicId": inscription_topic_id,
                "supplyKey": options.supply_key,
                "memo": options.memo,
            }
        )

    def createHashinal(self, *args: object, **kwargs: object) -> JsonValue:
        options_payload = self._parse_single_options(args, kwargs, "createHashinal")
        options = Hcs6CreateHashinalOptions.model_validate(options_payload)
        return self._register_dynamic_hashinal(
            metadata=options.metadata,
            data=None,
            memo=options.memo,
            ttl=options.ttl,
            inscription_options=options.inscription_options,
            registry_topic_id=options.registry_topic_id,
            submit_key=options.submit_key,
        )

    def register(self, *args: object, **kwargs: object) -> JsonValue:
        options_payload = self._parse_single_options(args, kwargs, "register")
        options = Hcs6RegisterOptions.model_validate(options_payload)
        return self._register_dynamic_hashinal(
            metadata=options.metadata,
            data=options.data,
            memo=options.memo,
            ttl=options.ttl,
            inscription_options=options.inscription_options,
            registry_topic_id=options.registry_topic_id,
            submit_key=options.submit_key,
        )

    def _register_dynamic_hashinal(
        self,
        *,
        metadata: dict[str, object],
        data: dict[str, object] | None,
        memo: str | None,
        ttl: int | None,
        inscription_options: dict[str, object] | None,
        registry_topic_id: str | None,
        submit_key: str | None,
    ) -> JsonValue:
        topic_id = _clean(registry_topic_id)
        registry_tx_id: str | None = None
        if not topic_id:
            created = cast(dict[str, object], self.createRegistry({"ttl": ttl, "submitKey": True}))
            if not bool(created.get("success")):
                return cast(
                    JsonValue,
                    Hcs6CreateHashinalResponse(
                        success=False,
                        error=str(created.get("error") or "failed to create HCS-6 registry"),
                    ).model_dump(by_alias=True, exclude_none=True),
                )
            topic_id = str(created.get("topicId") or "")
            registry_tx_id = str(created.get("transactionId") or "") or None
        else:
            topic_id = _validate_topic_id(topic_id, "registryTopicId")
            topic_info = self._mirror_client.get_topic_info(topic_id)
            if _parse_hcs6_topic_memo(topic_info.get("memo")) is None:
                return cast(
                    JsonValue,
                    Hcs6CreateHashinalResponse(
                        success=False,
                        error=f"Topic {topic_id} is not a valid HCS-6 registry",
                    ).model_dump(by_alias=True, exclude_none=True),
                )

        inscription_topic_id = self._inscribe_input(
            self._build_inscription_input(metadata, data),
            metadata=metadata,
            inscription_options=inscription_options,
        )
        registered = cast(
            dict[str, object],
            self.registerEntryWithKey(
                topic_id,
                {
                    "targetTopicId": inscription_topic_id,
                    "memo": memo or "Dynamic hashinal registration",
                },
                submit_key,
            ),
        )
        if not bool(registered.get("success")):
            return cast(
                JsonValue,
                Hcs6CreateHashinalResponse(
                    success=False,
                    error=str(registered.get("error") or "failed to register entry"),
                ).model_dump(by_alias=True, exclude_none=True),
            )

        response = Hcs6CreateHashinalResponse(
            success=True,
            registryTopicId=topic_id,
            inscriptionTopicId=inscription_topic_id,
            transactionId=registry_tx_id,
        )
        return cast(JsonValue, response.model_dump(by_alias=True, exclude_none=True))

    def _build_inscription_input(
        self, metadata: dict[str, object], data: dict[str, object] | None
    ) -> dict[str, object]:
        if data and isinstance(data.get("base64"), str):
            return {
                "type": "buffer",
                "buffer": base64.b64decode(cast(str, data["base64"])),
                "fileName": "data.bin",
                "mimeType": str(data.get("mimeType") or "application/octet-stream"),
            }
        if data and isinstance(data.get("url"), str):
            return {"type": "url", "url": str(data["url"])}
        return {
            "type": "buffer",
            "buffer": json.dumps(metadata, separators=(",", ":")).encode("utf-8"),
            "fileName": "metadata.json",
            "mimeType": "application/json",
        }

    def _inscribe_input(
        self,
        inscription_input: dict[str, object],
        *,
        metadata: dict[str, object] | None,
        inscription_options: dict[str, object] | None,
    ) -> str:
        if not self._operator_id or not self._operator_key_string:
            raise ValidationError(
                "on-chain operator credentials are not configured", ErrorContext()
            )
        input_payload = InscriptionInput.model_validate(inscription_input)

        opts = dict(inscription_options or {})
        broker_options = InscribeViaRegistryBrokerOptions(
            base_url=str(
                opts.get("baseUrl") or opts.get("base_url") or _DEFAULT_INSCRIBER_BASE_URL
            ),
            api_key=cast(str | None, opts.get("apiKey") or opts.get("api_key")),
            ledger_api_key=cast(str | None, opts.get("ledgerApiKey") or opts.get("ledger_api_key")),
            ledger_account_id=self._operator_id,
            ledger_private_key=self._operator_key_string,
            ledger_network=self._network,
            mode="file",
            metadata=metadata,
            tags=cast(list[str] | None, opts.get("tags")),
            file_standard=cast(str | None, opts.get("fileStandard") or opts.get("file_standard")),
            wait_for_confirmation=True,
        )
        result = inscribe(input_payload, broker_options)
        topic_id = _clean(result.topic_id)
        if not topic_id:
            raise ValidationError("inscription did not return topicId", ErrorContext())
        return _validate_topic_id(topic_id, "inscriptionTopicId")

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
                close_fn()
        except Exception as exc:
            raise TransportError(
                "failed to close HCS-6 Hedera client",
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
        return {str(k): v for k, v in payload.items()}

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

    def _parse_submit_inputs(
        self,
        args: tuple[object, ...],
        kwargs: Mapping[str, object],
        *,
        method: str,
    ) -> tuple[str, dict[str, object], object | None]:
        if len(args) > 3:
            raise ValidationError(
                f"{method} expects at most three positional arguments", ErrorContext()
            )
        if not args and not kwargs.get("topicId") and not kwargs.get("topic_id"):
            raise ValidationError("topicId is required", ErrorContext())
        if args and not isinstance(args[0], str):
            raise ValidationError("topicId must be a string", ErrorContext())
        topic_id_raw = cast(str, args[0] if args else kwargs.get("topicId", kwargs.get("topic_id")))
        topic_id = _validate_topic_id(topic_id_raw, "topicId")

        payload: dict[str, object] = {}
        submit_key: object | None = None
        if len(args) >= 2:
            payload.update(_coerce_mapping(args[1], "payload"))
        if len(args) >= 3:
            submit_key = args[2]
        if kwargs.get("payload") is not None:
            payload.update(_coerce_mapping(kwargs["payload"], "payload"))
        if "submitKey" in kwargs:
            submit_key = kwargs["submitKey"]
        if "submit_key" in kwargs:
            submit_key = kwargs["submit_key"]
        for key, value in kwargs.items():
            if key in {"topicId", "topic_id", "payload", "submitKey", "submit_key"}:
                continue
            if not payload:
                payload[key] = value
        return topic_id, payload, submit_key

    def _parse_register_inputs(
        self, args: tuple[object, ...], kwargs: Mapping[str, object]
    ) -> tuple[str, dict[str, object], object | None]:
        if len(args) > 3:
            raise ValidationError(
                "registerEntryWithKey expects at most three positional arguments", ErrorContext()
            )
        if not args and "registryTopicId" not in kwargs and "registry_topic_id" not in kwargs:
            raise ValidationError("registryTopicId is required", ErrorContext())
        if args and not isinstance(args[0], str):
            raise ValidationError("registryTopicId must be a string", ErrorContext())
        registry_topic_id_raw = cast(
            str, args[0] if args else kwargs.get("registryTopicId", kwargs.get("registry_topic_id"))
        )
        registry_topic_id = _validate_topic_id(registry_topic_id_raw, "registryTopicId")

        options_payload: dict[str, object] = {}
        submit_key: object | None = None
        if len(args) >= 2:
            options_payload.update(_coerce_mapping(args[1], "options"))
        if len(args) >= 3:
            submit_key = args[2]
        if isinstance(kwargs.get("options"), Mapping):
            options_payload.update(_coerce_mapping(kwargs["options"], "options"))
        if "submitKey" in kwargs:
            submit_key = kwargs["submitKey"]
        if "submit_key" in kwargs:
            submit_key = kwargs["submit_key"]
        for key, value in kwargs.items():
            if key in {
                "registryTopicId",
                "registry_topic_id",
                "options",
                "submitKey",
                "submit_key",
            }:
                continue
            options_payload[key] = value
        return registry_topic_id, options_payload, submit_key

    def _parse_get_registry_inputs(
        self, args: tuple[object, ...], kwargs: Mapping[str, object]
    ) -> tuple[str, Hcs6QueryRegistryOptions]:
        if len(args) > 2:
            raise ValidationError(
                "getRegistry expects at most two positional arguments", ErrorContext()
            )
        if not args and not kwargs.get("topicId") and not kwargs.get("topic_id"):
            raise ValidationError("topicId is required", ErrorContext())
        if args and not isinstance(args[0], str):
            raise ValidationError("topicId must be a string", ErrorContext())
        topic_id_raw = cast(str, args[0] if args else kwargs.get("topicId", kwargs.get("topic_id")))
        topic_id = _validate_topic_id(topic_id_raw, "topicId")

        options_payload: dict[str, object] = {}
        if len(args) >= 2:
            options_payload.update(_coerce_mapping(args[1], "options"))
        for key, value in kwargs.items():
            if key in {"topicId", "topic_id"}:
                continue
            options_payload[key] = value
        options = Hcs6QueryRegistryOptions.model_validate(options_payload)
        return topic_id, options

    create_registry = createRegistry
    submit_message = submitMessage
    submit_message_with_key = submitMessageWithKey
    register_entry = registerEntry
    register_entry_with_key = registerEntryWithKey
    get_registry = getRegistry
    create_hashinal = createHashinal
    inscribe_and_mint = inscribeAndMint
    get_key_type = getKeyType
    get_operator_key = getOperatorKey


class AsyncHcs6Client(AsyncHcsModuleClient):
    """Asynchronous HCS-6 client."""

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
        super().__init__("hcs6", resolved_transport)
        self._sync_client = Hcs6Client(
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

    async def submitMessage(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.submitMessage, *args, **kwargs)

    async def submitMessageWithKey(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.submitMessageWithKey, *args, **kwargs)

    async def registerEntry(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.registerEntry, *args, **kwargs)

    async def registerEntryWithKey(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.registerEntryWithKey, *args, **kwargs)

    async def getRegistry(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.getRegistry, *args, **kwargs)

    async def mint(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.mint, *args, **kwargs)

    async def inscribeAndMint(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.inscribeAndMint, *args, **kwargs)

    async def createHashinal(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.createHashinal, *args, **kwargs)

    async def register(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.register, *args, **kwargs)

    async def getKeyType(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.getKeyType, *args, **kwargs)

    async def getOperatorKey(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.getOperatorKey, *args, **kwargs)

    async def close(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.close, *args, **kwargs)

    create_registry = createRegistry
    submit_message = submitMessage
    submit_message_with_key = submitMessageWithKey
    register_entry = registerEntry
    register_entry_with_key = registerEntryWithKey
    get_registry = getRegistry
    create_hashinal = createHashinal
    inscribe_and_mint = inscribeAndMint
    get_key_type = getKeyType
    get_operator_key = getOperatorKey
