"""Registry Broker route probe demo.

This demo targets the production Registry API by default and can be pointed to
any broker base URL via environment variables.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

from standards_sdk_py import (
    ApiError,
    RegistryBrokerAuthConfig,
    RegistryBrokerClient,
    SdkConfig,
    SdkNetworkConfig,
)

DEFAULT_REGISTRY_BASE_URL = "https://hol.org/registry/api/v1"
DEFAULT_MESSAGE = "Route probe from standards-sdk-py"
DEFAULT_TARGET_UAIDS = [
    "uaid:aid:9WADT6xgCjoT3XP4QCsfQdJwPn8RhXCufoHQcbKRTzdS6fTnmY4BxFKPrwjqkiT4aC",
]


def _parse_list_env(name: str, fallback: list[str]) -> list[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return fallback
    values = [value.strip() for value in raw.split(",")]
    parsed = [value for value in values if value]
    return parsed or fallback


def _parse_optional_api_keys() -> list[str]:
    raw = os.getenv("REGISTRY_BROKER_ROUTE_PROBE_API_KEYS", "").strip()
    if not raw:
        return [""]
    values = [value.strip() for value in raw.split(",")]
    parsed = [value for value in values if value]
    return parsed or [""]


def _create_client(api_key: str | None, include_account_context: bool) -> RegistryBrokerClient:
    base_url = os.getenv("REGISTRY_BROKER_BASE_URL", DEFAULT_REGISTRY_BASE_URL).strip()
    account_id = None
    if include_account_context:
        account_id = os.getenv("REGISTRY_BROKER_ACCOUNT_ID", "").strip() or None
    auth = RegistryBrokerAuthConfig(api_key=api_key, account_id=account_id)
    config = SdkConfig(
        network=SdkNetworkConfig(registry_broker_base_url=base_url),
        registry_auth=auth,
    )
    return RegistryBrokerClient(config=config)


def _probe_one(client: RegistryBrokerClient, uaid: str, message: str) -> dict[str, Any]:
    path = f"/route/{quote(uaid, safe='')}"
    return client.request_json(
        path,
        {
            "method": "POST",
            "body": {"message": message},
        },
    )


def main() -> None:
    uaids = _parse_list_env("REGISTRY_BROKER_ROUTE_PROBE_UAIDS", DEFAULT_TARGET_UAIDS)
    message = (
        os.getenv("REGISTRY_BROKER_ROUTE_PROBE_MESSAGE", DEFAULT_MESSAGE).strip() or DEFAULT_MESSAGE
    )
    api_keys = _parse_optional_api_keys()

    for index, api_key in enumerate(api_keys, start=1):
        is_anonymous = not api_key
        label = "anonymous" if is_anonymous else f"api-key-{index}"
        print(f"\nRoute probe mode={label}")
        client = _create_client(api_key or None, include_account_context=not is_anonymous)
        try:
            for uaid in uaids:
                try:
                    payload = _probe_one(client, uaid, message)
                    payload_keys: list[str] = []
                    if isinstance(payload, dict):
                        payload_keys = [str(key) for key in payload.keys()]
                    print(f"uaid={uaid} status=ok payloadKeys={sorted(payload_keys)}")
                except ApiError as error:
                    status_code = error.context.status_code
                    print(f"uaid={uaid} status=error code={status_code}")
        finally:
            client.close()


if __name__ == "__main__":
    main()
