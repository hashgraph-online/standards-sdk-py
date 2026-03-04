"""Skill quote and publish example."""

from standards_sdk_py import RegistryBrokerClient


def main() -> None:
    client = RegistryBrokerClient()
    payload = {
        "name": "example-skill",
        "version": "0.1.0",
        "description": "Example skill payload",
        "content": "name: example-skill",
    }
    try:
        quote = client.call_operation("quote_skill_publish", body=payload)
        print(f"Quote response type: {type(quote).__name__}")
        publish = client.publish_skill(payload)
        print(f"Publish accepted: {publish.accepted}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
