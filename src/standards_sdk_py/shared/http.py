"""HTTP transports and JSON response helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from json import JSONDecodeError
from typing import Any
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from standards_sdk_py.exceptions import (
    ApiError,
    AuthError,
    ErrorContext,
    ParseError,
    TransportError,
)
from standards_sdk_py.shared.types import Headers, JsonObject, JsonValue, QueryParams


def _normalize_path(path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    if not path.startswith("/"):
        return f"/{path}"
    return path


def _merge_headers(base: Mapping[str, str] | None, extra: Mapping[str, str] | None) -> Headers:
    merged: Headers = {}
    if base:
        merged.update({k.lower(): v for k, v in base.items()})
    if extra:
        merged.update({k.lower(): v for k, v in extra.items()})
    return merged


def _encode_query(params: QueryParams | None) -> str:
    if not params:
        return ""
    payload = {k: str(v) for k, v in params.items() if v is not None}
    if not payload:
        return ""
    return f"?{urlencode(payload, doseq=True)}"


def _context_from_response(
    response: httpx.Response,
    body: JsonValue | str | None = None,
    details: dict[str, Any] | None = None,
) -> ErrorContext:
    method = response.request.method if response.request else None
    url = str(response.request.url) if response.request else None
    return ErrorContext(
        status_code=response.status_code,
        method=method,
        url=url,
        body=body,
        details=details,
    )


def parse_json_body(response: httpx.Response) -> JsonValue:
    try:
        parsed = response.json()
    except (JSONDecodeError, ValueError) as exc:
        if not response.content or response.content.strip() == b"":
            return None
        raise ParseError(
            "Failed to parse JSON response body",
            ErrorContext(
                status_code=response.status_code,
                method=response.request.method if response.request else None,
                url=str(response.request.url) if response.request else None,
            ),
        ) from exc
    if isinstance(parsed, dict | list | str | int | float | bool) or parsed is None:
        return parsed
    raise ParseError(
        "Unsupported JSON value type in response",
        ErrorContext(
            status_code=response.status_code,
            method=response.request.method if response.request else None,
            url=str(response.request.url) if response.request else None,
        ),
    )


def parse_as_model(payload: JsonValue, model_type: type[BaseModel]) -> BaseModel:
    try:
        return model_type.model_validate(payload)
    except PydanticValidationError as exc:
        raise ParseError(
            f"Failed to validate {model_type.__name__}",
            ErrorContext(details={"errors": exc.errors()}),
        ) from exc


@dataclass(slots=True)
class SyncHttpTransport:
    """Synchronous HTTP transport wrapper with normalized error handling."""

    base_url: str
    headers: Headers | None = None
    timeout_seconds: float = 30.0
    client: httpx.Client | None = None
    _owns_client: bool = field(init=False, repr=False)
    _client: httpx.Client = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._owns_client = self.client is None
        self._client = self.client or httpx.Client(timeout=self.timeout_seconds)

    def request(
        self,
        method: str,
        path: str,
        *,
        query: QueryParams | None = None,
        headers: Headers | None = None,
        body: JsonObject | None = None,
    ) -> httpx.Response:
        target = f"{self.base_url.rstrip('/')}{_normalize_path(path)}{_encode_query(query)}"
        merged_headers = _merge_headers(self.headers, headers)
        try:
            response = self._client.request(
                method=method.upper(),
                url=target,
                headers=merged_headers,
                json=body,
            )
        except httpx.HTTPError as exc:
            raise TransportError(
                "HTTP request failed",
                ErrorContext(method=method.upper(), url=target),
            ) from exc
        if response.status_code in (401, 403):
            payload = parse_json_body(response)
            raise AuthError(
                "Authentication failed",
                _context_from_response(response, body=payload),
            )
        if response.status_code >= 400:
            payload = parse_json_body(response)
            raise ApiError(
                f"API request failed with status {response.status_code}",
                _context_from_response(response, body=payload),
            )
        return response

    def request_json(
        self,
        method: str,
        path: str,
        *,
        query: QueryParams | None = None,
        headers: Headers | None = None,
        body: JsonObject | None = None,
    ) -> JsonValue:
        response = self.request(
            method=method,
            path=path,
            query=query,
            headers=headers,
            body=body,
        )
        return parse_json_body(response)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


@dataclass(slots=True)
class AsyncHttpTransport:
    """Asynchronous HTTP transport wrapper with normalized error handling."""

    base_url: str
    headers: Headers | None = None
    timeout_seconds: float = 30.0
    client: httpx.AsyncClient | None = None
    _owns_client: bool = field(init=False, repr=False)
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._owns_client = self.client is None
        self._client = self.client or httpx.AsyncClient(timeout=self.timeout_seconds)

    async def request(
        self,
        method: str,
        path: str,
        *,
        query: QueryParams | None = None,
        headers: Headers | None = None,
        body: JsonObject | None = None,
    ) -> httpx.Response:
        target = f"{self.base_url.rstrip('/')}{_normalize_path(path)}{_encode_query(query)}"
        merged_headers = _merge_headers(self.headers, headers)
        try:
            response = await self._client.request(
                method=method.upper(),
                url=target,
                headers=merged_headers,
                json=body,
            )
        except httpx.HTTPError as exc:
            raise TransportError(
                "HTTP request failed",
                ErrorContext(method=method.upper(), url=target),
            ) from exc
        if response.status_code in (401, 403):
            payload = parse_json_body(response)
            raise AuthError(
                "Authentication failed",
                _context_from_response(response, body=payload),
            )
        if response.status_code >= 400:
            payload = parse_json_body(response)
            raise ApiError(
                f"API request failed with status {response.status_code}",
                _context_from_response(response, body=payload),
            )
        return response

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        query: QueryParams | None = None,
        headers: Headers | None = None,
        body: JsonObject | None = None,
    ) -> JsonValue:
        response = await self.request(
            method=method,
            path=path,
            query=query,
            headers=headers,
            body=body,
        )
        return parse_json_body(response)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
