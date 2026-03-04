import os

import pytest

from standards_sdk_py.exceptions import ApiError, ValidationError
from standards_sdk_py.inscriber import (
    InscriberClient,
    InscribeViaRegistryBrokerOptions,
    InscriptionInput,
)


@pytest.mark.integration
def test_inscriber_registry_broker_end_to_end_testnet() -> None:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("set RUN_INTEGRATION=1 to run integration tests")
    if os.getenv("RUN_INSCRIBER_INTEGRATION") != "1":
        pytest.skip("set RUN_INSCRIBER_INTEGRATION=1 to run inscriber integration")

    hedera_network = (os.getenv("HEDERA_NETWORK") or "").strip().lower()
    inscriber_network = (os.getenv("INSCRIBER_HEDERA_NETWORK") or "").strip().lower()
    if hedera_network and inscriber_network and hedera_network != inscriber_network:
        pytest.skip(
            "HEDERA_NETWORK and INSCRIBER_HEDERA_NETWORK disagree; set one canonical network value"
        )

    network = hedera_network or inscriber_network or "testnet"
    if network != "testnet":
        pytest.skip(
            "this integration test is testnet-only; set HEDERA_NETWORK=testnet "
            "(and clear INSCRIBER_HEDERA_NETWORK if present)"
        )

    account_id_candidates = [
        "TESTNET_HEDERA_ACCOUNT_ID",
        "INSCRIBER_LEDGER_ACCOUNT_ID",
        "HEDERA_ACCOUNT_ID",
    ]
    private_key_candidates = [
        "TESTNET_HEDERA_PRIVATE_KEY",
        "INSCRIBER_LEDGER_PRIVATE_KEY",
        "HEDERA_PRIVATE_KEY",
    ]
    account_id = next(
        (os.getenv(name, "").strip() for name in account_id_candidates if os.getenv(name)), ""
    )
    private_key = next(
        (os.getenv(name, "").strip() for name in private_key_candidates if os.getenv(name)),
        "",
    )
    if not account_id or not private_key:
        pytest.skip(
            "set TESTNET_HEDERA_ACCOUNT_ID/TESTNET_HEDERA_PRIVATE_KEY (or "
            "HEDERA_ACCOUNT_ID/HEDERA_PRIVATE_KEY for testnet) for deterministic testnet runs"
        )

    base_url = (os.getenv("REGISTRY_BROKER_BASE_URL") or "https://hol.org/registry/api/v1").strip()
    wait_timeout_ms = int((os.getenv("INSCRIBER_WAIT_TIMEOUT_MS") or "600000").strip())
    poll_interval_ms = int((os.getenv("INSCRIBER_POLL_INTERVAL_MS") or "2000").strip())
    client = InscriberClient()
    options = InscribeViaRegistryBrokerOptions(
        base_url=base_url,
        api_key=None,
        ledger_account_id=account_id,
        ledger_private_key=private_key,
        ledger_network=network,
        mode="file",
        metadata={"source": "standards-sdk-py-integration"},
        tags=["sdk", "python", "integration"],
        wait_for_confirmation=True,
        wait_timeout_ms=wait_timeout_ms,
        poll_interval_ms=poll_interval_ms,
    )
    try:
        result = client.inscribe_via_registry_broker(
            InscriptionInput(
                type="buffer",
                buffer=b"standards-sdk-py testnet inscription integration",
                fileName="standards-sdk-py-integration.txt",
                mimeType="text/plain",
            ),
            options,
        )
    except ApiError as exc:
        body = exc.context.body
        details_text = ""
        if isinstance(body, dict):
            details_text = " ".join(str(value) for value in body.values())
        elif isinstance(body, str):
            details_text = body
        if exc.context.status_code == 400 and "insufficient credits" in details_text.lower():
            pytest.skip("registry broker credits are insufficient for live inscription")
        raise
    except ValidationError as exc:
        details = exc.context.details or {}
        status = str(details.get("status", "")).lower()
        if str(exc) == "registry broker job did not complete before timeout" and status in {
            "pending",
            "queued",
            "in_progress",
            "processing",
            "submitted",
        }:
            pytest.skip("registry broker accepted job but it did not complete before timeout")
        raise
    assert result.confirmed is True
    assert (result.status or "").lower() == "completed"
    assert result.topic_id is not None and result.topic_id.startswith("0.0.")
    if result.network:
        assert result.network.lower() == network
