"""Typed dispatch helpers for HTTP-backed HCS module clients."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel

from standards_sdk_py.exceptions import ErrorContext, ValidationError
from standards_sdk_py.shared.hcs_module import AsyncHcsModuleClient, HcsModuleClient
from standards_sdk_py.shared.types import JsonValue

OperationOptions = Mapping[str, object] | BaseModel | None


def _coerce_invoke_args(
    options: OperationOptions,
    kwargs: dict[str, object],
) -> tuple[tuple[object, ...], dict[str, object]]:
    if options is None:
        return (), kwargs
    if kwargs:
        raise ValidationError(
            "pass either options or keyword arguments, not both",
            ErrorContext(),
        )
    if isinstance(options, BaseModel):
        return (options.model_dump(by_alias=True, exclude_none=True),), {}
    if isinstance(options, Mapping):
        return ({str(k): v for k, v in options.items()},), {}
    raise ValidationError(
        "options must be a mapping or pydantic model",
        ErrorContext(details={"type": type(options).__name__}),
    )


class TypedOperationClient(HcsModuleClient):
    """Synchronous typed wrapper for HTTP-backed operation dispatch."""

    def _invoke_typed(
        self,
        operation_name: str,
        options: OperationOptions = None,
        **kwargs: object,
    ) -> JsonValue:
        args, invoke_kwargs = _coerce_invoke_args(options, dict(kwargs))
        return self.invoke_operation(operation_name, *args, **invoke_kwargs)


class AsyncTypedOperationClient(AsyncHcsModuleClient):
    """Asynchronous typed wrapper for HTTP-backed operation dispatch."""

    async def _invoke_typed(
        self,
        operation_name: str,
        options: OperationOptions = None,
        **kwargs: object,
    ) -> JsonValue:
        args, invoke_kwargs = _coerce_invoke_args(options, dict(kwargs))
        return await self.invoke_operation(operation_name, *args, **invoke_kwargs)
