from __future__ import annotations

import base64
import hashlib
import os
import time

import pytest

from standards_sdk_py.hcs27 import HCS27Client


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return ""


@pytest.mark.integration
def test_hcs27_end_to_end_testnet() -> None:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("set RUN_INTEGRATION=1 to run live Hedera integration tests")
    if os.getenv("RUN_HCS27_INTEGRATION") not in {"1", "true", "TRUE"}:
        pytest.skip("set RUN_HCS27_INTEGRATION=1 to run HCS-27 integration tests")

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

    client = HCS27Client(operator_id=operator_id, operator_key=operator_key, network=network)
    topic = client.create_checkpoint_topic({"ttl": 3600})
    topic_id = str((topic or {}).get("topicId") or "")
    assert topic_id.startswith("0.0.")

    root_one = (
        base64.urlsafe_b64encode(hashlib.sha256(b"python-hcs27-root-1").digest())
        .decode("utf-8")
        .rstrip("=")
    )
    root_two = (
        base64.urlsafe_b64encode(hashlib.sha256(b"python-hcs27-root-2").digest())
        .decode("utf-8")
        .rstrip("=")
    )

    result_one = client.publish_checkpoint(
        topic_id,
        {
            "type": "ans-checkpoint-v1",
            "stream": {"registry": "ans", "log_id": "python-e2e"},
            "log": {"alg": "sha-256", "leaf": "sha256(jcs(event))", "merkle": "rfc9162"},
            "root": {"treeSize": "1", "rootHashB64u": root_one},
        },
        "python hcs27 checkpoint 1",
    )
    assert int((result_one or {}).get("sequenceNumber") or 0) > 0

    result_two = client.publish_checkpoint(
        topic_id,
        {
            "type": "ans-checkpoint-v1",
            "stream": {"registry": "ans", "log_id": "python-e2e"},
            "log": {"alg": "sha-256", "leaf": "sha256(jcs(event))", "merkle": "rfc9162"},
            "root": {"treeSize": "2", "rootHashB64u": root_two},
            "prev": {"treeSize": "1", "rootHashB64u": root_one},
        },
        "python hcs27 checkpoint 2",
    )
    assert int((result_two or {}).get("sequenceNumber") or 0) > 0

    time.sleep(8)

    checkpoints = client.get_checkpoints(topic_id)
    assert isinstance(checkpoints, list)
    assert len(checkpoints) >= 2
    assert client.validate_checkpoint_chain(checkpoints) is True
