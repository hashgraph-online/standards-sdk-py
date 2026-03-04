import os
import time

import pytest

from standards_sdk_py.hcs2 import HCS2Client, Hcs2Operation, Hcs2RegistryType


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return ""


@pytest.mark.integration
def test_hcs2_end_to_end_testnet() -> None:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("set RUN_INTEGRATION=1 to run live Hedera integration tests")
    if os.getenv("RUN_HCS2_INTEGRATION") not in {"1", "true", "TRUE"}:
        pytest.skip("set RUN_HCS2_INTEGRATION=1 to run HCS-2 integration tests")

    resolved_network = (os.getenv("HEDERA_NETWORK") or "testnet").strip().lower()
    if resolved_network == "mainnet" and os.getenv("ALLOW_MAINNET_INTEGRATION") != "1":
        pytest.skip(
            "resolved mainnet credentials; set ALLOW_MAINNET_INTEGRATION=1 to permit "
            "live mainnet writes"
        )
    if resolved_network != "testnet":
        pytest.skip("this test is testnet-only by default; set HEDERA_NETWORK=testnet")

    operator_id = _first_env(
        "TESTNET_HEDERA_ACCOUNT_ID",
        "HEDERA_ACCOUNT_ID",
        "HEDERA_OPERATOR_ID",
    )
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

    client = HCS2Client(
        operator_id=operator_id,
        operator_key=operator_key,
        network=resolved_network,
    )
    ttl_seconds = 3600

    try:
        registry_result = client.createRegistry(
            {
                "registryType": Hcs2RegistryType.INDEXED,
                "ttl": ttl_seconds,
                "adminKey": True,
                "submitKey": True,
            }
        )
        registry_topic_id = str((registry_result or {}).get("topicId") or "")
        assert registry_topic_id.startswith("0.0.")

        target_topic_result = client.createRegistry(
            {"registryType": Hcs2RegistryType.NON_INDEXED, "ttl": ttl_seconds}
        )
        target_topic_id = str((target_topic_result or {}).get("topicId") or "")
        assert target_topic_id.startswith("0.0.")

        register_result = client.registerEntry(
            registry_topic_id,
            {
                "targetTopicId": target_topic_id,
                "metadata": f"hcs://1/{target_topic_id}",
                "memo": "python-sdk register",
            },
            "hcs-2",
        )
        sequence_number = int((register_result or {}).get("sequenceNumber") or 0)
        assert sequence_number > 0

        time.sleep(8)

        update_result = client.updateEntry(
            registry_topic_id,
            {
                "uid": str(sequence_number),
                "targetTopicId": target_topic_id,
                "metadata": f"hcs://1/{target_topic_id}@updated",
                "memo": "python-sdk update",
            },
        )
        assert int((update_result or {}).get("sequenceNumber") or 0) > 0

        delete_result = client.deleteEntry(
            registry_topic_id,
            {"uid": str(sequence_number), "memo": "python-sdk delete"},
        )
        assert int((delete_result or {}).get("sequenceNumber") or 0) > 0

        time.sleep(10)

        registry = client.getRegistry(registry_topic_id, {"order": "asc"})
        registry_type = (registry or {}).get("registryType")
        if isinstance(registry_type, Hcs2RegistryType):
            assert registry_type == Hcs2RegistryType.INDEXED
        else:
            assert int(registry_type) == int(Hcs2RegistryType.INDEXED)
        assert int((registry or {}).get("ttl") or 0) == ttl_seconds

        entries = (registry or {}).get("entries")
        assert isinstance(entries, list)
        assert len(entries) >= 3

        operations = {
            str((entry.get("message") or {}).get("op"))
            for entry in entries
            if isinstance(entry, dict)
        }
        assert Hcs2Operation.REGISTER.value in operations
        assert Hcs2Operation.UPDATE.value in operations
        assert Hcs2Operation.DELETE.value in operations
    finally:
        client.close()
