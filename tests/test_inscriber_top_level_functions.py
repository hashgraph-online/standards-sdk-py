"""Top-level inscriber function parity tests."""

from __future__ import annotations

import types

import pytest

from standards_sdk_py.inscriber import client as inscriber_client


def test_inscriber_function_exports_exist() -> None:
    for name in (
        "generate_quote",
        "get_registry_broker_quote",
        "inscribe",
        "inscribe_via_registry_broker",
        "inscribe_with_signer",
        "retrieve_inscription",
        "wait_for_inscription_confirmation",
    ):
        assert hasattr(inscriber_client, name)


def test_generate_quote_delegates_to_quote_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()

    def _fake_get_quote(input_payload: object, options: object) -> object:
        del input_payload, options
        return sentinel

    monkeypatch.setattr(inscriber_client, "get_registry_broker_quote", _fake_get_quote)
    result = inscriber_client.generate_quote(types.SimpleNamespace(), types.SimpleNamespace())
    assert result is sentinel
