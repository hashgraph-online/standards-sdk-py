"""SDK configuration and explicit environment loading."""

from __future__ import annotations

from dataclasses import dataclass, field
from os import getenv


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped


DEFAULT_REGISTRY_BROKER_BASE_URL = "https://registry.hashgraphonline.com"
DEFAULT_MIRROR_NODE_BASE_URL = "https://mainnet-public.mirrornode.hedera.com/api/v1"


@dataclass(slots=True, frozen=True)
class SdkNetworkConfig:
    """Network endpoints used by the SDK."""

    registry_broker_base_url: str = DEFAULT_REGISTRY_BROKER_BASE_URL
    mirror_node_base_url: str = DEFAULT_MIRROR_NODE_BASE_URL


@dataclass(slots=True, frozen=True)
class RegistryBrokerAuthConfig:
    """Registry Broker request authentication defaults."""

    api_key: str | None = None
    account_id: str | None = None
    ledger_api_key: str | None = None
    default_headers: dict[str, str] = field(default_factory=dict)

    def headers(self) -> dict[str, str]:
        merged = dict(self.default_headers)
        if self.api_key:
            merged["x-api-key"] = self.api_key
        if self.account_id:
            merged["x-account-id"] = self.account_id
        if self.ledger_api_key:
            merged["x-ledger-api-key"] = self.ledger_api_key
            merged.setdefault("x-api-key", self.ledger_api_key)
        return merged


@dataclass(slots=True, frozen=True)
class SdkConfig:
    """Top-level immutable SDK config object."""

    network: SdkNetworkConfig = field(default_factory=SdkNetworkConfig)
    registry_auth: RegistryBrokerAuthConfig = field(
        default_factory=RegistryBrokerAuthConfig,
    )

    @staticmethod
    def from_env(prefix: str = "STANDARDS_SDK_PY_") -> SdkConfig:
        """Load config from environment without mutating process state."""
        broker_url = _clean(getenv(f"{prefix}REGISTRY_BROKER_BASE_URL"))
        mirror_url = _clean(getenv(f"{prefix}MIRROR_NODE_BASE_URL"))
        api_key = _clean(getenv(f"{prefix}API_KEY"))
        account_id = _clean(getenv(f"{prefix}ACCOUNT_ID"))
        ledger_api_key = _clean(getenv(f"{prefix}LEDGER_API_KEY"))
        network = SdkNetworkConfig(
            registry_broker_base_url=broker_url or DEFAULT_REGISTRY_BROKER_BASE_URL,
            mirror_node_base_url=mirror_url or DEFAULT_MIRROR_NODE_BASE_URL,
        )
        auth = RegistryBrokerAuthConfig(
            api_key=api_key,
            account_id=account_id,
            ledger_api_key=ledger_api_key,
        )
        return SdkConfig(network=network, registry_auth=auth)

    @staticmethod
    def from_mapping(mapping: dict[str, str], prefix: str = "STANDARDS_SDK_PY_") -> SdkConfig:
        """Load config from explicit mapping for deterministic tests."""
        broker_url = _clean(mapping.get(f"{prefix}REGISTRY_BROKER_BASE_URL"))
        mirror_url = _clean(mapping.get(f"{prefix}MIRROR_NODE_BASE_URL"))
        api_key = _clean(mapping.get(f"{prefix}API_KEY"))
        account_id = _clean(mapping.get(f"{prefix}ACCOUNT_ID"))
        ledger_api_key = _clean(mapping.get(f"{prefix}LEDGER_API_KEY"))
        network = SdkNetworkConfig(
            registry_broker_base_url=broker_url or DEFAULT_REGISTRY_BROKER_BASE_URL,
            mirror_node_base_url=mirror_url or DEFAULT_MIRROR_NODE_BASE_URL,
        )
        auth = RegistryBrokerAuthConfig(
            api_key=api_key,
            account_id=account_id,
            ledger_api_key=ledger_api_key,
        )
        return SdkConfig(network=network, registry_auth=auth)
