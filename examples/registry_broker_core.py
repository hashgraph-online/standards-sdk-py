"""Registry Broker core flow example."""

from standards_sdk_py import RegistryBrokerClient


def main() -> None:
    client = RegistryBrokerClient()
    try:
        protocols = client.list_protocols()
        print(f"Protocols: {len(protocols.protocols)}")
        result = client.search(query="hcs", limit=5)
        print(f"Search total: {result.total}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
