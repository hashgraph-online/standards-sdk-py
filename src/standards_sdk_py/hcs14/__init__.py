"""HCS-14 module."""

# ruff: noqa: N802

from __future__ import annotations

from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.operation_dispatch import (
    AsyncTypedOperationClient,
    OperationOptions,
    TypedOperationClient,
)
from standards_sdk_py.shared.types import JsonValue


class Hcs14Client(TypedOperationClient):
    """Synchronous HCS-14 client."""

    def __init__(self, transport: SyncHttpTransport) -> None:
        super().__init__("hcs14", transport)

    def canonicalizeAgentData(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("canonicalizeAgentData", options=options, **kwargs)

    def configureHederaClient(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("configureHederaClient", options=options, **kwargs)

    def createDid(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("createDid", options=options, **kwargs)

    def createDidWithUaid(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("createDidWithUaid", options=options, **kwargs)

    def createUaid(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("createUaid", options=options, **kwargs)

    def filterAdapters(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("filterAdapters", options=options, **kwargs)

    def filterIssuersByMethod(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("filterIssuersByMethod", options=options, **kwargs)

    def filterProfileResolversByMethod(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("filterProfileResolversByMethod", options=options, **kwargs)

    def filterResolversByMethod(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("filterResolversByMethod", options=options, **kwargs)

    def filterUaidProfileResolversByMethod(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("filterUaidProfileResolversByMethod", options=options, **kwargs)

    def filterUaidProfileResolversByProfileId(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed(
            "filterUaidProfileResolversByProfileId", options=options, **kwargs
        )

    def getIssuerRegistry(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("getIssuerRegistry", options=options, **kwargs)

    def getResolverRegistry(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("getResolverRegistry", options=options, **kwargs)

    def isEip155Caip10(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("isEip155Caip10", options=options, **kwargs)

    def isHederaCaip10(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("isHederaCaip10", options=options, **kwargs)

    def isHederaNetwork(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("isHederaNetwork", options=options, **kwargs)

    def listAdapters(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("listAdapters", options=options, **kwargs)

    def listIssuers(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("listIssuers", options=options, **kwargs)

    def listProfileResolvers(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("listProfileResolvers", options=options, **kwargs)

    def listResolvers(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("listResolvers", options=options, **kwargs)

    def listUaidProfileResolvers(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("listUaidProfileResolvers", options=options, **kwargs)

    def parseHcs14Did(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("parseHcs14Did", options=options, **kwargs)

    def parseHederaCaip10(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("parseHederaCaip10", options=options, **kwargs)

    def registerAdapter(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("registerAdapter", options=options, **kwargs)

    def registerAidDnsWebProfileResolver(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("registerAidDnsWebProfileResolver", options=options, **kwargs)

    def registerAnsDnsWebProfileResolver(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("registerAnsDnsWebProfileResolver", options=options, **kwargs)

    def registerHcs11ProfileResolver(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("registerHcs11ProfileResolver", options=options, **kwargs)

    def registerHederaIssuer(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("registerHederaIssuer", options=options, **kwargs)

    def registerHederaResolver(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("registerHederaResolver", options=options, **kwargs)

    def registerProfileResolver(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("registerProfileResolver", options=options, **kwargs)

    def registerUaidDidResolutionProfileResolver(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed(
            "registerUaidDidResolutionProfileResolver", options=options, **kwargs
        )

    def registerUaidDnsWebProfileResolver(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("registerUaidDnsWebProfileResolver", options=options, **kwargs)

    def registerUaidProfileResolver(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return self._invoke_typed("registerUaidProfileResolver", options=options, **kwargs)

    def resolveDidProfile(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("resolveDidProfile", options=options, **kwargs)

    def resolveUaidProfile(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("resolveUaidProfile", options=options, **kwargs)

    def toEip155Caip10(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("toEip155Caip10", options=options, **kwargs)

    def toHederaCaip10(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("toHederaCaip10", options=options, **kwargs)

    canonicalize_agent_data = canonicalizeAgentData
    configure_hedera_client = configureHederaClient
    create_did = createDid
    create_did_with_uaid = createDidWithUaid
    create_uaid = createUaid
    filter_adapters = filterAdapters
    filter_issuers_by_method = filterIssuersByMethod
    filter_profile_resolvers_by_method = filterProfileResolversByMethod
    filter_resolvers_by_method = filterResolversByMethod
    filter_uaid_profile_resolvers_by_method = filterUaidProfileResolversByMethod
    filter_uaid_profile_resolvers_by_profile_id = filterUaidProfileResolversByProfileId
    get_issuer_registry = getIssuerRegistry
    get_resolver_registry = getResolverRegistry
    is_eip155_caip10 = isEip155Caip10
    is_hedera_caip10 = isHederaCaip10
    is_hedera_network = isHederaNetwork
    list_adapters = listAdapters
    list_issuers = listIssuers
    list_profile_resolvers = listProfileResolvers
    list_resolvers = listResolvers
    list_uaid_profile_resolvers = listUaidProfileResolvers
    parse_hcs14_did = parseHcs14Did
    parse_hedera_caip10 = parseHederaCaip10
    register_adapter = registerAdapter
    register_aid_dns_web_profile_resolver = registerAidDnsWebProfileResolver
    register_ans_dns_web_profile_resolver = registerAnsDnsWebProfileResolver
    register_hcs11_profile_resolver = registerHcs11ProfileResolver
    register_hedera_issuer = registerHederaIssuer
    register_hedera_resolver = registerHederaResolver
    register_profile_resolver = registerProfileResolver
    register_uaid_did_resolution_profile_resolver = registerUaidDidResolutionProfileResolver
    register_uaid_dns_web_profile_resolver = registerUaidDnsWebProfileResolver
    register_uaid_profile_resolver = registerUaidProfileResolver
    resolve_did_profile = resolveDidProfile
    resolve_uaid_profile = resolveUaidProfile
    to_eip155_caip10 = toEip155Caip10
    to_hedera_caip10 = toHederaCaip10


class AsyncHcs14Client(AsyncTypedOperationClient):
    """Asynchronous HCS-14 client."""

    def __init__(self, transport: AsyncHttpTransport) -> None:
        super().__init__("hcs14", transport)

    async def canonicalizeAgentData(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("canonicalizeAgentData", options=options, **kwargs)

    async def configureHederaClient(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("configureHederaClient", options=options, **kwargs)

    async def createDid(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("createDid", options=options, **kwargs)

    async def createDidWithUaid(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("createDidWithUaid", options=options, **kwargs)

    async def createUaid(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("createUaid", options=options, **kwargs)

    async def filterAdapters(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("filterAdapters", options=options, **kwargs)

    async def filterIssuersByMethod(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("filterIssuersByMethod", options=options, **kwargs)

    async def filterProfileResolversByMethod(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("filterProfileResolversByMethod", options=options, **kwargs)

    async def filterResolversByMethod(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("filterResolversByMethod", options=options, **kwargs)

    async def filterUaidProfileResolversByMethod(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed(
            "filterUaidProfileResolversByMethod", options=options, **kwargs
        )

    async def filterUaidProfileResolversByProfileId(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed(
            "filterUaidProfileResolversByProfileId", options=options, **kwargs
        )

    async def getIssuerRegistry(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("getIssuerRegistry", options=options, **kwargs)

    async def getResolverRegistry(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("getResolverRegistry", options=options, **kwargs)

    async def isEip155Caip10(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("isEip155Caip10", options=options, **kwargs)

    async def isHederaCaip10(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("isHederaCaip10", options=options, **kwargs)

    async def isHederaNetwork(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("isHederaNetwork", options=options, **kwargs)

    async def listAdapters(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("listAdapters", options=options, **kwargs)

    async def listIssuers(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("listIssuers", options=options, **kwargs)

    async def listProfileResolvers(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("listProfileResolvers", options=options, **kwargs)

    async def listResolvers(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("listResolvers", options=options, **kwargs)

    async def listUaidProfileResolvers(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("listUaidProfileResolvers", options=options, **kwargs)

    async def parseHcs14Did(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("parseHcs14Did", options=options, **kwargs)

    async def parseHederaCaip10(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("parseHederaCaip10", options=options, **kwargs)

    async def registerAdapter(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("registerAdapter", options=options, **kwargs)

    async def registerAidDnsWebProfileResolver(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed(
            "registerAidDnsWebProfileResolver", options=options, **kwargs
        )

    async def registerAnsDnsWebProfileResolver(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed(
            "registerAnsDnsWebProfileResolver", options=options, **kwargs
        )

    async def registerHcs11ProfileResolver(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("registerHcs11ProfileResolver", options=options, **kwargs)

    async def registerHederaIssuer(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("registerHederaIssuer", options=options, **kwargs)

    async def registerHederaResolver(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("registerHederaResolver", options=options, **kwargs)

    async def registerProfileResolver(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("registerProfileResolver", options=options, **kwargs)

    async def registerUaidDidResolutionProfileResolver(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed(
            "registerUaidDidResolutionProfileResolver", options=options, **kwargs
        )

    async def registerUaidDnsWebProfileResolver(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed(
            "registerUaidDnsWebProfileResolver", options=options, **kwargs
        )

    async def registerUaidProfileResolver(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("registerUaidProfileResolver", options=options, **kwargs)

    async def resolveDidProfile(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("resolveDidProfile", options=options, **kwargs)

    async def resolveUaidProfile(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("resolveUaidProfile", options=options, **kwargs)

    async def toEip155Caip10(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("toEip155Caip10", options=options, **kwargs)

    async def toHederaCaip10(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("toHederaCaip10", options=options, **kwargs)

    canonicalize_agent_data = canonicalizeAgentData
    configure_hedera_client = configureHederaClient
    create_did = createDid
    create_did_with_uaid = createDidWithUaid
    create_uaid = createUaid
    filter_adapters = filterAdapters
    filter_issuers_by_method = filterIssuersByMethod
    filter_profile_resolvers_by_method = filterProfileResolversByMethod
    filter_resolvers_by_method = filterResolversByMethod
    filter_uaid_profile_resolvers_by_method = filterUaidProfileResolversByMethod
    filter_uaid_profile_resolvers_by_profile_id = filterUaidProfileResolversByProfileId
    get_issuer_registry = getIssuerRegistry
    get_resolver_registry = getResolverRegistry
    is_eip155_caip10 = isEip155Caip10
    is_hedera_caip10 = isHederaCaip10
    is_hedera_network = isHederaNetwork
    list_adapters = listAdapters
    list_issuers = listIssuers
    list_profile_resolvers = listProfileResolvers
    list_resolvers = listResolvers
    list_uaid_profile_resolvers = listUaidProfileResolvers
    parse_hcs14_did = parseHcs14Did
    parse_hedera_caip10 = parseHederaCaip10
    register_adapter = registerAdapter
    register_aid_dns_web_profile_resolver = registerAidDnsWebProfileResolver
    register_ans_dns_web_profile_resolver = registerAnsDnsWebProfileResolver
    register_hcs11_profile_resolver = registerHcs11ProfileResolver
    register_hedera_issuer = registerHederaIssuer
    register_hedera_resolver = registerHederaResolver
    register_profile_resolver = registerProfileResolver
    register_uaid_did_resolution_profile_resolver = registerUaidDidResolutionProfileResolver
    register_uaid_dns_web_profile_resolver = registerUaidDnsWebProfileResolver
    register_uaid_profile_resolver = registerUaidProfileResolver
    resolve_did_profile = resolveDidProfile
    resolve_uaid_profile = resolveUaidProfile
    to_eip155_caip10 = toEip155Caip10
    to_hedera_caip10 = toHederaCaip10


HCS14Client = Hcs14Client
AsyncHCS14Client = AsyncHcs14Client

__all__ = [
    "AsyncHCS14Client",
    "AsyncHcs14Client",
    "HCS14Client",
    "Hcs14Client",
]
