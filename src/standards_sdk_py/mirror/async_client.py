"""Asynchronous mirror node client."""

from __future__ import annotations

import asyncio

from pydantic import ValidationError as PydanticValidationError

from standards_sdk_py.exceptions import ApiError, ErrorContext, ParseError, TransportError
from standards_sdk_py.mirror.client import (
    _MIRROR_CAMEL_METHODS,
    MirrorNodeClient,
    _camel_to_snake,
    _to_query,
)
from standards_sdk_py.mirror.models import MirrorTopicMessagesResponse
from standards_sdk_py.shared.config import SdkConfig
from standards_sdk_py.shared.http import AsyncHttpTransport
from standards_sdk_py.shared.types import JsonObject, JsonValue, QueryParams


class AsyncMirrorNodeClient:
    """Asynchronous mirror node client."""

    def __init__(
        self,
        *,
        config: SdkConfig | None = None,
        transport: AsyncHttpTransport | None = None,
    ) -> None:
        self._config = config or SdkConfig.from_env()
        self._transport = transport or AsyncHttpTransport(
            base_url=self._config.network.mirror_node_base_url,
        )
        self._sync_delegate = MirrorNodeClient(config=self._config)
        self._max_retries = 5
        self._initial_delay_ms = 2000
        self._max_delay_ms = 30000
        self._backoff_factor = 2.0

    def configure_retry(self, config: JsonObject) -> None:
        self._sync_delegate.configure_retry(config)
        self._max_retries = self._sync_delegate._max_retries
        self._initial_delay_ms = self._sync_delegate._initial_delay_ms
        self._max_delay_ms = self._sync_delegate._max_delay_ms
        self._backoff_factor = self._sync_delegate._backoff_factor

    def configure_mirror_node(self, config: JsonObject) -> None:
        self._sync_delegate.configure_mirror_node(config)
        custom_url = config.get("customUrl")
        if isinstance(custom_url, str) and custom_url.strip():
            self._transport.base_url = custom_url.strip().rstrip("/")

    def get_base_url(self) -> str:
        return self._transport.base_url

    async def _request_json(self, path: str, *, query: QueryParams | None = None) -> JsonValue:
        delay_ms = self._initial_delay_ms
        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                return await self._transport.request_json("GET", path, query=query)
            except (TransportError, ApiError) as exc:
                last_error = exc
                status = exc.context.status_code if isinstance(exc, ApiError) else None
                retryable = isinstance(exc, TransportError) or status in {429, 500, 502, 503, 504}
                if attempt + 1 >= self._max_retries or not retryable:
                    break
                await asyncio.sleep(delay_ms / 1000.0)
                delay_ms = min(int(delay_ms * self._backoff_factor), self._max_delay_ms)
        if last_error is not None:
            raise last_error
        raise ParseError("Mirror request failed without error context", ErrorContext())

    async def get_topic_messages(
        self,
        topic_id: str,
        *,
        sequence_number: int | str | None = None,
        limit: int | None = None,
        order: str | None = None,
    ) -> MirrorTopicMessagesResponse:
        payload = await self._request_json(
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

    async def close(self) -> None:
        await self._transport.close()


def _install_async_passthroughs() -> None:
    excluded = {
        "configure_retry",
        "configure_mirror_node",
        "get_base_url",
        "get_topic_messages",
        "close",
    }
    for attr in dir(MirrorNodeClient):
        if attr.startswith("_") or attr in excluded:
            continue
        snake_attr = _camel_to_snake(attr)
        if hasattr(AsyncMirrorNodeClient, snake_attr):
            continue
        candidate = getattr(MirrorNodeClient, attr)
        if not callable(candidate) or hasattr(AsyncMirrorNodeClient, attr):
            continue

        async def _wrapper(
            self: AsyncMirrorNodeClient,
            *args: object,
            _name: str = attr,
            **kwargs: object,
        ) -> JsonValue:
            fn = getattr(self._sync_delegate, _name)
            return await asyncio.to_thread(fn, *args, **kwargs)

        _wrapper.__name__ = attr
        setattr(AsyncMirrorNodeClient, attr, _wrapper)


def _install_mirror_aliases() -> None:
    for camel_name in _MIRROR_CAMEL_METHODS:
        snake_name = _camel_to_snake(camel_name)
        if hasattr(AsyncMirrorNodeClient, snake_name) and not hasattr(
            AsyncMirrorNodeClient, camel_name
        ):
            setattr(AsyncMirrorNodeClient, camel_name, getattr(AsyncMirrorNodeClient, snake_name))


_install_async_passthroughs()
_install_mirror_aliases()

AsyncHederaMirrorNode = AsyncMirrorNodeClient
