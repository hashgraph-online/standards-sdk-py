"""Generic HCS module client scaffolding with parity method dispatch."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.types import JsonObject, JsonValue, QueryParams

_HTTP_GET_PREFIXES = (
    "get",
    "list",
    "fetch",
    "resolve",
    "validate",
    "check",
    "search",
    "is",
    "has",
)


def _camel_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _to_json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, bytes | bytearray):
        return bytes(value).hex()
    if isinstance(value, dict):
        payload: JsonObject = {}
        for key, item in value.items():
            payload[str(key)] = _to_json_value(item)
        return payload
    if isinstance(value, list | tuple | set):
        return [_to_json_value(item) for item in value]
    return str(value)


def _infer_method(operation_name: str) -> str:
    return "GET" if operation_name.startswith(_HTTP_GET_PREFIXES) else "POST"


def _to_query_value(value: object) -> str | int | float | bool | None:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    return str(value)


def _build_query(args: tuple[object, ...], kwargs: dict[str, object]) -> QueryParams | None:
    payload: QueryParams = {}
    if len(args) == 1 and isinstance(args[0], dict):
        for key, value in cast(dict[str, object], args[0]).items():
            payload[key] = _to_query_value(value)
    elif args:
        for index, value in enumerate(args):
            payload[f"arg{index}"] = _to_query_value(value)
    for key, value in kwargs.items():
        payload[key] = _to_query_value(value)
    return payload or None


def _build_body(args: tuple[object, ...], kwargs: dict[str, object]) -> JsonObject | None:
    if len(args) == 1 and isinstance(args[0], dict) and not kwargs:
        return cast(JsonObject, _to_json_value(args[0]))
    payload: JsonObject = {}
    if args:
        payload["args"] = _to_json_value(list(args))
    for key, value in kwargs.items():
        payload[key] = _to_json_value(value)
    return payload or None


@dataclass(slots=True)
class HcsModuleClient:
    """Synchronous HCS module HTTP client."""

    standard: str
    transport: SyncHttpTransport

    def call(
        self,
        path: str,
        *,
        method: str = "GET",
        query: QueryParams | None = None,
        body: JsonObject | None = None,
    ) -> JsonValue:
        prefix = f"/{self.standard}"
        return self.transport.request_json(method, f"{prefix}{path}", query=query, body=body)

    def invoke_operation(self, operation_name: str, *args: object, **kwargs: object) -> JsonValue:
        method = _infer_method(operation_name)
        path = f"/{operation_name}"
        if method == "GET":
            return self.call(path, method=method, query=_build_query(args, dict(kwargs)))
        return self.call(path, method=method, body=_build_body(args, dict(kwargs)))


@dataclass(slots=True)
class AsyncHcsModuleClient:
    """Asynchronous HCS module HTTP client."""

    standard: str
    transport: AsyncHttpTransport

    async def call(
        self,
        path: str,
        *,
        method: str = "GET",
        query: QueryParams | None = None,
        body: JsonObject | None = None,
    ) -> JsonValue:
        prefix = f"/{self.standard}"
        return await self.transport.request_json(method, f"{prefix}{path}", query=query, body=body)

    async def invoke_operation(
        self, operation_name: str, *args: object, **kwargs: object
    ) -> JsonValue:
        method = _infer_method(operation_name)
        path = f"/{operation_name}"
        if method == "GET":
            return await self.call(path, method=method, query=_build_query(args, dict(kwargs)))
        return await self.call(path, method=method, body=_build_body(args, dict(kwargs)))


def _make_sync_operation(name: str) -> Callable[..., JsonValue]:
    def _method(self: HcsModuleClient, *args: object, **kwargs: object) -> JsonValue:
        return self.invoke_operation(name, *args, **kwargs)

    _method.__name__ = name
    return _method


def _make_async_operation(name: str) -> Callable[..., Any]:
    async def _method(self: AsyncHcsModuleClient, *args: object, **kwargs: object) -> JsonValue:
        return await self.invoke_operation(name, *args, **kwargs)

    _method.__name__ = name
    return _method


def register_hcs_methods(
    sync_cls: type[HcsModuleClient],
    async_cls: type[AsyncHcsModuleClient],
    methods: tuple[str, ...],
) -> None:
    for method in sorted(set(methods)):
        if not hasattr(sync_cls, method):
            setattr(sync_cls, method, _make_sync_operation(method))
        snake_name = _camel_to_snake(method)
        if snake_name != method and not hasattr(sync_cls, snake_name):
            setattr(sync_cls, snake_name, _make_sync_operation(method))

        if not hasattr(async_cls, method):
            setattr(async_cls, method, _make_async_operation(method))
        if snake_name != method and not hasattr(async_cls, snake_name):
            setattr(async_cls, snake_name, _make_async_operation(method))
