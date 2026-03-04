"""Common JSON and protocol types."""

from __future__ import annotations

from typing import Any, TypeAlias

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
Headers: TypeAlias = dict[str, str]
QueryParams: TypeAlias = dict[str, str | int | float | bool | None]
AnyDict: TypeAlias = dict[str, Any]
