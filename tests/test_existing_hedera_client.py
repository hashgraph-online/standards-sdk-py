"""Tests for injecting an existing Hedera client into on-chain modules."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from standards_sdk_py.hcs2.client import Hcs2Client
from standards_sdk_py.hcs27.client import Hcs27Client
from standards_sdk_py.shared.http import SyncHttpTransport


def test_hcs2_uses_injected_hedera_client(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, int] = {"for_mainnet": 0, "for_testnet": 0}

    class FakeAccountId:
        def __init__(self, value: str) -> None:
            self._value = value

        def to_string(self) -> str:
            return self._value

    def _account_id_from_string(value: str) -> FakeAccountId:
        return FakeAccountId(value)

    def _private_key_from_string(_: str) -> object:
        return type(
            "PrivateKeyValue",
            (),
            {
                "isECDSA": lambda self: False,
                "getPublicKey": lambda self: type(
                    "PublicKeyValue", (), {"toString": lambda self: "fake-public-key"}
                )(),
            },
        )()

    def _for_mainnet() -> object:
        calls["for_mainnet"] += 1
        return object()

    def _for_testnet() -> object:
        calls["for_testnet"] += 1
        return object()

    fake_account_id_cls = type(
        "AccountId", (), {"fromString": staticmethod(_account_id_from_string)}
    )
    fake_private_key_cls = type(
        "PrivateKey", (), {"fromString": staticmethod(_private_key_from_string)}
    )
    fake_client_cls = type(
        "Client",
        (),
        {
            "forMainnet": staticmethod(_for_mainnet),
            "forTestnet": staticmethod(_for_testnet),
        },
    )

    fake_hedera = SimpleNamespace(
        AccountId=fake_account_id_cls,
        PrivateKey=fake_private_key_cls,
        Client=fake_client_cls,
    )
    monkeypatch.setattr(
        "standards_sdk_py.hcs2.client.importlib",
        SimpleNamespace(import_module=lambda _: fake_hedera),
    )

    injected_client = SimpleNamespace(setOperator=lambda *_: None)
    client = Hcs2Client(
        transport=SyncHttpTransport(base_url="https://example.invalid"),
        operator_id="0.0.1001",
        operator_key="302e020100300506032b6570042204200123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        hedera_client=injected_client,
    )

    assert client._hedera_client is injected_client
    assert calls == {"for_mainnet": 0, "for_testnet": 0}


def test_hcs27_uses_injected_client_network(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client_cls = type(
        "Client",
        (),
        {
            "forMainnet": staticmethod(lambda: object()),
            "forTestnet": staticmethod(lambda: object()),
        },
    )
    fake_hedera = SimpleNamespace(
        AccountId=type("AccountId", (), {"fromString": staticmethod(lambda value: value)}),
        PrivateKey=type("PrivateKey", (), {"fromString": staticmethod(lambda value: value)}),
        Client=fake_client_cls,
    )
    monkeypatch.setattr(
        "standards_sdk_py.hcs27.client.importlib",
        SimpleNamespace(import_module=lambda _: fake_hedera),
    )

    injected_client = SimpleNamespace(network_name="mainnet")
    client = Hcs27Client(
        transport=SyncHttpTransport(base_url="https://example.invalid"),
        hedera_client=injected_client,
        network="testnet",
    )

    assert client._network == "mainnet"
    assert client._mirror_client._transport.base_url == (
        "https://mainnet-public.mirrornode.hedera.com/api/v1"
    )
