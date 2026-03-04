"""HCS-18 discovery announce payload example."""

from __future__ import annotations

from standards_sdk_py.hcs18 import Hcs18CreateDiscoveryTopicOptions, Hcs18DiscoveryMessage


def main() -> None:
    create_topic_options = Hcs18CreateDiscoveryTopicOptions(
        ttlSeconds=3600,
        useOperatorAsAdmin=True,
        useOperatorAsSubmit=True,
    )
    announce_message = Hcs18DiscoveryMessage(
        op="announce",
        data={
            "uaid": "uaid:aid:ans-demo;uid=ans://v1.0.0.demo.agent",
            "displayName": "demo-agent",
            "protocols": ["hcs10", "a2a"],
        },
    )
    print(
        {
            "create_topic_options": create_topic_options.model_dump(
                by_alias=True, exclude_none=True
            ),
            "announce_message": announce_message.model_dump(by_alias=True, exclude_none=True),
        }
    )


if __name__ == "__main__":
    main()
