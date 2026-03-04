"""Canonical SDK exception hierarchy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ErrorContext:
    """Structured error context attached to SDK exceptions."""

    code: str | None = None
    status_code: int | None = None
    method: str | None = None
    url: str | None = None
    body: Any | None = None
    details: dict[str, Any] | None = None


class SdkError(Exception):
    """Base class for all standards-sdk-py exceptions."""

    def __init__(self, message: str, context: ErrorContext | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or ErrorContext()

    def __str__(self) -> str:
        if self.context.code:
            return f"{self.context.code}: {self.message}"
        return self.message


class ValidationError(SdkError):
    """Input or model validation failure."""


class TransportError(SdkError):
    """Network transport failure before application-level response parsing."""


class ApiError(SdkError):
    """HTTP API failure with status/body context."""


class ParseError(SdkError):
    """Response parse or schema parse failure."""


class AuthError(SdkError):
    """Authentication or authorization failure."""
