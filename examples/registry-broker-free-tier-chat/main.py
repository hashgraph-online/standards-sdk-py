"""Registry Broker free-tier chat demo.

This demo defaults to the production Registry API URL and can be pointed to a local
Registry Broker instance by overriding environment variables at runtime.
"""

from __future__ import annotations

import os
from urllib.parse import quote

from examples.registry_broker_demo_utils import (
    format_api_error,
    parse_non_negative_int,
    parse_positive_int,
)
from standards_sdk_py import (
    ApiError,
    RegistryBrokerAuthConfig,
    RegistryBrokerClient,
    SdkConfig,
    SdkNetworkConfig,
)
from standards_sdk_py.registry_broker.models import CreateSessionResponse, SendMessageResponse
from standards_sdk_py.shared.types import JsonObject, JsonValue

DEFAULT_REGISTRY_BASE_URL = "https://hol.org/registry/api/v1"
DEFAULT_CHAT_TARGET_UAID = (
    "uaid:aid:3AUoqGTHnMXv1PB8ATCtkB86Xw2uEEJuqMRNCirGQehhNhnQ1vHuwJfAh5K5Dp6RFE"
)
DEFAULT_ATTEMPTS_PER_KEY = 3


def _extract_api_keys() -> list[str]:
    raw = os.getenv("REGISTRY_BROKER_FREE_TIER_CHAT_API_KEYS", "").strip()
    if not raw:
        raise RuntimeError(
            "Set REGISTRY_BROKER_FREE_TIER_CHAT_API_KEYS to one or more comma-separated API keys."
        )
    values = [value.strip() for value in raw.split(",")]
    api_keys = [value for value in values if value]
    if not api_keys:
        raise RuntimeError(
            "REGISTRY_BROKER_FREE_TIER_CHAT_API_KEYS did not include any usable keys."
        )
    return api_keys


def _create_client(api_key: str, account_id: str | None) -> RegistryBrokerClient:
    base_url = os.getenv("REGISTRY_BROKER_BASE_URL", DEFAULT_REGISTRY_BASE_URL).strip()
    config = SdkConfig(
        network=SdkNetworkConfig(registry_broker_base_url=base_url),
        registry_auth=RegistryBrokerAuthConfig(api_key=api_key, account_id=account_id),
    )
    return RegistryBrokerClient(config=config)


def _read_chat_free_usage(
    client: RegistryBrokerClient, account_id: str
) -> dict[str, JsonValue] | None:
    path = f"/credits/chat-free-usage?accountId={quote(account_id, safe='')}"
    result = client.request_json(path)
    if isinstance(result, dict):
        return result
    return None


def _set_chat_free_usage_seed(client: RegistryBrokerClient, account_id: str, count: int) -> None:
    client.request_json(
        "/credits/test/chat-free-usage",
        {
            "method": "POST",
            "body": {
                "accountId": account_id,
                "count": count,
            },
        },
    )


def _run_chat_attempts(api_key: str, attempts: int, key_index: int) -> None:
    account_id = os.getenv("REGISTRY_BROKER_ACCOUNT_ID", "").strip() or None
    target_uaid = os.getenv("REGISTRY_BROKER_CHAT_TARGET_UAID", DEFAULT_CHAT_TARGET_UAID).strip()
    seed_count = parse_non_negative_int(os.getenv("REGISTRY_BROKER_CHAT_FREE_TIER_SEED_COUNT"))

    print(f"\nTesting API key #{key_index + 1} attempts={attempts}")
    client = _create_client(api_key, account_id)
    try:
        if account_id:
            before = _read_chat_free_usage(client, account_id)
            if before:
                print(
                    f"usage-before used={before.get('used')} remaining={before.get('remaining')} "
                    f"limit={before.get('limit')}"
                )
            if seed_count is not None:
                _set_chat_free_usage_seed(client, account_id, seed_count)
                seeded = _read_chat_free_usage(client, account_id)
                if seeded:
                    print(
                        f"usage-seeded used={seeded.get('used')} "
                        f"remaining={seeded.get('remaining')} limit={seeded.get('limit')}"
                    )

        session_payload: JsonObject = {"uaid": target_uaid}
        try:
            session: CreateSessionResponse = client.create_session(session_payload)
        except ApiError as error:
            print(f"session create failed {format_api_error(error)}")
            return
        session_id = session.session_id
        print(f"session created sessionId={session_id}")

        for attempt_index in range(attempts):
            try:
                response: SendMessageResponse = client.send_message(
                    {
                        "sessionId": session_id,
                        "uaid": target_uaid,
                        "streaming": False,
                        "message": f"free-tier chat demo attempt {attempt_index + 1}",
                    }
                )
            except ApiError as error:
                if error.context.status_code == 402:
                    print(f"attempt={attempt_index + 1} send " f"{format_api_error(error)}")
                    continue
                print(f"attempt={attempt_index + 1} send " f"{format_api_error(error)}")
                continue
            response_session = response.session_id
            response_message = response.message_id
            print(
                f"attempt={attempt_index + 1} status=ok "
                f"sessionId={response_session} messageId={response_message}"
            )

        if account_id:
            after = _read_chat_free_usage(client, account_id)
            if after:
                print(
                    f"usage-after used={after.get('used')} remaining={after.get('remaining')} "
                    f"limit={after.get('limit')}"
                )
    finally:
        client.close()


def main() -> None:
    attempts = parse_positive_int(
        os.getenv("REGISTRY_BROKER_FREE_TIER_CHAT_ATTEMPTS"),
        DEFAULT_ATTEMPTS_PER_KEY,
    )
    api_keys = _extract_api_keys()
    for key_index, key in enumerate(api_keys):
        _run_chat_attempts(key, attempts, key_index)


if __name__ == "__main__":
    main()
