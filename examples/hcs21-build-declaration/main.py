"""HCS-21 adapter declaration payload example."""

from __future__ import annotations

from standards_sdk_py.hcs21 import (
    Hcs21AdapterDeclaration,
    Hcs21AdapterPackage,
    Hcs21CreateRegistryTopicOptions,
    Hcs21Operation,
    Hcs21PublishDeclarationOptions,
)


def main() -> None:
    declaration = Hcs21AdapterDeclaration(
        op=Hcs21Operation.REGISTER,
        adapterId="demo-summarizer",
        entity="hashgraph-online",
        package=Hcs21AdapterPackage(
            registry="npm",
            name="@hashgraph-online/demo-summarizer",
            version="1.0.0",
            integrity="sha512-demo",
        ),
        manifest="hcs://1/0.0.700100",
        manifestSequence=1,
        config={"inputSchema": "json", "outputSchema": "markdown"},
        stateModel="stateless",
    )
    create_topic_options = Hcs21CreateRegistryTopicOptions(
        ttl=3600,
        indexed=True,
        topicType=0,
        useOperatorAsAdmin=True,
        useOperatorAsSubmit=True,
    )
    publish_options = Hcs21PublishDeclarationOptions(
        topicId="0.0.700101",
        declaration=declaration,
        transactionMemo="hcs21 declaration publish example",
    )
    print(
        {
            "create_topic_options": create_topic_options.model_dump(
                by_alias=True, exclude_none=True
            ),
            "publish_options": publish_options.model_dump(by_alias=True, exclude_none=True),
        }
    )


if __name__ == "__main__":
    main()
