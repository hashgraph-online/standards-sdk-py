"""Inscriber quote/auth payload example."""

from __future__ import annotations

import base64
from dataclasses import asdict

from standards_sdk_py.inscriber import (
    BrokerQuoteRequest,
    InscribeViaRegistryBrokerOptions,
    InscriptionInput,
)


def main() -> None:
    input_payload = InscriptionInput(
        type="buffer",
        buffer=b"hello from standards-sdk-py",
        fileName="hello.txt",
        mimeType="text/plain",
    )
    options = InscribeViaRegistryBrokerOptions(
        base_url="https://hol.org/registry/api/v1",
        api_key="demo-api-key",
        mode="file",
        metadata={"source": "inscriber-auth-client-example"},
        tags=["python", "inscriber", "example"],
        wait_for_confirmation=False,
    )
    quote_request = BrokerQuoteRequest(
        inputType=input_payload.type,
        mode=options.mode,
        base64=base64.b64encode(input_payload.buffer or b"").decode("utf-8"),
        fileName=input_payload.file_name,
        mimeType=input_payload.mime_type,
        metadata=options.metadata,
        tags=options.tags,
    )
    print(
        {
            "input_payload": input_payload.model_dump(by_alias=True, exclude_none=True),
            "options": asdict(options),
            "quote_request": quote_request.model_dump(by_alias=True, exclude_none=True),
        }
    )


if __name__ == "__main__":
    main()
