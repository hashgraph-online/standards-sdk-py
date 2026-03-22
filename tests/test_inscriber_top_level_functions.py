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
    def _fake_resolve(input_payload: object, options: object) -> tuple[object, object]:
        del input_payload, options
        return object(), inscriber_client.InscriptionOptions(network="testnet")

    def _fake_inscribe(
        input_payload: object,
        client_config: object,
        options: object,
        existing_client: object | None = None,
    ) -> object:
        del input_payload, client_config, options, existing_client
        return inscriber_client.InscriptionResponse(
            quote=True,
            result={
                "totalCostHbar": "1",
                "validUntil": "",
                "breakdown": {"transfers": []},
            },
        )

    monkeypatch.setattr(inscriber_client, "_resolve_inscriber_invocation", _fake_resolve)
    monkeypatch.setattr(inscriber_client, "_inscribe_with_inscriber", _fake_inscribe)
    result = inscriber_client.generate_quote(types.SimpleNamespace(), types.SimpleNamespace())
    assert isinstance(result, inscriber_client.InscriberQuoteResult)
