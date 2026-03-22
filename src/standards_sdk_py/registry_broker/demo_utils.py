"""Helpers for Registry Broker demos and scripts."""

from __future__ import annotations

from collections.abc import Mapping

from standards_sdk_py import ApiError


def parse_positive_int(value: str | None, fallback: int) -> int:
    """Parse a positive integer with fallback semantics."""
    if value is None:
        return fallback
    trimmed = value.strip()
    if not trimmed:
        return fallback
    parsed = int(trimmed)
    if parsed <= 0:
        raise ValueError("Expected a positive integer")
    return parsed


def parse_positive_float(value: str | None, fallback: float) -> float:
    """Parse a positive float with fallback semantics."""
    if value is None:
        return fallback
    trimmed = value.strip()
    if not trimmed:
        return fallback
    parsed = float(trimmed)
    if parsed <= 0:
        raise ValueError("Expected a positive float")
    return parsed


def parse_non_negative_int(value: str | None) -> int | None:
    """Parse a non-negative integer or return None for empty/invalid values."""
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    try:
        parsed = int(trimmed)
    except ValueError:
        return None
    if parsed < 0:
        return None
    return parsed


def summarize_mapping_keys(payload: Mapping[object, object]) -> str:
    """Return a compact, deterministic view of mapping keys."""
    keys = sorted(str(key) for key in payload.keys())
    if not keys:
        return "<none>"
    if len(keys) <= 8:
        return ",".join(keys)
    return f"{','.join(keys[:8])},...(+{len(keys) - 8})"


def format_api_error(error: ApiError) -> str:
    """Format ApiError details without logging raw body contents."""
    status_code = error.context.status_code
    code = error.context.code or "<none>"
    body = error.context.body

    if isinstance(body, Mapping):
        body_summary = f"bodyKeys={summarize_mapping_keys(body)}"
    elif isinstance(body, list):
        body_summary = f"bodyType=list bodyLength={len(body)}"
    elif isinstance(body, str):
        trimmed = body.strip()
        body_summary = f"bodyType=str bodyLength={len(trimmed)}"
    elif body is None:
        body_summary = "bodyType=none"
    else:
        body_summary = f"bodyType={type(body).__name__}"

    return f"status={status_code} code={code} {body_summary}"
