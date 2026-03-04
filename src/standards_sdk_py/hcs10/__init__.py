"""HCS-10 module."""

# ruff: noqa: N802

from __future__ import annotations

from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.operation_dispatch import (
    AsyncTypedOperationClient,
    OperationOptions,
    TypedOperationClient,
)
from standards_sdk_py.shared.types import JsonValue


class Hcs10Client(TypedOperationClient):
    """Synchronous HCS-10 client."""

    def __init__(self, transport: SyncHttpTransport) -> None:
        super().__init__("hcs10", transport)

    def confirmConnection(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("confirmConnection", options=options, **kwargs)

    def create(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("create", options=options, **kwargs)

    def createAccount(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("createAccount", options=options, **kwargs)

    def createAgent(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("createAgent", options=options, **kwargs)

    def createAndRegisterAgent(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("createAndRegisterAgent", options=options, **kwargs)

    def createAndRegisterMCPServer(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("createAndRegisterMCPServer", options=options, **kwargs)

    def createConnectionTopic(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("createConnectionTopic", options=options, **kwargs)

    def createInboundTopic(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("createInboundTopic", options=options, **kwargs)

    def createMCPServer(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("createMCPServer", options=options, **kwargs)

    def createRegistryTopic(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("createRegistryTopic", options=options, **kwargs)

    def createTopic(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("createTopic", options=options, **kwargs)

    def getAccountAndSigner(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("getAccountAndSigner", options=options, **kwargs)

    def getClient(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("getClient", options=options, **kwargs)

    def getInboundTopicType(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("getInboundTopicType", options=options, **kwargs)

    def getLogger(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("getLogger", options=options, **kwargs)

    def getNetwork(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("getNetwork", options=options, **kwargs)

    def getOperatorAccountId(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("getOperatorAccountId", options=options, **kwargs)

    def handleConnectionRequest(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("handleConnectionRequest", options=options, **kwargs)

    def inscribeFile(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("inscribeFile", options=options, **kwargs)

    def inscribePfp(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("inscribePfp", options=options, **kwargs)

    def registerAgent(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("registerAgent", options=options, **kwargs)

    def registerAgentWithGuardedRegistry(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("registerAgentWithGuardedRegistry", options=options, **kwargs)

    def sendMessage(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("sendMessage", options=options, **kwargs)

    def sendTransaction(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("sendTransaction", options=options, **kwargs)

    def sendTransactionOperation(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("sendTransactionOperation", options=options, **kwargs)

    def storeHCS11Profile(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("storeHCS11Profile", options=options, **kwargs)

    def submitPayload(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("submitPayload", options=options, **kwargs)

    def waitForConnectionConfirmation(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("waitForConnectionConfirmation", options=options, **kwargs)

    confirm_connection = confirmConnection
    create_account = createAccount
    create_agent = createAgent
    create_and_register_agent = createAndRegisterAgent
    create_and_register_m_c_p_server = createAndRegisterMCPServer
    create_connection_topic = createConnectionTopic
    create_inbound_topic = createInboundTopic
    create_m_c_p_server = createMCPServer
    create_registry_topic = createRegistryTopic
    create_topic = createTopic
    get_account_and_signer = getAccountAndSigner
    get_client = getClient
    get_inbound_topic_type = getInboundTopicType
    get_logger = getLogger
    get_network = getNetwork
    get_operator_account_id = getOperatorAccountId
    handle_connection_request = handleConnectionRequest
    inscribe_file = inscribeFile
    inscribe_pfp = inscribePfp
    register_agent = registerAgent
    register_agent_with_guarded_registry = registerAgentWithGuardedRegistry
    send_message = sendMessage
    send_transaction = sendTransaction
    send_transaction_operation = sendTransactionOperation
    store_h_c_s11_profile = storeHCS11Profile
    submit_payload = submitPayload
    wait_for_connection_confirmation = waitForConnectionConfirmation


class AsyncHcs10Client(AsyncTypedOperationClient):
    """Asynchronous HCS-10 client."""

    def __init__(self, transport: AsyncHttpTransport) -> None:
        super().__init__("hcs10", transport)

    async def confirmConnection(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("confirmConnection", options=options, **kwargs)

    async def create(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("create", options=options, **kwargs)

    async def createAccount(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("createAccount", options=options, **kwargs)

    async def createAgent(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("createAgent", options=options, **kwargs)

    async def createAndRegisterAgent(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("createAndRegisterAgent", options=options, **kwargs)

    async def createAndRegisterMCPServer(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("createAndRegisterMCPServer", options=options, **kwargs)

    async def createConnectionTopic(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("createConnectionTopic", options=options, **kwargs)

    async def createInboundTopic(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("createInboundTopic", options=options, **kwargs)

    async def createMCPServer(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("createMCPServer", options=options, **kwargs)

    async def createRegistryTopic(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("createRegistryTopic", options=options, **kwargs)

    async def createTopic(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("createTopic", options=options, **kwargs)

    async def getAccountAndSigner(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("getAccountAndSigner", options=options, **kwargs)

    async def getClient(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("getClient", options=options, **kwargs)

    async def getInboundTopicType(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("getInboundTopicType", options=options, **kwargs)

    async def getLogger(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("getLogger", options=options, **kwargs)

    async def getNetwork(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("getNetwork", options=options, **kwargs)

    async def getOperatorAccountId(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("getOperatorAccountId", options=options, **kwargs)

    async def handleConnectionRequest(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("handleConnectionRequest", options=options, **kwargs)

    async def inscribeFile(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("inscribeFile", options=options, **kwargs)

    async def inscribePfp(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("inscribePfp", options=options, **kwargs)

    async def registerAgent(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("registerAgent", options=options, **kwargs)

    async def registerAgentWithGuardedRegistry(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed(
            "registerAgentWithGuardedRegistry", options=options, **kwargs
        )

    async def sendMessage(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("sendMessage", options=options, **kwargs)

    async def sendTransaction(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("sendTransaction", options=options, **kwargs)

    async def sendTransactionOperation(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("sendTransactionOperation", options=options, **kwargs)

    async def storeHCS11Profile(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("storeHCS11Profile", options=options, **kwargs)

    async def submitPayload(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("submitPayload", options=options, **kwargs)

    async def waitForConnectionConfirmation(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("waitForConnectionConfirmation", options=options, **kwargs)

    confirm_connection = confirmConnection
    create_account = createAccount
    create_agent = createAgent
    create_and_register_agent = createAndRegisterAgent
    create_and_register_m_c_p_server = createAndRegisterMCPServer
    create_connection_topic = createConnectionTopic
    create_inbound_topic = createInboundTopic
    create_m_c_p_server = createMCPServer
    create_registry_topic = createRegistryTopic
    create_topic = createTopic
    get_account_and_signer = getAccountAndSigner
    get_client = getClient
    get_inbound_topic_type = getInboundTopicType
    get_logger = getLogger
    get_network = getNetwork
    get_operator_account_id = getOperatorAccountId
    handle_connection_request = handleConnectionRequest
    inscribe_file = inscribeFile
    inscribe_pfp = inscribePfp
    register_agent = registerAgent
    register_agent_with_guarded_registry = registerAgentWithGuardedRegistry
    send_message = sendMessage
    send_transaction = sendTransaction
    send_transaction_operation = sendTransactionOperation
    store_h_c_s11_profile = storeHCS11Profile
    submit_payload = submitPayload
    wait_for_connection_confirmation = waitForConnectionConfirmation


HCS10Client = Hcs10Client
AsyncHCS10Client = AsyncHcs10Client

__all__ = [
    "AsyncHCS10Client",
    "AsyncHcs10Client",
    "HCS10Client",
    "Hcs10Client",
]
