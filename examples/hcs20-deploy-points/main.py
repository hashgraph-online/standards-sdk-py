"""HCS-20 points payload example."""

from __future__ import annotations

from standards_sdk_py.hcs20 import Hcs20DeployPointsOptions, Hcs20MintPointsOptions


def main() -> None:
    deploy_options = Hcs20DeployPointsOptions(
        name="Demo Loyalty Points",
        tick="DLP",
        maxSupply="1000000",
        limitPerMint="1000",
        metadata="ipfs://bafybeigdyrzt-demo",
        memo="hcs20 deploy example",
        usePrivateTopic=True,
    )
    mint_options = Hcs20MintPointsOptions(
        tick="DLP",
        amount="250",
        to="0.0.700090",
        memo="hcs20 mint example",
        topicId="0.0.700091",
    )
    print(
        {
            "deploy_options": deploy_options.model_dump(by_alias=True, exclude_none=True),
            "mint_options": mint_options.model_dump(by_alias=True, exclude_none=True),
        }
    )


if __name__ == "__main__":
    main()
