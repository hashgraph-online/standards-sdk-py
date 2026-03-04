"""Typed request/response models for HCS-5 operations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Hcs5Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Hcs5MintOptions(_Hcs5Model):
    token_id: str = Field(alias="tokenId")
    metadata_topic_id: str | None = Field(default=None, alias="metadataTopicId")
    supply_key: str | None = Field(default=None, alias="supplyKey")
    memo: str | None = None


class Hcs5CreateHashinalOptions(_Hcs5Model):
    token_id: str = Field(alias="tokenId")
    inscription_input: dict[str, object] = Field(alias="inscriptionInput")
    inscription_options: dict[str, object] = Field(default_factory=dict, alias="inscriptionOptions")
    supply_key: str | None = Field(default=None, alias="supplyKey")
    memo: str | None = None


class Hcs5MintResponse(_Hcs5Model):
    success: bool
    serial_number: int | None = Field(default=None, alias="serialNumber")
    transaction_id: str | None = Field(default=None, alias="transactionId")
    metadata: str | None = None
    error: str | None = None


def build_hcs1_hrl(topic_id: str) -> str:
    return f"hcs://1/{topic_id.strip()}"
