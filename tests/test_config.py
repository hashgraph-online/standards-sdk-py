from standards_sdk_py.shared.config import RegistryBrokerAuthConfig, SdkConfig


def test_config_from_mapping() -> None:
    config = SdkConfig.from_mapping(
        {
            "STANDARDS_SDK_PY_REGISTRY_BROKER_BASE_URL": "https://example-broker.test",
            "STANDARDS_SDK_PY_MIRROR_NODE_BASE_URL": "https://example-mirror.test",
            "STANDARDS_SDK_PY_API_KEY": "key-123",
            "STANDARDS_SDK_PY_ACCOUNT_ID": "0.0.123",
            "STANDARDS_SDK_PY_LEDGER_API_KEY": "ledger-abc",
        },
    )
    assert config.network.registry_broker_base_url == "https://example-broker.test"
    assert config.network.mirror_node_base_url == "https://example-mirror.test"
    assert config.registry_auth.api_key == "key-123"
    assert config.registry_auth.account_id == "0.0.123"
    assert config.registry_auth.ledger_api_key == "ledger-abc"


def test_registry_auth_headers() -> None:
    headers = RegistryBrokerAuthConfig(
        api_key="api-k",
        account_id="0.0.7",
        ledger_api_key="ledger-k",
        default_headers={"x-custom": "x"},
    ).headers()
    assert headers["x-custom"] == "x"
    assert headers["x-account-id"] == "0.0.7"
    assert headers["x-api-key"] == "api-k"
    assert headers["x-ledger-api-key"] == "ledger-k"
