"""Draft-aligned HCS-27 checkpoint helper example."""

from __future__ import annotations

import base64
import hashlib
import json

from standards_sdk_py.hcs27 import HCS27Client


def main() -> None:
    client = HCS27Client()
    metadata = {
        "type": "ans-checkpoint-v1",
        "stream": {"registry": "ans", "log_id": "example-log"},
        "log": {"alg": "sha-256", "leaf": "sha256(jcs(event))", "merkle": "rfc9162"},
        "root": {
            "treeSize": "2",
            "rootHashB64u": base64.urlsafe_b64encode(
                hashlib.sha256(b"python-sdk-hcs27-example").digest()
            )
            .decode("utf-8")
            .rstrip("="),
        },
    }

    checkpoint = {"p": "hcs-27", "op": "register", "metadata": metadata}

    print(
        json.dumps(
            {
                "topic_memo": client.build_topic_memo({"ttl": 3600}),
                "transaction_memo": client.build_transaction_memo(),
                "leaf_hash_hex": client.leaf_hash_hex_from_entry(
                    {"registry": "ans", "record_id": "example-record"}
                ),
                "merkle_root_hex": client.merkle_root_from_entries(
                    [
                        {"registry": "ans", "record_id": "example-record-1"},
                        {"registry": "ans", "record_id": "example-record-2"},
                    ]
                ),
                "validated_metadata": client.validate_checkpoint_message({"message": checkpoint}),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
