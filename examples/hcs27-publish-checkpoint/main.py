"""Draft-aligned HCS-27 live checkpoint example with HRL overflow."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time

from standards_sdk_py.hcs27 import HCS27Client


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return ""


def main() -> None:
    network = (_first_env("HEDERA_NETWORK") or "testnet").lower()
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
        raise RuntimeError(
            "Set HEDERA_ACCOUNT_ID/HEDERA_PRIVATE_KEY or TESTNET_HEDERA_ACCOUNT_ID/"
            "TESTNET_HEDERA_PRIVATE_KEY before running this example."
        )

    client = HCS27Client(operator_id=operator_id, operator_key=operator_key, network=network)
    topic_id = _first_env("HCS27_CHECKPOINT_TOPIC_ID")
    if not topic_id:
        topic = client.create_checkpoint_topic({"ttl": 3600, "useOperatorAsAdmin": True})
        topic_id = str((topic or {}).get("topicId") or "")
        print(json.dumps({"created_topic_id": topic_id}, indent=2))

    inline_metadata = {
        "type": "ans-checkpoint-v1",
        "stream": {"registry": "ans", "log_id": "python-example-inline"},
        "log": {"alg": "sha-256", "leaf": "sha256(jcs(event))", "merkle": "rfc9162"},
        "root": {
            "treeSize": "1",
            "rootHashB64u": base64.urlsafe_b64encode(
                hashlib.sha256(b"python-sdk-hcs27-inline-root").digest()
            )
            .decode("utf-8")
            .rstrip("="),
        },
    }
    inline_result = client.publish_checkpoint(
        topic_id,
        inline_metadata,
        "standards-sdk-py inline checkpoint",
    )

    overflow_metadata = {
        "type": "ans-checkpoint-v1",
        "stream": {"registry": "ans", "log_id": "python-example-overflow"},
        "log": {"alg": "sha-256", "leaf": "sha256(jcs(event))-" * 90, "merkle": "rfc9162"},
        "root": {
            "treeSize": "2",
            "rootHashB64u": base64.urlsafe_b64encode(
                hashlib.sha256(b"python-sdk-hcs27-overflow-root").digest()
            )
            .decode("utf-8")
            .rstrip("="),
        },
    }
    overflow_result = client.publish_checkpoint(
        topic_id,
        overflow_metadata,
        "standards-sdk-py overflow checkpoint",
    )

    records: list[dict[str, object]] = []
    for _attempt in range(20):
        fetched = client.get_checkpoints(topic_id)
        if isinstance(fetched, list) and len(fetched) >= 2:
            records = fetched
            break
        time.sleep(3)
    if len(records) < 2:
        raise RuntimeError("timed out waiting for HCS-27 checkpoints to arrive on the mirror node")

    overflow_reference = ""
    for record in records:
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        metadata_value = message.get("metadata")
        if isinstance(metadata_value, str) and metadata_value.startswith("hcs://1/"):
            overflow_reference = metadata_value
            break
    if not overflow_reference:
        raise RuntimeError("failed to find HCS-1 metadata reference in fetched checkpoints")

    print(
        json.dumps(
            {
                "topic_id": topic_id,
                "inline_result": inline_result,
                "overflow_result": overflow_result,
                "overflow_metadata_reference": overflow_reference,
                "validated_checkpoint_chain": client.validate_checkpoint_chain(records),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
