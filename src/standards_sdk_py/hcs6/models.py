"""Typed request/response models for HCS-6 operations."""

from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Hcs6Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Hcs6Operation(StrEnum):
    REGISTER = "register"


class Hcs6RegistryType(IntEnum):
    NON_INDEXED = 1


class Hcs6Message(_Hcs6Model):
    p: Literal["hcs-6"] = "hcs-6"
    op: Hcs6Operation = Hcs6Operation.REGISTER
    t_id: str
    m: str | None = None


class Hcs6CreateRegistryOptions(_Hcs6Model):
    ttl: int = 86400
    admin_key: str | bool | None = Field(default=None, alias="adminKey")
    submit_key: str | bool | None = Field(default=None, alias="submitKey")
    use_operator_as_admin: bool = Field(default=False, alias="useOperatorAsAdmin")
    use_operator_as_submit: bool = Field(default=False, alias="useOperatorAsSubmit")
    memo_override: str | None = Field(default=None, alias="memoOverride")


class Hcs6RegisterEntryOptions(_Hcs6Model):
    target_topic_id: str = Field(alias="targetTopicId")
    memo: str | None = None
    analytics_memo: str | None = Field(default=None, alias="analyticsMemo")


class Hcs6QueryRegistryOptions(_Hcs6Model):
    limit: int = 100
    order: Literal["asc", "desc"] = "asc"
    skip: int = 0


class Hcs6MintOptions(_Hcs6Model):
    token_id: str = Field(alias="tokenId")
    metadata_topic_id: str | None = Field(default=None, alias="metadataTopicId")
    supply_key: str | None = Field(default=None, alias="supplyKey")
    memo: str | None = None


class Hcs6InscribeAndMintOptions(_Hcs6Model):
    token_id: str = Field(alias="tokenId")
    inscription_input: dict[str, object] = Field(alias="inscriptionInput")
    inscription_options: dict[str, object] | None = Field(default=None, alias="inscriptionOptions")
    supply_key: str | None = Field(default=None, alias="supplyKey")
    memo: str | None = None


class Hcs6CreateHashinalOptions(_Hcs6Model):
    metadata: dict[str, object]
    memo: str | None = None
    ttl: int | None = None
    inscription_options: dict[str, object] | None = Field(default=None, alias="inscriptionOptions")
    registry_topic_id: str | None = Field(default=None, alias="registryTopicId")
    submit_key: str | None = Field(default=None, alias="submitKey")


class Hcs6RegisterOptions(_Hcs6Model):
    metadata: dict[str, object]
    data: dict[str, object] | None = None
    memo: str | None = None
    ttl: int | None = None
    inscription_options: dict[str, object] | None = Field(default=None, alias="inscriptionOptions")
    registry_topic_id: str | None = Field(default=None, alias="registryTopicId")
    submit_key: str | None = Field(default=None, alias="submitKey")


class Hcs6TopicRegistrationResponse(_Hcs6Model):
    success: bool
    topic_id: str | None = Field(default=None, alias="topicId")
    transaction_id: str | None = Field(default=None, alias="transactionId")
    error: str | None = None


class Hcs6RegistryOperationResponse(_Hcs6Model):
    success: bool
    transaction_id: str | None = Field(default=None, alias="transactionId")
    sequence_number: int | None = Field(default=None, alias="sequenceNumber")
    error: str | None = None


class Hcs6RegistryEntry(_Hcs6Model):
    topic_id: str = Field(alias="topicId")
    sequence: int
    timestamp: str
    payer: str
    message: Hcs6Message
    consensus_timestamp: str = Field(alias="consensus_timestamp")
    registry_type: Hcs6RegistryType = Field(alias="registry_type")


class Hcs6TopicRegistry(_Hcs6Model):
    topic_id: str = Field(alias="topicId")
    registry_type: Hcs6RegistryType = Field(alias="registryType")
    ttl: int
    entries: list[Hcs6RegistryEntry]
    latest_entry: Hcs6RegistryEntry | None = Field(default=None, alias="latestEntry")


class Hcs6MintResponse(_Hcs6Model):
    success: bool
    serial_number: int | None = Field(default=None, alias="serialNumber")
    transaction_id: str | None = Field(default=None, alias="transactionId")
    metadata: str | None = None
    error: str | None = None


class Hcs6CreateHashinalResponse(_Hcs6Model):
    success: bool
    registry_topic_id: str | None = Field(default=None, alias="registryTopicId")
    inscription_topic_id: str | None = Field(default=None, alias="inscriptionTopicId")
    transaction_id: str | None = Field(default=None, alias="transactionId")
    error: str | None = None


def build_hcs6_hrl(topic_id: str) -> str:
    return f"hcs://6/{topic_id.strip()}"
