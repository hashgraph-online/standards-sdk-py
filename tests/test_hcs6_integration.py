import os
import time

import pytest

from standards_sdk_py.hcs6 import HCS6Client, Hcs6Operation, Hcs6RegistryType


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return ""


@pytest.mark.integration
def test_hcs6_end_to_end_testnet() -> None:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("set RUN_INTEGRATION=1 to run live Hedera integration tests")
    if os.getenv("RUN_HCS6_INTEGRATION") not in {"1", "true", "TRUE"}:
        pytest.skip("set RUN_HCS6_INTEGRATION=1 to run HCS-6 integration tests")

    network = (os.getenv("HEDERA_NETWORK") or "testnet").strip().lower()
    if network == "mainnet" and os.getenv("ALLOW_MAINNET_INTEGRATION") != "1":
        pytest.skip(
            "resolved mainnet credentials; set ALLOW_MAINNET_INTEGRATION=1 to permit writes"
        )
    if network != "testnet":
        pytest.skip("this test is testnet-only by default; set HEDERA_NETWORK=testnet")

    operator_id = _first_env("TESTNET_HEDERA_ACCOUNT_ID", "HEDERA_ACCOUNT_ID", "HEDERA_OPERATOR_ID")
    operator_key = _first_env(
        "TESTNET_HEDERA_PRIVATE_KEY",
        "HEDERA_PRIVATE_KEY",
        "HEDERA_OPERATOR_KEY",
    )
    if not operator_id or not operator_key:
        pytest.skip(
            "set TESTNET_HEDERA_ACCOUNT_ID/TESTNET_HEDERA_PRIVATE_KEY "
            "(or HEDERA_ACCOUNT_ID/HEDERA_PRIVATE_KEY) to run this test"
        )

    client = HCS6Client(operator_id=operator_id, operator_key=operator_key, network=network)
    try:
        registry = client.createRegistry({"ttl": 3600, "submitKey": True})
        registry_topic_id = str((registry or {}).get("topicId") or "")
        assert registry_topic_id.startswith("0.0.")

        target = client.createRegistry({"ttl": 3600})
        target_topic_id = str((target or {}).get("topicId") or "")
        assert target_topic_id.startswith("0.0.")

        operation = client.registerEntry(
            registry_topic_id,
            {"targetTopicId": target_topic_id, "memo": "python-sdk hcs6 register"},
        )
        assert int((operation or {}).get("sequenceNumber") or 0) > 0

        time.sleep(8)

        resolved = client.getRegistry(registry_topic_id, {"order": "asc"})
        registry_type = (resolved or {}).get("registryType")
        if isinstance(registry_type, Hcs6RegistryType):
            assert registry_type == Hcs6RegistryType.NON_INDEXED
        else:
            assert int(registry_type) == int(Hcs6RegistryType.NON_INDEXED)
        entries = (resolved or {}).get("entries")
        assert isinstance(entries, list)
        assert len(entries) <= 1
        if entries:
            message = entries[0].get("message") if isinstance(entries[0], dict) else {}
            assert str((message or {}).get("op")) == Hcs6Operation.REGISTER.value
            assert str((message or {}).get("t_id")) == target_topic_id
    finally:
        client.close()
