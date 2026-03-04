"""HCS-11 module."""

# ruff: noqa: N802

from __future__ import annotations

from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.operation_dispatch import (
    AsyncTypedOperationClient,
    OperationOptions,
    TypedOperationClient,
)
from standards_sdk_py.shared.types import JsonValue


class Hcs11Client(TypedOperationClient):
    """Synchronous HCS-11 client."""

    def __init__(self, transport: SyncHttpTransport) -> None:
        super().__init__("hcs11", transport)

    def createAIAgentProfile(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("createAIAgentProfile", options=options, **kwargs)

    def createAndInscribeProfile(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("createAndInscribeProfile", options=options, **kwargs)

    def createMCPServerProfile(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("createMCPServerProfile", options=options, **kwargs)

    def createPersonalProfile(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("createPersonalProfile", options=options, **kwargs)

    def fetchProfileByAccountId(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("fetchProfileByAccountId", options=options, **kwargs)

    def getAgentTypeFromMetadata(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("getAgentTypeFromMetadata", options=options, **kwargs)

    def getCapabilitiesFromTags(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("getCapabilitiesFromTags", options=options, **kwargs)

    def getClient(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("getClient", options=options, **kwargs)

    def getOperatorId(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("getOperatorId", options=options, **kwargs)

    def initializeOperator(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("initializeOperator", options=options, **kwargs)

    def inscribeImage(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("inscribeImage", options=options, **kwargs)

    def inscribeProfile(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("inscribeProfile", options=options, **kwargs)

    def parseProfileFromString(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("parseProfileFromString", options=options, **kwargs)

    def profileToJSONString(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("profileToJSONString", options=options, **kwargs)

    def setProfileForAccountMemo(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("setProfileForAccountMemo", options=options, **kwargs)

    def updateAccountMemoWithProfile(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("updateAccountMemoWithProfile", options=options, **kwargs)

    def validateProfile(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("validateProfile", options=options, **kwargs)

    create_a_i_agent_profile = createAIAgentProfile
    create_and_inscribe_profile = createAndInscribeProfile
    create_m_c_p_server_profile = createMCPServerProfile
    create_personal_profile = createPersonalProfile
    fetch_profile_by_account_id = fetchProfileByAccountId
    get_agent_type_from_metadata = getAgentTypeFromMetadata
    get_capabilities_from_tags = getCapabilitiesFromTags
    get_client = getClient
    get_operator_id = getOperatorId
    initialize_operator = initializeOperator
    inscribe_image = inscribeImage
    inscribe_profile = inscribeProfile
    parse_profile_from_string = parseProfileFromString
    profile_to_j_s_o_n_string = profileToJSONString
    set_profile_for_account_memo = setProfileForAccountMemo
    update_account_memo_with_profile = updateAccountMemoWithProfile
    validate_profile = validateProfile


class AsyncHcs11Client(AsyncTypedOperationClient):
    """Asynchronous HCS-11 client."""

    def __init__(self, transport: AsyncHttpTransport) -> None:
        super().__init__("hcs11", transport)

    async def createAIAgentProfile(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("createAIAgentProfile", options=options, **kwargs)

    async def createAndInscribeProfile(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("createAndInscribeProfile", options=options, **kwargs)

    async def createMCPServerProfile(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("createMCPServerProfile", options=options, **kwargs)

    async def createPersonalProfile(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("createPersonalProfile", options=options, **kwargs)

    async def fetchProfileByAccountId(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("fetchProfileByAccountId", options=options, **kwargs)

    async def getAgentTypeFromMetadata(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("getAgentTypeFromMetadata", options=options, **kwargs)

    async def getCapabilitiesFromTags(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("getCapabilitiesFromTags", options=options, **kwargs)

    async def getClient(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("getClient", options=options, **kwargs)

    async def getOperatorId(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("getOperatorId", options=options, **kwargs)

    async def initializeOperator(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("initializeOperator", options=options, **kwargs)

    async def inscribeImage(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("inscribeImage", options=options, **kwargs)

    async def inscribeProfile(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("inscribeProfile", options=options, **kwargs)

    async def parseProfileFromString(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("parseProfileFromString", options=options, **kwargs)

    async def profileToJSONString(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("profileToJSONString", options=options, **kwargs)

    async def setProfileForAccountMemo(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("setProfileForAccountMemo", options=options, **kwargs)

    async def updateAccountMemoWithProfile(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("updateAccountMemoWithProfile", options=options, **kwargs)

    async def validateProfile(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("validateProfile", options=options, **kwargs)

    create_a_i_agent_profile = createAIAgentProfile
    create_and_inscribe_profile = createAndInscribeProfile
    create_m_c_p_server_profile = createMCPServerProfile
    create_personal_profile = createPersonalProfile
    fetch_profile_by_account_id = fetchProfileByAccountId
    get_agent_type_from_metadata = getAgentTypeFromMetadata
    get_capabilities_from_tags = getCapabilitiesFromTags
    get_client = getClient
    get_operator_id = getOperatorId
    initialize_operator = initializeOperator
    inscribe_image = inscribeImage
    inscribe_profile = inscribeProfile
    parse_profile_from_string = parseProfileFromString
    profile_to_j_s_o_n_string = profileToJSONString
    set_profile_for_account_memo = setProfileForAccountMemo
    update_account_memo_with_profile = updateAccountMemoWithProfile
    validate_profile = validateProfile


HCS11Client = Hcs11Client
AsyncHCS11Client = AsyncHcs11Client

__all__ = [
    "AsyncHCS11Client",
    "AsyncHcs11Client",
    "HCS11Client",
    "Hcs11Client",
]
