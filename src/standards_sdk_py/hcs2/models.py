"""Typed request/response models for HCS-2 operations."""

from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Hcs2Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Hcs2Operation(StrEnum):
    REGISTER = "register"
    UPDATE = "update"
    DELETE = "delete"
    MIGRATE = "migrate"


class Hcs2RegistryType(IntEnum):
    INDEXED = 0
    NON_INDEXED = 1


class Hcs2Message(_Hcs2Model):
    p: str
    op: Hcs2Operation
    t_id: str | None = None
    uid: str | None = None
    metadata: str | None = None
    m: str | None = None
    ttl: int | None = None


class Hcs2RegisterMessage(Hcs2Message):
    op: Literal[Hcs2Operation.REGISTER] = Hcs2Operation.REGISTER
    t_id: str


class Hcs2UpdateMessage(Hcs2Message):
    op: Literal[Hcs2Operation.UPDATE] = Hcs2Operation.UPDATE
    uid: str
    t_id: str


class Hcs2DeleteMessage(Hcs2Message):
    op: Literal[Hcs2Operation.DELETE] = Hcs2Operation.DELETE
    uid: str


class Hcs2MigrateMessage(Hcs2Message):
    op: Literal[Hcs2Operation.MIGRATE] = Hcs2Operation.MIGRATE
    t_id: str


class CreateRegistryOptions(_Hcs2Model):
    registry_type: Hcs2RegistryType = Field(default=Hcs2RegistryType.INDEXED, alias="registryType")
    ttl: int = 86400
    admin_key: str | bool | None = Field(default=None, alias="adminKey")
    submit_key: str | bool | None = Field(default=None, alias="submitKey")
    use_operator_as_admin: bool = Field(default=False, alias="useOperatorAsAdmin")
    use_operator_as_submit: bool = Field(default=False, alias="useOperatorAsSubmit")
    memo_override: str | None = Field(default=None, alias="memoOverride")
    transaction_memo: str | None = Field(default=None, alias="transactionMemo")


class RegisterEntryOptions(_Hcs2Model):
    target_topic_id: str = Field(alias="targetTopicId")
    metadata: str | None = None
    memo: str | None = None
    analytics_memo: str | None = Field(default=None, alias="analyticsMemo")
    registry_type: Hcs2RegistryType | None = Field(default=None, alias="registryType")


class UpdateEntryOptions(_Hcs2Model):
    target_topic_id: str = Field(alias="targetTopicId")
    uid: str
    metadata: str | None = None
    memo: str | None = None
    analytics_memo: str | None = Field(default=None, alias="analyticsMemo")
    registry_type: Hcs2RegistryType | None = Field(default=None, alias="registryType")


class DeleteEntryOptions(_Hcs2Model):
    uid: str
    memo: str | None = None
    analytics_memo: str | None = Field(default=None, alias="analyticsMemo")
    registry_type: Hcs2RegistryType | None = Field(default=None, alias="registryType")


class MigrateRegistryOptions(_Hcs2Model):
    target_topic_id: str = Field(alias="targetTopicId")
    metadata: str | None = None
    memo: str | None = None
    analytics_memo: str | None = Field(default=None, alias="analyticsMemo")
    registry_type: Hcs2RegistryType | None = Field(default=None, alias="registryType")


class QueryRegistryOptions(_Hcs2Model):
    limit: int = 100
    order: Literal["asc", "desc"] = "asc"
    skip: int = 0
    resolve_overflow: bool = Field(default=False, alias="resolveOverflow")


class CreateRegistryResult(_Hcs2Model):
    success: bool
    topic_id: str | None = Field(default=None, alias="topicId")
    transaction_id: str | None = Field(default=None, alias="transactionId")
    error: str | None = None


class OperationResult(_Hcs2Model):
    success: bool
    transaction_id: str | None = Field(default=None, alias="transactionId")
    sequence_number: int | None = Field(default=None, alias="sequenceNumber")
    error: str | None = None


class RegistryEntry(_Hcs2Model):
    topic_id: str = Field(alias="topicId")
    sequence: int
    timestamp: str
    payer: str
    message: Hcs2Message
    consensus_timestamp: str = Field(alias="consensus_timestamp")
    registry_type: Hcs2RegistryType = Field(alias="registry_type")


class TopicRegistry(_Hcs2Model):
    topic_id: str = Field(alias="topicId")
    registry_type: Hcs2RegistryType = Field(alias="registryType")
    ttl: int
    entries: list[RegistryEntry]
    latest_entry: RegistryEntry | None = Field(default=None, alias="latestEntry")
