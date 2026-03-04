"""HCS-15 client with direct on-chain execution parity."""

# ruff: noqa: N802

from __future__ import annotations

import asyncio
import importlib
from collections.abc import Mapping
from typing import Any, cast

from pydantic import BaseModel

from standards_sdk_py.exceptions import ErrorContext, ParseError, TransportError, ValidationError
from standards_sdk_py.hcs15.models import (
    Hcs15BaseAccountCreateResult,
    Hcs15CreateBaseAccountOptions,
    Hcs15CreatePetalAccountOptions,
    Hcs15PetalAccountCreateResult,
)
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.hcs_module import AsyncHcsModuleClient, HcsModuleClient
from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.types import JsonValue

_DEFAULT_REGISTRY_BROKER_BASE_URL = "https://registry.hashgraphonline.com"
_BASE_CREATE_MEMO = "hcs-15:op:base_create"
_PETAL_CREATE_MEMO = "hcs-15:op:petal_create"
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


def _normalize_evm_address(value: object | None) -> str:
    rendered = _to_string(value).strip()
    if not rendered:
        return ""
    if rendered.startswith(("0x", "0X")):
        return rendered
    return f"0x{rendered}"


class Hcs15Client(HcsModuleClient):
    """Synchronous HCS-15 client."""

    def __init__(
        self,
        transport: SyncHttpTransport | None = None,
        *,
        operator_id: str,
        operator_key: str,
        network: str = "testnet",
        key_type: str | None = None,
    ) -> None:
        config = SdkConfig.from_env()
        resolved_transport = transport or SyncHttpTransport(
            base_url=config.network.registry_broker_base_url or _DEFAULT_REGISTRY_BROKER_BASE_URL,
        )
        super().__init__("hcs15", resolved_transport)

        self._network = _normalize_network(network)
        self._hedera: Any | None = None
        self._hedera_client: Any | None = None
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
                "hedera-sdk-py is required for on-chain HCS-15 operations",
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

        normalized_key_type = _clean(key_type).lower()
        if normalized_key_type in {"ed25519", "ecdsa"}:
            self._key_type = normalized_key_type
        elif callable(getattr(private_key, "isECDSA", None)) and bool(private_key.isECDSA()):
            self._key_type = "ecdsa"
        else:
            self._key_type = "ed25519"

    def createBaseAccount(self, *args: object, **kwargs: object) -> JsonValue:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(_ONCHAIN_CREDS_ERROR, ErrorContext())
        options = Hcs15CreateBaseAccountOptions.model_validate(
            self._parse_single_options(args, kwargs, "createBaseAccount")
        )

        try:
            private_key = self._hedera.PrivateKey.generateECDSA()
            public_key = private_key.getPublicKey()
        except Exception as exc:
            raise TransportError(
                "failed to generate ECDSA keypair",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc

        initial_balance = options.initial_balance if options.initial_balance > 0 else 10.0
        tx = (
            self._hedera.AccountCreateTransaction()
            .setKey(public_key)
            .setAlias(public_key.toEvmAddress())
            .setInitialBalance(self._hedera.Hbar(initial_balance))
            .setTransactionMemo(_clean(options.transaction_memo) or _BASE_CREATE_MEMO)
        )
        if options.max_automatic_token_associations is not None:
            tx.setMaxAutomaticTokenAssociations(int(options.max_automatic_token_associations))
        if _clean(options.account_memo):
            tx.setAccountMemo(_clean(options.account_memo))

        try:
            response = tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to create HCS-15 base account",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc

        account_id = _to_string(getattr(receipt, "accountId", None))
        if not account_id:
            raise ParseError("HCS-15 BASE_ACCOUNT_CREATE_FAILED", ErrorContext())

        result = Hcs15BaseAccountCreateResult(
            accountId=account_id,
            privateKey=_to_string(private_key.toString()),
            privateKeyHex=_to_string(private_key.toStringRaw()),
            publicKey=_to_string(public_key.toString()),
            evmAddress=_normalize_evm_address(public_key.toEvmAddress()),
            transactionId=_to_string(getattr(response, "transactionId", None)) or None,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def createPetalAccount(self, *args: object, **kwargs: object) -> JsonValue:
        if self._hedera is None or self._hedera_client is None:
            raise ValidationError(_ONCHAIN_CREDS_ERROR, ErrorContext())
        options = Hcs15CreatePetalAccountOptions.model_validate(
            self._parse_single_options(args, kwargs, "createPetalAccount")
        )

        base_private_key = _clean(options.base_private_key)
        if not base_private_key:
            raise ValidationError("basePrivateKey is required", ErrorContext())
        try:
            parsed_base_key = self._hedera.PrivateKey.fromStringECDSA(base_private_key)
        except Exception as exc:
            raise ValidationError(
                "invalid base private key",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc
        public_key = parsed_base_key.getPublicKey()

        initial_balance = options.initial_balance if options.initial_balance > 0 else 1.0
        tx = (
            self._hedera.AccountCreateTransaction()
            .setKey(public_key)
            .setInitialBalance(self._hedera.Hbar(initial_balance))
            .setTransactionMemo(_clean(options.transaction_memo) or _PETAL_CREATE_MEMO)
        )
        if options.max_automatic_token_associations is not None:
            tx.setMaxAutomaticTokenAssociations(int(options.max_automatic_token_associations))
        if _clean(options.account_memo):
            tx.setAccountMemo(_clean(options.account_memo))

        try:
            response = tx.execute(self._hedera_client)
            receipt = response.getReceipt(self._hedera_client)
        except Exception as exc:
            raise TransportError(
                "failed to create HCS-15 petal account",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc

        account_id = _to_string(getattr(receipt, "accountId", None))
        if not account_id:
            raise ParseError("HCS-15 PETAL_ACCOUNT_CREATE_FAILED", ErrorContext())

        result = Hcs15PetalAccountCreateResult(
            accountId=account_id,
            transactionId=_to_string(getattr(response, "transactionId", None)) or None,
        )
        return cast(JsonValue, result.model_dump(by_alias=True, exclude_none=True))

    def getKeyType(self, *args: object, **kwargs: object) -> JsonValue:
        _ = (args, kwargs)
        if self._key_type is None:
            raise ParseError("operator key type is unavailable", ErrorContext())
        return self._key_type

    def close(self, *args: object, **kwargs: object) -> JsonValue:
        _ = (args, kwargs)
        try:
            close_fn = getattr(self._hedera_client, "close", None)
            if self._hedera_client is not None and callable(close_fn):
                self._hedera_client.close()
        except Exception as exc:
            raise TransportError(
                "failed to close HCS-15 Hedera client",
                ErrorContext(details={"reason": str(exc)}),
            ) from exc
        return None

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

    create_base_account = createBaseAccount
    create_petal_account = createPetalAccount
    get_key_type = getKeyType


class AsyncHcs15Client(AsyncHcsModuleClient):
    """Asynchronous HCS-15 client."""

    def __init__(
        self,
        transport: AsyncHttpTransport | None = None,
        *,
        operator_id: str,
        operator_key: str,
        network: str = "testnet",
        key_type: str | None = None,
    ) -> None:
        config = SdkConfig.from_env()
        resolved_transport = transport or AsyncHttpTransport(
            base_url=config.network.registry_broker_base_url or _DEFAULT_REGISTRY_BROKER_BASE_URL,
        )
        super().__init__("hcs15", resolved_transport)
        self._sync_client = Hcs15Client(
            transport=SyncHttpTransport(
                base_url=resolved_transport.base_url,
                headers=dict(resolved_transport.headers or {}),
            ),
            operator_id=operator_id,
            operator_key=operator_key,
            network=network,
            key_type=key_type,
        )

    async def createBaseAccount(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.createBaseAccount, *args, **kwargs)

    async def createPetalAccount(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.createPetalAccount, *args, **kwargs)

    async def getKeyType(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.getKeyType, *args, **kwargs)

    async def close(self, *args: object, **kwargs: object) -> JsonValue:
        return await asyncio.to_thread(self._sync_client.close, *args, **kwargs)

    create_base_account = createBaseAccount
    create_petal_account = createPetalAccount
    get_key_type = getKeyType
