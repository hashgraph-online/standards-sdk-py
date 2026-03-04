"""HCS-17 state hash payload example."""

from __future__ import annotations

from standards_sdk_py.hcs17 import (
    HCS17Client,
    Hcs17ComputeAndPublishOptions,
    Hcs17StateHashMessage,
    Hcs17SubmitMessageOptions,
)

_TEST_OPERATOR_ID = "0.0.1001"
_TEST_OPERATOR_KEY = (
    "302e020100300506032b657004220420fb77695921a5c79474d57c42006f03ff"
    "178688514d797fb30f60fd0fc9e82716"
)


def main() -> None:
    state_message = Hcs17StateHashMessage(
        state_hash="6d2f4b7308b3d7bd74a85f5d9f54f6f1278cc5fd1fe9c1c911f66fce2e112ebf",
        topics=["0.0.700080", "0.0.700081"],
        account_id="0.0.700082",
        epoch=12,
        m="hcs17 state hash",
    )
    submit_options = Hcs17SubmitMessageOptions(topicId="0.0.700080", message=state_message)
    compute_options = Hcs17ComputeAndPublishOptions(
        accountId="0.0.700082",
        accountPublicKey="302a300506032b6570032100b4f2d8e4",
        topics=["0.0.700080", "0.0.700081"],
        publishTopicId="0.0.700080",
    )
    client = HCS17Client(
        operator_id=_TEST_OPERATOR_ID,
        operator_key=_TEST_OPERATOR_KEY,
        network="testnet",
    )
    print(
        {
            "key_type": client.get_key_type(),
            "submit_options": submit_options.model_dump(by_alias=True, exclude_none=True),
            "compute_options": compute_options.model_dump(by_alias=True, exclude_none=True),
        }
    )


if __name__ == "__main__":
    main()
