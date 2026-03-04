"""Typed request/response models for HCS-17 operations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Hcs17Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Hcs17StateHashMessage(_Hcs17Model):
    p: Literal["hcs-17"] = "hcs-17"
    op: Literal["state_hash"] = "state_hash"
    state_hash: str = Field(alias="state_hash")
    topics: list[str]
    account_id: str = Field(alias="account_id")
    epoch: int | None = None
    timestamp: str | None = None
    m: str | None = None


class Hcs17CreateTopicOptions(_Hcs17Model):
    ttl: int = 86400
    admin_key: str | bool | None = Field(default=None, alias="adminKey")
    submit_key: str | bool | None = Field(default=None, alias="submitKey")
    use_operator_as_admin: bool = Field(default=False, alias="useOperatorAsAdmin")
    use_operator_as_submit: bool = Field(default=False, alias="useOperatorAsSubmit")
    transaction_memo: str | None = Field(default=None, alias="transactionMemo")


class Hcs17ComputeAndPublishOptions(_Hcs17Model):
    account_id: str = Field(alias="accountId")
    account_public_key: str = Field(alias="accountPublicKey")
    topics: list[str]
    publish_topic_id: str = Field(alias="publishTopicId")
    memo: str | None = None


class Hcs17SubmitMessageOptions(_Hcs17Model):
    topic_id: str = Field(alias="topicId")
    message: Hcs17StateHashMessage
    transaction_memo: str | None = Field(default=None, alias="transactionMemo")


class Hcs17SubmitMessageResult(_Hcs17Model):
    success: bool
    transaction_id: str | None = Field(default=None, alias="transactionId")
    sequence_number: int | None = Field(default=None, alias="sequenceNumber")
    error: str | None = None


class Hcs17ComputeAndPublishResult(_Hcs17Model):
    state_hash: str = Field(alias="stateHash")
    transaction_id: str | None = Field(default=None, alias="transactionId")
    sequence_number: int | None = Field(default=None, alias="sequenceNumber")
