"""HCS-27 module."""

# ruff: noqa: N802

from __future__ import annotations

from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.operation_dispatch import (
    AsyncTypedOperationClient,
    OperationOptions,
    TypedOperationClient,
)
from standards_sdk_py.shared.types import JsonValue


class Hcs27Client(TypedOperationClient):
    """Synchronous HCS-27 client."""

    def __init__(self, transport: SyncHttpTransport) -> None:
        super().__init__("hcs27", transport)

    def buildTopicMemo(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("buildTopicMemo", options=options, **kwargs)

    def parseTopicMemo(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("parseTopicMemo", options=options, **kwargs)

    def buildTransactionMemo(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("buildTransactionMemo", options=options, **kwargs)

    def validateCheckpointMessage(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("validateCheckpointMessage", options=options, **kwargs)

    def validateCheckpointChain(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("validateCheckpointChain", options=options, **kwargs)

    def emptyRoot(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("emptyRoot", options=options, **kwargs)

    def hashLeaf(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("hashLeaf", options=options, **kwargs)

    def hashNode(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("hashNode", options=options, **kwargs)

    def merkleRootFromCanonicalEntries(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("merkleRootFromCanonicalEntries", options=options, **kwargs)

    def merkleRootFromEntries(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("merkleRootFromEntries", options=options, **kwargs)

    def leafHashHexFromEntry(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("leafHashHexFromEntry", options=options, **kwargs)

    def verifyInclusionProof(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("verifyInclusionProof", options=options, **kwargs)

    def verifyConsistencyProof(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("verifyConsistencyProof", options=options, **kwargs)

    def createCheckpointTopic(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("createCheckpointTopic", options=options, **kwargs)

    def publishCheckpoint(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("publishCheckpoint", options=options, **kwargs)

    def getCheckpoints(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("getCheckpoints", options=options, **kwargs)

    def resolveHCS1Reference(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("resolveHCS1Reference", options=options, **kwargs)

    build_topic_memo = buildTopicMemo
    parse_topic_memo = parseTopicMemo
    build_transaction_memo = buildTransactionMemo
    validate_checkpoint_message = validateCheckpointMessage
    validate_checkpoint_chain = validateCheckpointChain
    empty_root = emptyRoot
    hash_leaf = hashLeaf
    hash_node = hashNode
    merkle_root_from_canonical_entries = merkleRootFromCanonicalEntries
    merkle_root_from_entries = merkleRootFromEntries
    leaf_hash_hex_from_entry = leafHashHexFromEntry
    verify_inclusion_proof = verifyInclusionProof
    verify_consistency_proof = verifyConsistencyProof
    create_checkpoint_topic = createCheckpointTopic
    publish_checkpoint = publishCheckpoint
    get_checkpoints = getCheckpoints
    resolve_h_c_s1_reference = resolveHCS1Reference


class AsyncHcs27Client(AsyncTypedOperationClient):
    """Asynchronous HCS-27 client."""

    def __init__(self, transport: AsyncHttpTransport) -> None:
        super().__init__("hcs27", transport)

    async def buildTopicMemo(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("buildTopicMemo", options=options, **kwargs)

    async def parseTopicMemo(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("parseTopicMemo", options=options, **kwargs)

    async def buildTransactionMemo(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("buildTransactionMemo", options=options, **kwargs)

    async def validateCheckpointMessage(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("validateCheckpointMessage", options=options, **kwargs)

    async def validateCheckpointChain(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("validateCheckpointChain", options=options, **kwargs)

    async def emptyRoot(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("emptyRoot", options=options, **kwargs)

    async def hashLeaf(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("hashLeaf", options=options, **kwargs)

    async def hashNode(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("hashNode", options=options, **kwargs)

    async def merkleRootFromCanonicalEntries(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("merkleRootFromCanonicalEntries", options=options, **kwargs)

    async def merkleRootFromEntries(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("merkleRootFromEntries", options=options, **kwargs)

    async def leafHashHexFromEntry(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("leafHashHexFromEntry", options=options, **kwargs)

    async def verifyInclusionProof(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("verifyInclusionProof", options=options, **kwargs)

    async def verifyConsistencyProof(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("verifyConsistencyProof", options=options, **kwargs)

    async def createCheckpointTopic(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("createCheckpointTopic", options=options, **kwargs)

    async def publishCheckpoint(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("publishCheckpoint", options=options, **kwargs)

    async def getCheckpoints(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("getCheckpoints", options=options, **kwargs)

    async def resolveHCS1Reference(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("resolveHCS1Reference", options=options, **kwargs)

    build_topic_memo = buildTopicMemo
    parse_topic_memo = parseTopicMemo
    build_transaction_memo = buildTransactionMemo
    validate_checkpoint_message = validateCheckpointMessage
    validate_checkpoint_chain = validateCheckpointChain
    empty_root = emptyRoot
    hash_leaf = hashLeaf
    hash_node = hashNode
    merkle_root_from_canonical_entries = merkleRootFromCanonicalEntries
    merkle_root_from_entries = merkleRootFromEntries
    leaf_hash_hex_from_entry = leafHashHexFromEntry
    verify_inclusion_proof = verifyInclusionProof
    verify_consistency_proof = verifyConsistencyProof
    create_checkpoint_topic = createCheckpointTopic
    publish_checkpoint = publishCheckpoint
    get_checkpoints = getCheckpoints
    resolve_h_c_s1_reference = resolveHCS1Reference


HCS27Client = Hcs27Client
AsyncHCS27Client = AsyncHcs27Client

__all__ = [
    "AsyncHCS27Client",
    "AsyncHcs27Client",
    "HCS27Client",
    "Hcs27Client",
]
