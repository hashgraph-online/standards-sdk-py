"""Typed request/response models for HCS-18 operations."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class _Hcs18Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Hcs18DiscoveryOperation(StrEnum):
    ANNOUNCE = "announce"
    PROPOSE = "propose"
    RESPOND = "respond"
    COMPLETE = "complete"
    WITHDRAW = "withdraw"


class Hcs18DiscoveryMessage(_Hcs18Model):
    p: str = "hcs-18"
    op: Hcs18DiscoveryOperation
    data: dict[str, object]


class Hcs18CreateDiscoveryTopicOptions(_Hcs18Model):
    ttl_seconds: int = Field(default=86400, alias="ttlSeconds")
    admin_key: str | bool | None = Field(default=None, alias="adminKey")
    submit_key: str | bool | None = Field(default=None, alias="submitKey")
    use_operator_as_admin: bool = Field(default=False, alias="useOperatorAsAdmin")
    use_operator_as_submit: bool = Field(default=False, alias="useOperatorAsSubmit")
    memo_override: str | None = Field(default=None, alias="memoOverride")


class Hcs18CreateDiscoveryTopicResult(_Hcs18Model):
    topic_id: str = Field(alias="topicId")
    transaction_id: str | None = Field(default=None, alias="transactionId")


class Hcs18OperationResult(_Hcs18Model):
    success: bool
    transaction_id: str | None = Field(default=None, alias="transactionId")
    sequence_number: int | None = Field(default=None, alias="sequenceNumber")
    error: str | None = None
