import os
import time

import pytest

from standards_sdk_py.hcs7 import HCS7Client


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return ""


@pytest.mark.integration
def test_hcs7_end_to_end_testnet() -> None:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("set RUN_INTEGRATION=1 to run live Hedera integration tests")
    if os.getenv("RUN_HCS7_INTEGRATION") not in {"1", "true", "TRUE"}:
        pytest.skip("set RUN_HCS7_INTEGRATION=1 to run HCS-7 integration tests")

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

    client = HCS7Client(operator_id=operator_id, operator_key=operator_key, network=network)
    try:
        registry = client.createRegistry({"ttl": 3600, "submitKey": True})
        registry_topic_id = str((registry or {}).get("topicId") or "")
        assert registry_topic_id.startswith("0.0.")

        metadata_topic = client.createRegistry({"ttl": 3600})
        metadata_topic_id = str((metadata_topic or {}).get("topicId") or "")
        assert metadata_topic_id.startswith("0.0.")

        wasm_topic = client.createRegistry({"ttl": 3600})
        wasm_topic_id = str((wasm_topic or {}).get("topicId") or "")
        assert wasm_topic_id.startswith("0.0.")

        config_result = client.registerConfig(
            {
                "registryTopicId": registry_topic_id,
                "type": "wasm",
                "wasm": {
                    "wasmTopicId": wasm_topic_id,
                    "inputType": {"stateData": {"x": "number"}},
                    "outputType": {"type": "string", "format": "topic-id"},
                },
                "memo": "python-sdk hcs7 register-config",
            }
        )
        assert int((config_result or {}).get("sequenceNumber") or 0) > 0

        metadata_result = client.registerMetadata(
            {
                "registryTopicId": registry_topic_id,
                "metadataTopicId": metadata_topic_id,
                "weight": 1,
                "tags": ["python", "integration"],
                "data": {"source": "standards-sdk-py"},
                "memo": "python-sdk hcs7 register",
            }
        )
        assert int((metadata_result or {}).get("sequenceNumber") or 0) > 0

        time.sleep(8)

        resolved = client.getRegistry(registry_topic_id, {"order": "asc"})
        entries = (resolved or {}).get("entries")
        assert isinstance(entries, list)
        assert len(entries) >= 2
        operations = {
            str((entry.get("message") or {}).get("op"))
            for entry in entries
            if isinstance(entry, dict)
        }
        assert "register-config" in operations
        assert "register" in operations
    finally:
        client.close()
