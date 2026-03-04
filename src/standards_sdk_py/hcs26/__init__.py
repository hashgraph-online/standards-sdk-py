"""HCS-26 module."""

# ruff: noqa: N802

from __future__ import annotations

from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.operation_dispatch import (
    AsyncTypedOperationClient,
    OperationOptions,
    TypedOperationClient,
)
from standards_sdk_py.shared.types import JsonValue


class Hcs26Client(TypedOperationClient):
    """Synchronous HCS-26 client."""

    def __init__(self, transport: SyncHttpTransport) -> None:
        super().__init__("hcs26", transport)

    def buildTopicMemo(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("buildTopicMemo", options=options, **kwargs)

    def parseTopicMemo(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("parseTopicMemo", options=options, **kwargs)

    def buildTransactionMemo(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("buildTransactionMemo", options=options, **kwargs)

    def parseTransactionMemo(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("parseTransactionMemo", options=options, **kwargs)

    def resolveDiscoveryRecord(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("resolveDiscoveryRecord", options=options, **kwargs)

    def listVersionRegisters(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("listVersionRegisters", options=options, **kwargs)

    def getLatestVersionRegister(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("getLatestVersionRegister", options=options, **kwargs)

    def resolveManifest(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("resolveManifest", options=options, **kwargs)

    def verifyVersionRegisterMatchesManifest(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("verifyVersionRegisterMatchesManifest", options=options, **kwargs)

    def resolveSkill(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("resolveSkill", options=options, **kwargs)

    def listSkillVersions(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("listSkillVersions", options=options, **kwargs)

    def resolveSkillVersion(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("resolveSkillVersion", options=options, **kwargs)

    def createRegistryBrokerVerificationProvider(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed(
            "createRegistryBrokerVerificationProvider", options=options, **kwargs
        )

    build_topic_memo = buildTopicMemo
    parse_topic_memo = parseTopicMemo
    build_transaction_memo = buildTransactionMemo
    parse_transaction_memo = parseTransactionMemo
    resolve_discovery_record = resolveDiscoveryRecord
    list_version_registers = listVersionRegisters
    get_latest_version_register = getLatestVersionRegister
    resolve_manifest = resolveManifest
    verify_version_register_matches_manifest = verifyVersionRegisterMatchesManifest
    resolve_skill = resolveSkill
    list_skill_versions = listSkillVersions
    resolve_skill_version = resolveSkillVersion
    create_registry_broker_verification_provider = createRegistryBrokerVerificationProvider


class AsyncHcs26Client(AsyncTypedOperationClient):
    """Asynchronous HCS-26 client."""

    def __init__(self, transport: AsyncHttpTransport) -> None:
        super().__init__("hcs26", transport)

    async def buildTopicMemo(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("buildTopicMemo", options=options, **kwargs)

    async def parseTopicMemo(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("parseTopicMemo", options=options, **kwargs)

    async def buildTransactionMemo(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("buildTransactionMemo", options=options, **kwargs)

    async def parseTransactionMemo(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("parseTransactionMemo", options=options, **kwargs)

    async def resolveDiscoveryRecord(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("resolveDiscoveryRecord", options=options, **kwargs)

    async def listVersionRegisters(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("listVersionRegisters", options=options, **kwargs)

    async def getLatestVersionRegister(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("getLatestVersionRegister", options=options, **kwargs)

    async def resolveManifest(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("resolveManifest", options=options, **kwargs)

    async def verifyVersionRegisterMatchesManifest(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed(
            "verifyVersionRegisterMatchesManifest", options=options, **kwargs
        )

    async def resolveSkill(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("resolveSkill", options=options, **kwargs)

    async def listSkillVersions(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("listSkillVersions", options=options, **kwargs)

    async def resolveSkillVersion(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("resolveSkillVersion", options=options, **kwargs)

    async def createRegistryBrokerVerificationProvider(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed(
            "createRegistryBrokerVerificationProvider", options=options, **kwargs
        )

    build_topic_memo = buildTopicMemo
    parse_topic_memo = parseTopicMemo
    build_transaction_memo = buildTransactionMemo
    parse_transaction_memo = parseTransactionMemo
    resolve_discovery_record = resolveDiscoveryRecord
    list_version_registers = listVersionRegisters
    get_latest_version_register = getLatestVersionRegister
    resolve_manifest = resolveManifest
    verify_version_register_matches_manifest = verifyVersionRegisterMatchesManifest
    resolve_skill = resolveSkill
    list_skill_versions = listSkillVersions
    resolve_skill_version = resolveSkillVersion
    create_registry_broker_verification_provider = createRegistryBrokerVerificationProvider


HCS26Client = Hcs26Client
AsyncHCS26Client = AsyncHcs26Client

__all__ = [
    "AsyncHCS26Client",
    "AsyncHcs26Client",
    "HCS26Client",
    "Hcs26Client",
]
