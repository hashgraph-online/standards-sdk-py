"""HCS-5 mint/hashinal payload example."""

from __future__ import annotations

from standards_sdk_py.hcs5 import Hcs5CreateHashinalOptions, Hcs5MintOptions, build_hcs1_hrl


def main() -> None:
    metadata_topic_id = "0.0.700010"
    mint_options = Hcs5MintOptions(
        tokenId="0.0.710001",
        metadataTopicId=metadata_topic_id,
        memo="hcs5 mint example",
    )
    create_hashinal_options = Hcs5CreateHashinalOptions(
        tokenId="0.0.710001",
        inscriptionInput={
            "type": "buffer",
            "buffer": "68656c6c6f2d68617368696e616c",
            "fileName": "hello-hashinal.txt",
            "mimeType": "text/plain",
        },
        inscriptionOptions={"baseUrl": "https://hol.org/registry/api/v1"},
        memo="hcs5 create-hashinal example",
    )
    print(
        {
            "hcs1_hrl": build_hcs1_hrl(metadata_topic_id),
            "mint_options": mint_options.model_dump(by_alias=True, exclude_none=True),
            "create_hashinal_options": create_hashinal_options.model_dump(
                by_alias=True,
                exclude_none=True,
            ),
        }
    )


if __name__ == "__main__":
    main()
