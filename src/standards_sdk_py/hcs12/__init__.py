"""HCS-12 module."""

# ruff: noqa: N802

from __future__ import annotations

from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.operation_dispatch import (
    AsyncTypedOperationClient,
    OperationOptions,
    TypedOperationClient,
)
from standards_sdk_py.shared.types import JsonValue


class Hcs12Client(TypedOperationClient):
    """Synchronous HCS-12 client."""

    def __init__(self, transport: SyncHttpTransport) -> None:
        super().__init__("hcs12", transport)

    def addActionToAssembly(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("addActionToAssembly", options=options, **kwargs)

    def addBlockToAssembly(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("addBlockToAssembly", options=options, **kwargs)

    def createAssembly(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("createAssembly", options=options, **kwargs)

    def createAssemblyTopic(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("createAssemblyTopic", options=options, **kwargs)

    def createRegistryTopic(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("createRegistryTopic", options=options, **kwargs)

    def getClient(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("getClient", options=options, **kwargs)

    def getOperatorAccountId(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("getOperatorAccountId", options=options, **kwargs)

    def getOperatorPrivateKey(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("getOperatorPrivateKey", options=options, **kwargs)

    def initializeRegistries(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("initializeRegistries", options=options, **kwargs)

    def inscribeFile(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("inscribeFile", options=options, **kwargs)

    def registerAction(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("registerAction", options=options, **kwargs)

    def registerAssemblyDirect(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("registerAssemblyDirect", options=options, **kwargs)

    def registerBlock(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("registerBlock", options=options, **kwargs)

    def submitMessage(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("submitMessage", options=options, **kwargs)

    def updateAssembly(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("updateAssembly", options=options, **kwargs)

    add_action_to_assembly = addActionToAssembly
    add_block_to_assembly = addBlockToAssembly
    create_assembly = createAssembly
    create_assembly_topic = createAssemblyTopic
    create_registry_topic = createRegistryTopic
    get_client = getClient
    get_operator_account_id = getOperatorAccountId
    get_operator_private_key = getOperatorPrivateKey
    initialize_registries = initializeRegistries
    inscribe_file = inscribeFile
    register_action = registerAction
    register_assembly_direct = registerAssemblyDirect
    register_block = registerBlock
    submit_message = submitMessage
    update_assembly = updateAssembly


class AsyncHcs12Client(AsyncTypedOperationClient):
    """Asynchronous HCS-12 client."""

    def __init__(self, transport: AsyncHttpTransport) -> None:
        super().__init__("hcs12", transport)

    async def addActionToAssembly(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("addActionToAssembly", options=options, **kwargs)

    async def addBlockToAssembly(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("addBlockToAssembly", options=options, **kwargs)

    async def createAssembly(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("createAssembly", options=options, **kwargs)

    async def createAssemblyTopic(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("createAssemblyTopic", options=options, **kwargs)

    async def createRegistryTopic(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("createRegistryTopic", options=options, **kwargs)

    async def getClient(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("getClient", options=options, **kwargs)

    async def getOperatorAccountId(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("getOperatorAccountId", options=options, **kwargs)

    async def getOperatorPrivateKey(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("getOperatorPrivateKey", options=options, **kwargs)

    async def initializeRegistries(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("initializeRegistries", options=options, **kwargs)

    async def inscribeFile(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("inscribeFile", options=options, **kwargs)

    async def registerAction(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("registerAction", options=options, **kwargs)

    async def registerAssemblyDirect(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("registerAssemblyDirect", options=options, **kwargs)

    async def registerBlock(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("registerBlock", options=options, **kwargs)

    async def submitMessage(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("submitMessage", options=options, **kwargs)

    async def updateAssembly(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("updateAssembly", options=options, **kwargs)

    add_action_to_assembly = addActionToAssembly
    add_block_to_assembly = addBlockToAssembly
    create_assembly = createAssembly
    create_assembly_topic = createAssemblyTopic
    create_registry_topic = createRegistryTopic
    get_client = getClient
    get_operator_account_id = getOperatorAccountId
    get_operator_private_key = getOperatorPrivateKey
    initialize_registries = initializeRegistries
    inscribe_file = inscribeFile
    register_action = registerAction
    register_assembly_direct = registerAssemblyDirect
    register_block = registerBlock
    submit_message = submitMessage
    update_assembly = updateAssembly


HCS12Client = Hcs12Client
AsyncHCS12Client = AsyncHcs12Client

__all__ = [
    "AsyncHCS12Client",
    "AsyncHcs12Client",
    "HCS12Client",
    "Hcs12Client",
]
