"""Typed request and response models for HCS-27."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Hcs27Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True, strict=True)


class Hcs27StreamId(_Hcs27Model):
    registry: str
    log_id: str = Field(alias="log_id")


class Hcs27LogProfile(_Hcs27Model):
    alg: str
    leaf: str
    merkle: str


class Hcs27RootCommitment(_Hcs27Model):
    tree_size: str = Field(alias="treeSize")
    root_hash_b64u: str = Field(alias="rootHashB64u")


class Hcs27PreviousCommitment(_Hcs27Model):
    tree_size: str = Field(alias="treeSize")
    root_hash_b64u: str = Field(alias="rootHashB64u")


class Hcs27Signature(_Hcs27Model):
    alg: str
    kid: str
    b64u: str


class Hcs27CheckpointMetadata(_Hcs27Model):
    type: Literal["ans-checkpoint-v1"] = "ans-checkpoint-v1"
    stream: Hcs27StreamId
    log: Hcs27LogProfile
    root: Hcs27RootCommitment
    prev: Hcs27PreviousCommitment | None = None
    sig: Hcs27Signature | None = None


class Hcs27MetadataDigest(_Hcs27Model):
    alg: str
    b64u: str


class Hcs27CheckpointMessage(_Hcs27Model):
    p: Literal["hcs-27"] = "hcs-27"
    op: Literal["register"] = "register"
    metadata: dict[str, object] | str
    metadata_digest: Hcs27MetadataDigest | None = Field(default=None, alias="metadata_digest")
    m: str | None = None


class Hcs27CreateCheckpointTopicOptions(_Hcs27Model):
    ttl: int = 86400
    admin_key: str | bool | None = Field(default=None, alias="adminKey")
    submit_key: str | bool | None = Field(default=None, alias="submitKey")
    use_operator_as_admin: bool = Field(default=False, alias="useOperatorAsAdmin")
    use_operator_as_submit: bool = Field(default=False, alias="useOperatorAsSubmit")
    transaction_memo: str | None = Field(default=None, alias="transactionMemo")


class Hcs27CreateCheckpointTopicResult(_Hcs27Model):
    topic_id: str = Field(alias="topicId")
    transaction_id: str = Field(alias="transactionId")


class Hcs27PublishCheckpointResult(_Hcs27Model):
    transaction_id: str = Field(alias="transactionId")
    sequence_number: int = Field(alias="sequenceNumber")


class Hcs27TopicMemo(_Hcs27Model):
    indexed_flag: int = Field(alias="indexedFlag")
    ttl_seconds: int = Field(alias="ttlSeconds")
    topic_type: int = Field(alias="topicType")


class Hcs27CheckpointRecord(_Hcs27Model):
    topic_id: str = Field(alias="topicId")
    sequence: int
    consensus_timestamp: str = Field(alias="consensusTimestamp")
    payer: str | None = None
    message: Hcs27CheckpointMessage
    effective_metadata: Hcs27CheckpointMetadata = Field(alias="effectiveMetadata")


class Hcs27InclusionProof(_Hcs27Model):
    leaf_hash: str = Field(alias="leafHash")
    leaf_index: str = Field(alias="leafIndex")
    tree_size: str = Field(alias="treeSize")
    path: list[str]
    root_hash: str = Field(alias="rootHash")
    root_signature: str | None = Field(default=None, alias="rootSignature")
    tree_version: int = Field(alias="treeVersion")


class Hcs27ConsistencyProof(_Hcs27Model):
    old_tree_size: str = Field(alias="oldTreeSize")
    new_tree_size: str = Field(alias="newTreeSize")
    old_root_hash: str = Field(alias="oldRootHash")
    new_root_hash: str = Field(alias="newRootHash")
    consistency_path: list[str] = Field(alias="consistencyPath")
    tree_version: int = Field(alias="treeVersion")
