"""HCS-5 client with direct on-chain execution parity."""

# ruff: noqa: N802

from __future__ import annotations

import asyncio
import importlib
from collections.abc import Mapping
from typing import Any, cast

from pydantic import BaseModel

from standards_sdk_py.exceptions import ErrorContext, ValidationError
from standards_sdk_py.hcs5.models import (
    Hcs5CreateHashinalOptions,
    Hcs5MintOptions,
    Hcs5MintResponse,
    build_hcs1_hrl,
)
from standards_sdk_py.inscriber import (
    InscribeViaRegistryBrokerOptions,
    InscriptionInput,
    inscribe,
)
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.hcs_module import AsyncHcsModuleClient, HcsModuleClient
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.types import JsonValue

_DEFAULT_REGISTRY_BROKER_BASE_URL = "https://registry.hashgraphonline.com"


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


class Hcs5Client(HcsModuleClient):
    """Synchronous HCS-5 client."""

    def __init__(
        self,
        transport: SyncHttpTransport | None = None,
        *,
        operator_id: str,
        operator_key: str,
        network: str = "testnet",
    ) -> None:
        config = SdkConfig.from_env()
        resolved_transport = transport or SyncHttpTransport(
            base_url=config.network.registry_broker_base_url or _DEFAULT_REGISTRY_BROKER_BASE_URL,
        )
        super().__init__("hcs5", resolved_transport)

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
        self._initialize_onchain(cleaned_operator_id, cleaned_operator_key)

    def _initialize_onchain(self, operator_id: str, operator_key: str) -> None:
        try:
            hedera = importlib.import_module("hedera")
        except ModuleNotFoundError as exc:
            raise ValidationError(
                "hedera-sdk-py is required for on-chain HCS-5 operations",
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

    def mint(self, *args: object, **kwargs: object) -> JsonValue:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(
                "on-chain operator credentials are not configured", ErrorContext()
            )

        options = Hcs5MintOptions.model_validate(self._parse_single_options(args, kwargs, "mint"))
        if not options.metadata_topic_id:
            return cast(
                JsonValue,
                Hcs5MintResponse(
                    success=False, error="metadataTopicId is required for mint()"
                ).model_dump(by_alias=True, exclude_none=True),
            )
        metadata = build_hcs1_hrl(options.metadata_topic_id)
        tx = self._hedera.TokenMintTransaction().setTokenId(
            self._hedera.TokenId.fromString(options.token_id)
        )
        tx.setMetadata([metadata.encode("utf-8")])
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
                Hcs5MintResponse(success=False, error=str(exc)).model_dump(
                    by_alias=True, exclude_none=True
                ),
            )

        result = Hcs5MintResponse(
            success=True,
            serialNumber=self._extract_serial_number(receipt),
            transactionId=_to_string(getattr(response, "transactionId", None)) or None,
            metadata=metadata,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def createHashinal(self, *args: object, **kwargs: object) -> JsonValue:
        options = Hcs5CreateHashinalOptions.model_validate(
            self._parse_single_options(args, kwargs, "createHashinal")
        )
        if not self._operator_id or not self._operator_key_string:
            raise ValidationError(
                "on-chain operator credentials are not configured", ErrorContext()
            )

        inscription_input = InscriptionInput.model_validate(options.inscription_input)
        inscription_options = dict(options.inscription_options)
        broker_options = InscribeViaRegistryBrokerOptions(
            base_url=str(
                inscription_options.get("baseUrl")
                or inscription_options.get("base_url")
                or _DEFAULT_REGISTRY_BROKER_BASE_URL
            ),
            api_key=cast(
                str | None, inscription_options.get("apiKey") or inscription_options.get("api_key")
            ),
            ledger_api_key=cast(
                str | None,
                inscription_options.get("ledgerApiKey")
                or inscription_options.get("ledger_api_key"),
            ),
            ledger_account_id=self._operator_id,
            ledger_private_key=self._operator_key_string,
            ledger_network=self._network,
            mode="file",
            metadata=cast(dict[str, object] | None, inscription_options.get("metadata")),
            tags=cast(list[str] | None, inscription_options.get("tags")),
            wait_for_confirmation=True,
        )
        inscription = inscribe(inscription_input, broker_options)
        if not inscription.confirmed or not inscription.topic_id:
            return cast(
                JsonValue,
                Hcs5MintResponse(success=False, error="Failed to inscribe content").model_dump(
                    by_alias=True, exclude_none=True
                ),
            )

        return self.mint(
            {
                "tokenId": options.token_id,
                "metadataTopicId": inscription.topic_id,
                "supplyKey": options.supply_key,
                "memo": options.memo,
            }
        )

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

    create_hashinal = createHashinal


class AsyncHcs5Client(AsyncHcsModuleClient):
    """Asynchronous HCS-5 client."""

    def __init__(
        self,
        transport: AsyncHttpTransport | None = None,
        *,
        operator_id: str,
        operator_key: str,
        network: str = "testnet",
    ) -> None:
        config = SdkConfig.from_env()
        resolved_transport = transport or AsyncHttpTransport(
            base_url=config.network.registry_broker_base_url or _DEFAULT_REGISTRY_BROKER_BASE_URL,
        )
        super().__init__("hcs5", resolved_transport)
        self._sync_client = Hcs5Client(
            transport=SyncHttpTransport(
                base_url=resolved_transport.base_url,
                headers=dict(resolved_transport.headers or {}),
            ),
            operator_id=operator_id,
            operator_key=operator_key,
            network=network,
        )

    async def mint(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.mint, *args, **kwargs)

    async def createHashinal(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.createHashinal, *args, **kwargs)

    create_hashinal = createHashinal
