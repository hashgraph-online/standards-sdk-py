from __future__ import annotations

import base64
import hashlib
import json

import brotli
import pytest

from standards_sdk_py.exceptions import TransportError, ValidationError
from standards_sdk_py.hcs27 import HCS27Client


def _client() -> HCS27Client:
    return HCS27Client()


def _root_hash_b64u(seed: str) -> str:
    return (
        base64.urlsafe_b64encode(hashlib.sha256(seed.encode("utf-8")).digest())
        .decode("utf-8")
        .rstrip("=")
    )


def _valid_metadata(log_id: str = "default") -> dict[str, object]:
    return {
        "type": "ans-checkpoint-v1",
        "stream": {"registry": "ans", "log_id": log_id},
        "log": {"alg": "sha-256", "leaf": "sha256(jcs(event))", "merkle": "rfc9162"},
        "root": {"treeSize": "1", "rootHashB64u": _root_hash_b64u("root")},
    }


def test_hcs27_topic_memo_round_trip() -> None:
    client = _client()
    memo = client.build_topic_memo({"ttl": 3600})
    assert memo == "hcs-27:0:3600:0"
    assert client.parse_topic_memo(memo) == {
        "indexedFlag": 0,
        "ttlSeconds": 3600,
        "topicType": 0,
    }


def test_hcs27_empty_root_and_leaf_vectors() -> None:
    client = _client()
    entry = {
        "event": "register",
        "issued_at": "2026-01-01T00:00:00Z",
        "log_id": "default",
        "payload": {
            "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "uri": "hcs://1/0.0.123",
        },
        "record_id": "registry-native-id",
        "registry": "example",
    }
    assert client.empty_root() == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert (
        client.leaf_hash_hex_from_entry(entry)
        == "a12882925d08570166fe748ebdc16670fc0c69428e2b60ed388b35b52c91d6e2"
    )


def test_hcs27_validate_checkpoint_message_accepts_draft_shape() -> None:
    client = _client()
    metadata = _valid_metadata()
    validated = client.validate_checkpoint_message(
        {"message": {"p": "hcs-27", "op": "register", "metadata": metadata}}
    )
    assert validated == metadata


def test_hcs27_validate_checkpoint_message_rejects_non_canonical_tree_size() -> None:
    client = _client()
    metadata = _valid_metadata()
    metadata["root"] = {"treeSize": "01", "rootHashB64u": _root_hash_b64u("root")}
    with pytest.raises(
        ValidationError, match="metadata.root.treeSize must be a canonical base-10 string"
    ):
        client.validate_checkpoint_message(
            {"message": {"p": "hcs-27", "op": "register", "metadata": metadata}}
        )


def test_hcs27_validate_checkpoint_message_resolves_hcs1_reference() -> None:
    client = _client()
    metadata = _valid_metadata()
    metadata_bytes = json.dumps(metadata, separators=(",", ":")).encode("utf-8")
    digest = (
        base64.urlsafe_b64encode(hashlib.sha256(metadata_bytes).digest())
        .decode("utf-8")
        .rstrip("=")
    )
    validated = client.validate_checkpoint_message(
        {
            "message": {
                "p": "hcs-27",
                "op": "register",
                "metadata": "hcs://1/0.0.123",
                "metadata_digest": {"alg": "sha-256", "b64u": digest},
            },
            "resolver": lambda _: metadata_bytes,
        }
    )
    assert validated == metadata


def test_hcs27_verify_inclusion_and_consistency_proof_objects() -> None:
    client = _client()
    leaf_hex = "a12882925d08570166fe748ebdc16670fc0c69428e2b60ed388b35b52c91d6e2"
    root_b64 = base64.b64encode(bytes.fromhex(leaf_hex)).decode("utf-8")
    assert (
        client.verify_inclusion_proof(
            {
                "proof": {
                    "leafHash": leaf_hex,
                    "leafIndex": "0",
                    "treeSize": "1",
                    "path": [],
                    "rootHash": root_b64,
                    "treeVersion": 1,
                }
            }
        )
        is True
    )
    assert (
        client.verify_consistency_proof(
            {
                "proof": {
                    "oldTreeSize": "0",
                    "newTreeSize": "10",
                    "oldRootHash": "",
                    "newRootHash": "ignored",
                    "consistencyPath": [],
                    "treeVersion": 1,
                }
            }
        )
        is True
    )


def test_hcs27_validate_checkpoint_chain_uses_prev_root_hash_b64u() -> None:
    client = _client()
    root_one = _root_hash_b64u("root-1")
    root_two = _root_hash_b64u("root-2")
    records = [
        {
            "topicId": "0.0.123",
            "sequence": 1,
            "consensusTimestamp": "1.2",
            "message": {"p": "hcs-27", "op": "register", "metadata": _valid_metadata("stream-a")},
            "effectiveMetadata": _valid_metadata("stream-a"),
        },
        {
            "topicId": "0.0.123",
            "sequence": 2,
            "consensusTimestamp": "1.3",
            "message": {"p": "hcs-27", "op": "register", "metadata": _valid_metadata("stream-a")},
            "effectiveMetadata": {
                "type": "ans-checkpoint-v1",
                "stream": {"registry": "ans", "log_id": "stream-a"},
                "log": {"alg": "sha-256", "leaf": "sha256(jcs(event))", "merkle": "rfc9162"},
                "root": {"treeSize": "2", "rootHashB64u": root_two},
                "prev": {"treeSize": "1", "rootHashB64u": root_one},
            },
        },
    ]
    records[0]["effectiveMetadata"]["root"] = {"treeSize": "1", "rootHashB64u": root_one}
    assert client.validate_checkpoint_chain(records) is True


def test_hcs27_resolve_hcs1_reference_decodes_wrapped_payload() -> None:
    client = _client()
    original = json.dumps(_valid_metadata(), separators=(",", ":")).encode("utf-8")
    wrapped = json.dumps(
        {
            "o": 0,
            "c": "data:application/json;base64,"
            + base64.b64encode(brotli.compress(original)).decode("utf-8"),
        }
    ).encode("utf-8")
    encoded = base64.b64encode(wrapped).decode("utf-8")

    class FakeMirrorResponse:
        def __init__(self) -> None:
            self.messages = [
                type(
                    "Msg",
                    (),
                    {
                        "message": encoded,
                        "consensus_timestamp": "1.2",
                        "sequence_number": 1,
                        "model_extra": {},
                    },
                )()
            ]

    client._mirror_client = type(
        "Mirror",
        (),
        {"get_topic_messages": lambda self, topic_id, order="asc": FakeMirrorResponse()},
    )()

    resolved = client.resolve_h_c_s1_reference("hcs://1/0.0.123")
    assert resolved == original


def test_hcs27_get_checkpoints_wraps_mirror_failures() -> None:
    client = _client()
    client._mirror_client = type(
        "Mirror",
        (),
        {
            "get_topic_messages": lambda self, topic_id, order="asc": (_ for _ in ()).throw(
                RuntimeError("mirror unavailable")
            )
        },
    )()

    with pytest.raises(TransportError, match="failed to fetch HCS-27 checkpoints"):
        client.get_checkpoints("0.0.123")
