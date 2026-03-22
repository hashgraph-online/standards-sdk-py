from __future__ import annotations

import base64
import hashlib
import json

import pytest

from standards_sdk_py.exceptions import ParseError, TransportError, ValidationError
from standards_sdk_py.hcs27 import AsyncHCS27Client, HCS27Client
from standards_sdk_py.hcs27 import client as hcs27_client_module


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


def test_hcs27_validate_checkpoint_message_rejects_tree_size_whitespace() -> None:
    client = _client()
    metadata = _valid_metadata()
    metadata["root"] = {"treeSize": " 1 ", "rootHashB64u": _root_hash_b64u("root")}
    with pytest.raises(
        ValidationError, match="metadata.root.treeSize must be a canonical base-10 string"
    ):
        client.validate_checkpoint_message(
            {"message": {"p": "hcs-27", "op": "register", "metadata": metadata}}
        )


def test_hcs27_validate_checkpoint_message_rejects_300_char_memo() -> None:
    client = _client()
    with pytest.raises(ValidationError, match="message memo must be at most 299 characters"):
        client.validate_checkpoint_message(
            {
                "message": {
                    "p": "hcs-27",
                    "op": "register",
                    "m": "x" * 300,
                    "metadata": _valid_metadata(),
                }
            }
        )


def test_hcs27_canonicalize_json_uses_ecmascript_float_rendering() -> None:
    canonical = hcs27_client_module._canonicalize_json({"value": 333333333.33333329})
    assert canonical == b'{"value":333333333.3333333}'


def test_hcs27_canonicalize_json_sorts_keys_by_utf16_code_units() -> None:
    canonical = hcs27_client_module._canonicalize_json({"𐀀": 1, "\ue000": 2})
    assert canonical == '{"𐀀":1,"\ue000":2}'.encode()


def test_hcs27_hash_leaf_uses_raw_canonical_entry_bytes() -> None:
    client = _client()
    canonical_entry = '{"a":1}'
    assert (
        client.hash_leaf({"canonicalEntry": canonical_entry})
        == hashlib.sha256(b"\x00" + canonical_entry.encode("utf-8")).hexdigest()
    )


def test_hcs27_hash_leaf_unwraps_entry_options_mapping() -> None:
    client = _client()
    entry = {"event": "register", "registry": "example"}
    assert client.hash_leaf({"entry": entry}) == client.hash_leaf(entry)


def test_hcs27_leaf_hash_hex_from_entry_unwraps_entry_options_mapping() -> None:
    client = _client()
    entry = {"event": "register", "registry": "example"}
    assert client.leaf_hash_hex_from_entry({"entry": entry}) == client.leaf_hash_hex_from_entry(
        entry
    )


def test_hcs27_merkle_root_from_entries_unwraps_entries_options_mapping() -> None:
    client = _client()
    entries = [{"event": "register", "registry": "example"}]
    assert client.merkle_root_from_entries({"entries": entries}) == client.merkle_root_from_entries(
        entries
    )


def test_hcs27_merkle_root_from_canonical_entries_unwraps_entries_options_mapping() -> None:
    client = _client()
    entries = ['{"event":"register","registry":"example"}']
    assert client.merkle_root_from_canonical_entries(
        {"entries": entries}
    ) == client.merkle_root_from_canonical_entries(entries)


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


def test_hcs27_resolve_hcs1_reference_reads_raw_cdn_payload() -> None:
    client = _client()
    original = json.dumps(_valid_metadata(), separators=(",", ":")).encode("utf-8")
    client._hrl_transport = type(
        "Transport",
        (),
        {
            "request": staticmethod(
                lambda method, path, query: type(
                    "Response",
                    (),
                    {"content": original},
                )()
            )
        },
    )()

    resolved = client.resolve_h_c_s1_reference("hcs://1/0.0.123")
    assert resolved == original


def test_hcs27_resolve_hcs1_reference_uses_inscription_cdn() -> None:
    client = _client()
    client._hrl_transport = type(
        "Transport",
        (),
        {
            "request": staticmethod(
                lambda method, path, query: type(
                    "Response",
                    (),
                    {"content": b'{"type":"ans-checkpoint-v1"}'},
                )()
            )
        },
    )()
    resolved = client.resolve_h_c_s1_reference("hcs://1/0.0.123")
    assert resolved == b'{"type":"ans-checkpoint-v1"}'


def test_hcs27_accepts_custom_cdn_base_url() -> None:
    client = HCS27Client(cdn_base_url="https://cdn.example.com/hcs")
    assert client._hrl_transport.base_url == "https://cdn.example.com/hcs"


def test_hcs27_publish_checkpoint_validates_overflow_message_before_inscribing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    def _inscribe(*args: object, **kwargs: object) -> object:
        calls.append((args, kwargs))
        raise AssertionError("inscribe should not be called for an invalid overflow message")

    monkeypatch.setattr(hcs27_client_module, "inscribe", _inscribe)

    client = _client()
    client._hedera = object()
    client._hedera_client = object()
    client._operator_id = "0.0.1001"
    client._operator_key_raw = (
        "302e020100300506032b6570042204200123456789abcdef0123456789abcdef"
        "0123456789abcdef0123456789abcdef"
    )

    metadata = {
        "type": "ans-checkpoint-v1",
        "stream": {"registry": "ans", "log_id": "overflow"},
        "log": {
            "alg": "sha-256",
            "leaf": "sha256(jcs(event))-" * 90,
            "merkle": "rfc9162",
        },
        "root": {"treeSize": "1", "rootHashB64u": _root_hash_b64u("overflow")},
    }

    with pytest.raises(ValidationError, match="message memo must be at most 299 characters"):
        client.publish_checkpoint("0.0.123", metadata, "x" * 300)

    assert calls == []


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


def test_hcs27_get_checkpoints_paginates_via_collect_items() -> None:
    client = _client()
    payload_one = {"p": "hcs-27", "op": "register", "metadata": _valid_metadata("stream-a")}
    payload_two = {"p": "hcs-27", "op": "register", "metadata": _valid_metadata("stream-b")}
    encoded_one = base64.b64encode(json.dumps(payload_one).encode("utf-8")).decode("utf-8")
    encoded_two = base64.b64encode(json.dumps(payload_two).encode("utf-8")).decode("utf-8")

    class PaginatedMirror:
        def _collect_items(
            self,
            path: str,
            *,
            query: dict[str, object],
            item_key: str,
        ) -> list[dict[str, object]]:
            assert path == "/topics/0.0.123/messages"
            assert query == {"order": "asc"}
            assert item_key == "messages"
            return [
                {
                    "consensus_timestamp": "1.1",
                    "message": encoded_one,
                    "sequence_number": 1,
                },
                {
                    "consensus_timestamp": "1.2",
                    "message": encoded_two,
                    "sequence_number": 2,
                },
            ]

    client._mirror_client = PaginatedMirror()
    records = client.get_checkpoints("0.0.123")
    assert isinstance(records, list)
    assert [record["sequence"] for record in records] == [1, 2]
    assert [record["effectiveMetadata"]["stream"]["log_id"] for record in records] == [
        "stream-a",
        "stream-b",
    ]


def test_hcs27_get_checkpoints_accepts_single_options_mapping() -> None:
    client = _client()
    metadata = _valid_metadata("stream-a")
    encoded = base64.b64encode(
        json.dumps({"p": "hcs-27", "op": "register", "metadata": metadata}).encode("utf-8")
    ).decode("utf-8")

    class Mirror:
        def get_topic_messages(self, topic_id: str, order: str = "asc") -> dict[str, object]:
            assert topic_id == "0.0.777"
            assert order == "asc"
            return {
                "messages": [
                    {
                        "consensus_timestamp": "1.1",
                        "message": encoded,
                        "sequence_number": 1,
                    }
                ],
                "links": {"next": None},
            }

    client._mirror_client = Mirror()
    records = client.get_checkpoints({"topicId": "0.0.777"})
    assert isinstance(records, list)
    assert records[0]["topicId"] == "0.0.777"


def test_hcs27_get_checkpoints_raises_on_invalid_message_payload() -> None:
    client = _client()

    class Mirror:
        def get_topic_messages(self, topic_id: str, order: str = "asc") -> dict[str, object]:
            _ = (topic_id, order)
            return {
                "messages": [
                    {
                        "consensus_timestamp": "1.1",
                        "message": "%%%not-base64%%%",
                        "sequence_number": 9,
                    }
                ],
                "links": {"next": None},
            }

    client._mirror_client = Mirror()

    with pytest.raises(ParseError, match="failed to decode HCS-27 checkpoint message payload"):
        client.get_checkpoints("0.0.123")


def test_hcs27_publish_checkpoint_uses_utf8_json_submit_bytes() -> None:
    client = HCS27Client()
    submitted: dict[str, object] = {}
    fake_receipt = type("FakeReceipt", (), {"topicSequenceNumber": 7})()

    def get_receipt(_self: object, _hedera_client: object) -> object:
        return fake_receipt

    fake_response = type(
        "FakeResponse",
        (),
        {
            "transactionId": "0.0.123@1.2.3",
            "getReceipt": get_receipt,
        },
    )()

    def set_topic_id(self: object, topic: object) -> object:
        submitted["topic"] = topic
        return self

    def set_message(self: object, message: bytes) -> object:
        submitted["message"] = message
        return self

    def set_transaction_memo(self: object, memo: str) -> object:
        submitted["memo"] = memo
        return self

    def execute(_self: object, _hedera_client: object) -> object:
        return fake_response

    fake_transaction_cls = type(
        "FakeTransaction",
        (),
        {
            "setTopicId": set_topic_id,
            "setMessage": set_message,
            "setTransactionMemo": set_transaction_memo,
            "execute": execute,
        },
    )
    fake_topic_id_cls = type(
        "FakeTopicId",
        (),
        {"fromString": staticmethod(lambda value: value)},
    )

    client._hedera = type(
        "FakeHedera",
        (),
        {
            "TopicId": fake_topic_id_cls,
            "TopicMessageSubmitTransaction": fake_transaction_cls,
        },
    )()
    client._hedera_client = object()
    expected_message = {
        "p": "hcs-27",
        "op": "register",
        "metadata": _valid_metadata(),
        "m": "snowman: \u2603",
    }
    client._prepare_checkpoint_payload = lambda metadata, message_memo: (
        expected_message,
        None,
    )
    client.validateCheckpointMessage = lambda **kwargs: kwargs["message"]["metadata"]

    result = client.publish_checkpoint("0.0.123", _valid_metadata())
    assert result["sequenceNumber"] == 7
    assert submitted["message"] == json.dumps(
        expected_message,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def test_hcs27_publish_checkpoint_accepts_single_options_mapping() -> None:
    client = HCS27Client()
    submitted: dict[str, object] = {}

    def get_receipt(_self: object, _hedera_client: object) -> object:
        return type("FakeReceipt", (), {"topicSequenceNumber": 5})()

    fake_response = type(
        "FakeResponse",
        (),
        {
            "transactionId": "0.0.123@1.2.3",
            "getReceipt": get_receipt,
        },
    )()

    def set_topic_id(self: object, topic: object) -> object:
        submitted["topic"] = topic
        return self

    def set_message(self: object, message: bytes) -> object:
        submitted["message"] = message
        return self

    def set_transaction_memo(self: object, memo: str) -> object:
        submitted["memo"] = memo
        return self

    def execute(_self: object, _hedera_client: object) -> object:
        return fake_response

    client._hedera = type(
        "FakeHedera",
        (),
        {
            "TopicId": type(
                "FakeTopicId",
                (),
                {"fromString": staticmethod(lambda value: value)},
            ),
            "TopicMessageSubmitTransaction": type(
                "FakeTransaction",
                (),
                {
                    "setTopicId": set_topic_id,
                    "setMessage": set_message,
                    "setTransactionMemo": set_transaction_memo,
                    "execute": execute,
                },
            ),
        },
    )()
    client._hedera_client = object()
    client.validateCheckpointMessage = lambda **kwargs: kwargs["message"]["metadata"]

    result = client.publish_checkpoint(
        {
            "topicId": "0.0.123",
            "metadata": _valid_metadata(),
            "messageMemo": "checkpoint memo",
            "transactionMemo": "analytics memo",
        }
    )

    assert result["sequenceNumber"] == 5
    assert submitted["topic"] == "0.0.123"
    assert submitted["memo"] == "analytics memo"


def test_hcs27_publish_metadata_hcs1_requires_inscriber_credentials() -> None:
    client = HCS27Client()
    metadata_bytes = json.dumps(_valid_metadata(), separators=(",", ":")).encode("utf-8")
    with pytest.raises(
        ValidationError,
        match="operator credentials are required for inscriber-backed HCS-1 overflow publication",
    ):
        client._publish_metadata_hcs1(metadata_bytes)


def test_hcs27_publish_metadata_hcs1_uses_configured_inscriber_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = HCS27Client(inscriber_base_url="https://inscriber.example.com/api")
    client._operator_id = "0.0.123"
    client._operator_key_raw = "test-private-key"
    metadata_bytes = json.dumps(_valid_metadata(), separators=(",", ":")).encode("utf-8")
    captured: dict[str, object] = {}

    def fake_inscribe(input_payload: object, options: object) -> object:
        captured["input"] = input_payload
        captured["options"] = options
        return type(
            "Result",
            (),
            {"result": {"topicId": "0.0.500"}, "inscription": None, "confirmed": True},
        )()

    monkeypatch.setattr(hcs27_client_module, "inscribe", fake_inscribe)

    reference, digest = client._publish_metadata_hcs1(metadata_bytes)
    assert reference == "hcs://1/0.0.500"
    assert digest
    assert captured["options"].base_url == "https://inscriber.example.com/api"


def test_async_hcs27_client_accepts_mirror_client() -> None:
    mirror_client = object()
    client = AsyncHCS27Client(mirror_client=mirror_client)
    assert client._sync_client._mirror_client is mirror_client
