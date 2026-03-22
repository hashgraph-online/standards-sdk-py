"""Helpers for Registry Broker demos and scripts."""

from __future__ import annotations

import json
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


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(
        token in lowered
        for token in (
            "api_key",
            "apikey",
            "token",
            "secret",
            "password",
            "private",
            "authorization",
            "signature",
        )
    )


def sanitize_for_logging(value: object, *, _depth: int = 0) -> object:
    """Redact sensitive fields while retaining enough detail for debugging."""
    if _depth >= 4:
        return "<max-depth>"
    if isinstance(value, Mapping):
        sanitized: dict[str, object] = {}
        items = list(value.items())
        for raw_key, raw_val in items[:24]:
            key = str(raw_key)
            if _is_sensitive_key(key):
                sanitized[key] = "<redacted>"
            else:
                sanitized[key] = sanitize_for_logging(raw_val, _depth=_depth + 1)
        if len(items) > 24:
            sanitized["__truncated__"] = f"{len(items) - 24} more keys"
        return sanitized
    if isinstance(value, list):
        sanitized_list = [sanitize_for_logging(entry, _depth=_depth + 1) for entry in value[:24]]
        if len(value) > 24:
            sanitized_list.append(f"... ({len(value) - 24} more items)")
        return sanitized_list
    if isinstance(value, str):
        trimmed = value.strip()
        if len(trimmed) <= 240:
            return trimmed
        return f"{trimmed[:240]}...<truncated>"
    return value


def format_json_preview(value: object, *, max_chars: int = 420) -> str:
    """Serialize sanitized JSON-like values for concise logging."""
    safe_value = sanitize_for_logging(value)
    try:
        text = json.dumps(safe_value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        text = repr(safe_value)
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}...<truncated>"


def format_api_error(error: ApiError) -> str:
    """Format ApiError details with redacted, high-signal body context."""
    status_code = error.context.status_code
    code = error.context.code or "<none>"
    body = error.context.body
    return f"status={status_code} code={code} body={format_json_preview(body)}"
