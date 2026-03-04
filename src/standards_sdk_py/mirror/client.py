"""Mirror node sync and async clients with HederaMirrorNode parity methods."""

from __future__ import annotations

import base64
import re
from collections.abc import Mapping
from datetime import datetime
from time import sleep
from urllib.parse import urlparse

from pydantic import ValidationError as PydanticValidationError

from standards_sdk_py.exceptions import ApiError, ErrorContext, ParseError, TransportError
from standards_sdk_py.mirror.models import MirrorTopicMessagesResponse
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.http import SyncHttpTransport
from standards_sdk_py.shared.types import JsonObject, JsonValue, QueryParams

_MIRROR_CAMEL_METHODS = (
    "checkKeyListAccess",
    "configureMirrorNode",
    "configureRetry",
    "getAccountBalance",
    "getAccountMemo",
    "getAccountNfts",
    "getAccountTokens",
    "getBaseUrl",
    "getBlock",
    "getBlocks",
    "getContract",
    "getContractActions",
    "getContractLogs",
    "getContractLogsByContract",
    "getContractResult",
    "getContractResults",
    "getContractResultsByContract",
    "getContractState",
    "getContracts",
    "getHBARPrice",
    "getNetworkFees",
    "getNetworkInfo",
    "getNetworkStake",
    "getNetworkSupply",
    "getNftInfo",
    "getNftsByToken",
    "getOpcodeTraces",
    "getOutstandingTokenAirdrops",
    "getPendingTokenAirdrops",
    "getPublicKey",
    "getScheduleInfo",
    "getScheduledTransactionStatus",
    "getTokenInfo",
    "getTopicFees",
    "getTopicInfo",
    "getTopicMessages",
    "getTopicMessagesByFilter",
    "getTransaction",
    "getTransactionByTimestamp",
    "readSmartContractQuery",
    "requestAccount",
    "validateNFTOwnership",
)

_FIRST_CAP_RE = re.compile("(.)([A-Z][a-z]+)")
_ALL_CAP_RE = re.compile("([a-z0-9])([A-Z])")


def _camel_to_snake(name: str) -> str:
    first_pass = _FIRST_CAP_RE.sub(r"\1_\2", name)
    return _ALL_CAP_RE.sub(r"\1_\2", first_pass).lower()


def _to_query(payload: Mapping[str, object | None]) -> QueryParams | None:
    query: QueryParams = {}
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, bool | int | float | str):
            query[key] = value
        elif isinstance(value, datetime):
            query[key] = value.isoformat()
        else:
            query[key] = str(value)
    return query or None


def _next_path_from_links(raw: JsonObject) -> str | None:
    links = raw.get("links")
    if not isinstance(links, dict):
        return None
    next_link = links.get("next")
    if not isinstance(next_link, str) or not next_link.strip():
        return None
    parsed = urlparse(next_link)
    if parsed.path:
        return f"{parsed.path}{f'?{parsed.query}' if parsed.query else ''}"
    return next_link if next_link.startswith("/") else f"/{next_link.lstrip('/')}"


def _decode_base64_message(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return base64.b64decode(value).decode("utf-8")
    except Exception:
        return None


class MirrorNodeClient:
    """Synchronous mirror node client."""

    def __init__(
        self,
        *,
        config: SdkConfig | None = None,
        transport: SyncHttpTransport | None = None,
    ) -> None:
        self._config = config or SdkConfig.from_env()
        self._transport = transport or SyncHttpTransport(
            base_url=self._config.network.mirror_node_base_url,
        )
        self._max_retries = 5
        self._initial_delay_ms = 2000
        self._max_delay_ms = 30000
        self._backoff_factor = 2.0

    def configure_retry(self, config: JsonObject) -> None:
        retries = config.get("maxRetries")
        initial = config.get("initialDelayMs")
        maximum = config.get("maxDelayMs")
        factor = config.get("backoffFactor")
        if isinstance(retries, int) and retries > 0:
            self._max_retries = retries
        if isinstance(initial, int) and initial > 0:
            self._initial_delay_ms = initial
        if isinstance(maximum, int) and maximum > 0:
            self._max_delay_ms = maximum
        if isinstance(factor, int | float) and factor > 0:
            self._backoff_factor = float(factor)

    def configure_mirror_node(self, config: JsonObject) -> None:
        custom_url = config.get("customUrl")
        if isinstance(custom_url, str) and custom_url.strip():
            self._transport.base_url = custom_url.strip().rstrip("/")
        headers = config.get("headers")
        if isinstance(headers, dict):
            merged = dict(self._transport.headers or {})
            for key, value in headers.items():
                if isinstance(key, str) and isinstance(value, str):
                    merged[key] = value
            self._transport.headers = merged
        api_key = config.get("apiKey")
        if isinstance(api_key, str) and api_key.strip():
            merged = dict(self._transport.headers or {})
            merged["authorization"] = f"Bearer {api_key.strip()}"
            self._transport.headers = merged

    def get_base_url(self) -> str:
        return self._transport.base_url

    def _request_json(self, path: str, *, query: QueryParams | None = None) -> JsonValue:
        delay_ms = self._initial_delay_ms
        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                return self._transport.request_json("GET", path, query=query)
            except (TransportError, ApiError) as exc:
                last_error = exc
                status = exc.context.status_code if isinstance(exc, ApiError) else None
                retryable = isinstance(exc, TransportError) or status in {429, 500, 502, 503, 504}
                if attempt + 1 >= self._max_retries or not retryable:
                    break
                sleep(delay_ms / 1000.0)
                delay_ms = min(int(delay_ms * self._backoff_factor), self._max_delay_ms)
        if last_error is not None:
            raise last_error
        raise ParseError("Mirror request failed without error context", ErrorContext())

    def _collect_items(
        self,
        path: str,
        *,
        query: QueryParams | None,
        item_key: str,
    ) -> list[JsonObject]:
        endpoint: str | None = path
        current_query = query
        items: list[JsonObject] = []
        while endpoint:
            raw = self._request_json(endpoint, query=current_query)
            current_query = None
            if not isinstance(raw, dict):
                break
            payload = raw.get(item_key)
            if isinstance(payload, list):
                items.extend([item for item in payload if isinstance(item, dict)])
            endpoint = _next_path_from_links(raw)
        return items

    def request_account(self, account_id: str) -> JsonObject:
        raw = self._request_json(f"/accounts/{account_id}")
        return raw if isinstance(raw, dict) else {}

    def get_public_key(self, account_id: str) -> str | None:
        key_payload = self.request_account(account_id).get("key")
        if isinstance(key_payload, dict):
            key = key_payload.get("key")
            return key if isinstance(key, str) else None
        return None

    def get_account_memo(self, account_id: str) -> str | None:
        memo = self.request_account(account_id).get("memo")
        return memo if isinstance(memo, str) else None

    def get_topic_info(self, topic_id: str) -> JsonObject:
        raw = self._request_json(f"/topics/{topic_id}")
        return raw if isinstance(raw, dict) else {}

    def get_topic_fees(self, topic_id: str) -> JsonObject | None:
        fees = self.get_topic_info(topic_id).get("custom_fees")
        return fees if isinstance(fees, dict) else None

    def get_hbar_price(self, date: datetime | str) -> float | None:
        stamp = date.isoformat() if isinstance(date, datetime) else str(date)
        raw = self._request_json("/network/exchangerate", query=_to_query({"timestamp": stamp}))
        if not isinstance(raw, dict):
            return None
        current_rate = raw.get("current_rate")
        if not isinstance(current_rate, dict):
            return None
        cents = current_rate.get("cent_equivalent")
        hbar = current_rate.get("hbar_equivalent")
        if isinstance(cents, int | float) and isinstance(hbar, int | float) and hbar != 0:
            return (float(cents) / float(hbar)) / 100.0
        return None

    def get_token_info(self, token_id: str) -> JsonObject | None:
        raw = self._request_json(f"/tokens/{token_id}")
        return raw if isinstance(raw, dict) else None

    def get_topic_messages(
        self,
        topic_id: str,
        *,
        sequence_number: int | str | None = None,
        limit: int | None = None,
        order: str | None = None,
    ) -> MirrorTopicMessagesResponse:
        payload = self._request_json(
            f"/topics/{topic_id}/messages",
            query=_to_query({"sequencenumber": sequence_number, "limit": limit, "order": order}),
        )
        try:
            return MirrorTopicMessagesResponse.model_validate(payload)
        except PydanticValidationError as exc:
            raise ParseError(
                "Failed to validate mirror topic messages response",
                ErrorContext(details={"errors": exc.errors()}),
            ) from exc

    def check_key_list_access(self, key_bytes: bytes | str, user_public_key: str) -> bool:
        key_string = key_bytes if isinstance(key_bytes, str) else key_bytes.hex()
        return user_public_key in key_string

    def get_schedule_info(self, schedule_id: str) -> JsonObject | None:
        raw = self._request_json(f"/schedules/{schedule_id}")
        return raw if isinstance(raw, dict) else None

    def get_scheduled_transaction_status(self, schedule_id: str) -> JsonObject:
        info = self.get_schedule_info(schedule_id) or {}
        executed_timestamp = info.get("executed_timestamp")
        return {
            "executed": isinstance(executed_timestamp, str),
            "executedDate": executed_timestamp,
            "deleted": bool(info.get("deleted")),
        }

    def get_transaction(self, transaction_id_or_hash: str) -> JsonObject | None:
        raw = self._request_json(f"/transactions/{transaction_id_or_hash}")
        txs = raw.get("transactions") if isinstance(raw, dict) else None
        if isinstance(txs, list) and txs and isinstance(txs[0], dict):
            return txs[0]
        return raw if isinstance(raw, dict) else None

    def get_account_balance(self, account_id: str) -> float | None:
        balance_payload = self.request_account(account_id).get("balance")
        if isinstance(balance_payload, dict):
            balance = balance_payload.get("balance")
            if isinstance(balance, int | float):
                return float(balance)
        return None

    def get_topic_messages_by_filter(
        self,
        topic_id: str,
        options: JsonObject | None = None,
    ) -> list[JsonObject] | None:
        opts = options or {}
        sequence_number: int | str | None = None
        sequence_raw = opts.get("sequenceNumber")
        if isinstance(sequence_raw, int | str):
            sequence_number = sequence_raw
        limit: int | None = None
        limit_raw = opts.get("limit")
        if isinstance(limit_raw, int):
            limit = limit_raw
        order: str | None = None
        order_raw = opts.get("order")
        if isinstance(order_raw, str):
            order = order_raw
        response = self.get_topic_messages(
            topic_id,
            sequence_number=sequence_number,
            limit=limit,
            order=order,
        )
        messages: list[JsonObject] = []
        for message in response.messages:
            decoded = _decode_base64_message(message.message)
            messages.append(
                {
                    "consensus_timestamp": message.consensus_timestamp,
                    "sequence_number": message.sequence_number,
                    "running_hash": message.running_hash,
                    "message": decoded if decoded is not None else message.message,
                }
            )
        return messages

    def get_account_tokens(self, account_id: str, limit: int = 100) -> list[JsonObject] | None:
        return self._collect_items(
            f"/accounts/{account_id}/tokens", query=_to_query({"limit": limit}), item_key="tokens"
        )

    def get_transaction_by_timestamp(self, timestamp: str) -> list[JsonObject]:
        raw = self._request_json(
            "/transactions", query=_to_query({"timestamp": timestamp, "limit": 1})
        )
        if isinstance(raw, dict):
            transactions = raw.get("transactions")
            if isinstance(transactions, list):
                return [item for item in transactions if isinstance(item, dict)]
        return []

    def get_account_nfts(
        self, account_id: str, token_id: str | None = None, limit: int = 100
    ) -> list[JsonObject] | None:
        query = _to_query({"limit": limit, "token.id": token_id})
        return self._collect_items(f"/accounts/{account_id}/nfts", query=query, item_key="nfts")

    def validate_nft_ownership(
        self, account_id: str, token_id: str, serial_number: int
    ) -> JsonObject | None:
        nft = self.get_nft_info(token_id, serial_number)
        if not isinstance(nft, dict) or nft.get("account_id") != account_id:
            return None
        return nft

    def read_smart_contract_query(
        self,
        contract_id_or_address: str,
        function_selector: str,
        payer_account_id: str,
        options: JsonObject | None = None,
    ) -> JsonObject | None:
        payload: JsonObject = {
            "block": "latest",
            "data": function_selector,
            "estimate": False,
            "from": payer_account_id,
            "gas": 300000,
            "gasPrice": 0,
            "to": contract_id_or_address,
            "value": 0,
        }
        for key, value in (options or {}).items():
            payload[key] = value
        raw = self._transport.request_json("POST", "/contracts/call", body=payload)
        return raw if isinstance(raw, dict) else None

    def get_outstanding_token_airdrops(
        self, account_id: str, options: JsonObject | None = None
    ) -> list[JsonObject] | None:
        return self._collect_items(
            f"/accounts/{account_id}/airdrops/outstanding",
            query=_to_query(options or {}),
            item_key="airdrops",
        )

    def get_pending_token_airdrops(
        self, account_id: str, options: JsonObject | None = None
    ) -> list[JsonObject] | None:
        return self._collect_items(
            f"/accounts/{account_id}/airdrops/pending",
            query=_to_query(options or {}),
            item_key="airdrops",
        )

    def get_blocks(self, options: JsonObject | None = None) -> list[JsonObject] | None:
        return self._collect_items("/blocks", query=_to_query(options or {}), item_key="blocks")

    def get_block(self, block_number_or_hash: str) -> JsonObject | None:
        raw = self._request_json(f"/blocks/{block_number_or_hash}")
        return raw if isinstance(raw, dict) else None

    def get_contracts(self, options: JsonObject | None = None) -> list[JsonObject] | None:
        return self._collect_items(
            "/contracts", query=_to_query(options or {}), item_key="contracts"
        )

    def get_contract(
        self, contract_id_or_address: str, timestamp: str | None = None
    ) -> JsonObject | None:
        raw = self._request_json(
            f"/contracts/{contract_id_or_address}", query=_to_query({"timestamp": timestamp})
        )
        return raw if isinstance(raw, dict) else None

    def get_contract_results(self, options: JsonObject | None = None) -> list[JsonObject] | None:
        return self._collect_items(
            "/contracts/results", query=_to_query(options or {}), item_key="results"
        )

    def get_contract_result(
        self, transaction_id_or_hash: str, nonce: int | None = None
    ) -> JsonObject | None:
        raw = self._request_json(
            f"/contracts/results/{transaction_id_or_hash}", query=_to_query({"nonce": nonce})
        )
        return raw if isinstance(raw, dict) else None

    def get_contract_results_by_contract(
        self, contract_id_or_address: str, options: JsonObject | None = None
    ) -> list[JsonObject] | None:
        return self._collect_items(
            f"/contracts/{contract_id_or_address}/results",
            query=_to_query(options or {}),
            item_key="results",
        )

    def get_contract_state(
        self, contract_id_or_address: str, options: JsonObject | None = None
    ) -> list[JsonObject] | None:
        return self._collect_items(
            f"/contracts/{contract_id_or_address}/state",
            query=_to_query(options or {}),
            item_key="state",
        )

    def get_contract_actions(
        self, transaction_id_or_hash: str, options: JsonObject | None = None
    ) -> list[JsonObject] | None:
        return self._collect_items(
            f"/contracts/results/{transaction_id_or_hash}/actions",
            query=_to_query(options or {}),
            item_key="actions",
        )

    def get_contract_logs(self, options: JsonObject | None = None) -> list[JsonObject] | None:
        return self._collect_items(
            "/contracts/results/logs", query=_to_query(options or {}), item_key="logs"
        )

    def get_contract_logs_by_contract(
        self, contract_id_or_address: str, options: JsonObject | None = None
    ) -> list[JsonObject] | None:
        return self._collect_items(
            f"/contracts/{contract_id_or_address}/results/logs",
            query=_to_query(options or {}),
            item_key="logs",
        )

    def get_nft_info(self, token_id: str, serial_number: int) -> JsonObject | None:
        raw = self._request_json(f"/tokens/{token_id}/nfts/{serial_number}")
        return raw if isinstance(raw, dict) else None

    def get_nfts_by_token(
        self, token_id: str, options: JsonObject | None = None
    ) -> list[JsonObject] | None:
        return self._collect_items(
            f"/tokens/{token_id}/nfts", query=_to_query(options or {}), item_key="nfts"
        )

    def get_network_info(self) -> JsonObject | None:
        raw = self._request_json("/network/nodes")
        return raw if isinstance(raw, dict) else None

    def get_network_fees(self, timestamp: str | None = None) -> JsonObject | None:
        raw = self._request_json("/network/fees", query=_to_query({"timestamp": timestamp}))
        return raw if isinstance(raw, dict) else None

    def get_network_supply(self, timestamp: str | None = None) -> JsonObject | None:
        raw = self._request_json("/network/supply", query=_to_query({"timestamp": timestamp}))
        return raw if isinstance(raw, dict) else None

    def get_network_stake(self, timestamp: str | None = None) -> JsonObject | None:
        raw = self._request_json("/network/stake", query=_to_query({"timestamp": timestamp}))
        return raw if isinstance(raw, dict) else None

    def get_opcode_traces(
        self, transaction_id_or_hash: str, options: JsonObject | None = None
    ) -> JsonObject | None:
        raw = self._request_json(
            f"/contracts/results/{transaction_id_or_hash}/opcodes",
            query=_to_query(options or {}),
        )
        return raw if isinstance(raw, dict) else None

    def close(self) -> None:
        self._transport.close()


def _install_sync_mirror_aliases() -> None:
    for camel_name in _MIRROR_CAMEL_METHODS:
        snake_name = _camel_to_snake(camel_name)
        if hasattr(MirrorNodeClient, snake_name) and not hasattr(MirrorNodeClient, camel_name):
            setattr(MirrorNodeClient, camel_name, getattr(MirrorNodeClient, snake_name))


_install_sync_mirror_aliases()

HederaMirrorNode = MirrorNodeClient
