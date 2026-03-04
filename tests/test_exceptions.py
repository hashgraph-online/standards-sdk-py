"""Tests for exception hierarchy and SdkError formatting."""

import pytest

from standards_sdk_py.exceptions import (
    ApiError,
    AuthError,
    ErrorContext,
    ParseError,
    SdkError,
    TransportError,
    ValidationError,
)


def test_sdk_error_str_without_code() -> None:
    err = SdkError("something went wrong")
    assert str(err) == "something went wrong"
    assert err.message == "something went wrong"
    assert err.context.code is None


def test_sdk_error_str_with_code() -> None:
    ctx = ErrorContext(code="ERR_INVALID")
    err = SdkError("bad input", context=ctx)
    assert str(err) == "ERR_INVALID: bad input"


def test_sdk_error_default_context() -> None:
    err = SdkError("no ctx")
    assert err.context is not None
    assert err.context.status_code is None
    assert err.context.method is None
    assert err.context.url is None
    assert err.context.body is None
    assert err.context.details is None


def test_error_context_all_fields() -> None:
    ctx = ErrorContext(
        code="E1",
        status_code=500,
        method="POST",
        url="https://api.test",
        body={"key": "val"},
        details={"extra": "info"},
    )
    assert ctx.code == "E1"
    assert ctx.status_code == 500
    assert ctx.method == "POST"
    assert ctx.url == "https://api.test"
    assert ctx.body == {"key": "val"}
    assert ctx.details == {"extra": "info"}


def test_subclass_hierarchy() -> None:
    """Ensure each error subclass is an instance of SdkError and Exception."""
    for cls in (ValidationError, TransportError, ApiError, ParseError, AuthError):
        err = cls("test")
        assert isinstance(err, SdkError)
        assert isinstance(err, Exception)
        assert str(err) == "test"


def test_validation_error_with_context() -> None:
    err = ValidationError("invalid", ErrorContext(code="V1"))
    assert str(err) == "V1: invalid"


def test_errors_catchable_by_base() -> None:
    with pytest.raises(SdkError):
        raise TransportError("network down")
