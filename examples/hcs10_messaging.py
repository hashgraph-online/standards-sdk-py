"""HCS-10 messaging scaffold example."""

from standards_sdk_py.hcs10 import Hcs10Client
from standards_sdk_py.shared.http import SyncHttpTransport


def main() -> None:
    transport = SyncHttpTransport("https://registry.hashgraphonline.com")
    client = Hcs10Client(transport)
    payload = {
        "topicId": "0.0.0",
        "message": "hello",
    }
    try:
        response = client.call("/message", method="POST", body=payload)
        print(f"Response type: {type(response).__name__}")
    finally:
        transport.close()


if __name__ == "__main__":
    main()
