"""Typed request/response models for HCS-20 operations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Hcs20Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Hcs20DeployPointsOptions(_Hcs20Model):
    name: str
    tick: str
    max_supply: str = Field(alias="maxSupply")
    limit_per_mint: str | None = Field(default=None, alias="limitPerMint")
    metadata: str | None = None
    memo: str | None = None
    topic_memo: str | None = Field(default=None, alias="topicMemo")
    use_private_topic: bool = Field(default=False, alias="usePrivateTopic")
    topic_id: str | None = Field(default=None, alias="topicId")


class Hcs20MintPointsOptions(_Hcs20Model):
    tick: str
    amount: str
    to: str
    memo: str | None = None
    topic_id: str | None = Field(default=None, alias="topicId")


class Hcs20TransferPointsOptions(_Hcs20Model):
    tick: str
    amount: str
    from_account: str = Field(alias="from")
    to: str
    memo: str | None = None
    topic_id: str | None = Field(default=None, alias="topicId")


class Hcs20BurnPointsOptions(_Hcs20Model):
    tick: str
    amount: str
    from_account: str = Field(alias="from")
    memo: str | None = None
    topic_id: str | None = Field(default=None, alias="topicId")


class Hcs20RegisterTopicOptions(_Hcs20Model):
    topic_id: str = Field(alias="topicId")
    name: str
    metadata: str | None = None
    is_private: bool = Field(alias="isPrivate")
    memo: str | None = None


class Hcs20CreateTopicOptions(_Hcs20Model):
    memo: str | None = None
    admin_key: str | bool | None = Field(default=None, alias="adminKey")
    submit_key: str | bool | None = Field(default=None, alias="submitKey")
    use_operator_as_admin: bool = Field(default=False, alias="useOperatorAsAdmin")
    use_operator_as_submit: bool = Field(default=False, alias="useOperatorAsSubmit")


class Hcs20PointsInfo(_Hcs20Model):
    name: str
    tick: str
    max_supply: str = Field(alias="maxSupply")
    limit_per_mint: str | None = Field(default=None, alias="limitPerMint")
    metadata: str | None = None
    topic_id: str = Field(alias="topicId")
    deployer_account_id: str = Field(alias="deployerAccountId")
    current_supply: str = Field(alias="currentSupply")
    deployment_timestamp: str = Field(alias="deploymentTimestamp")
    is_private: bool = Field(alias="isPrivate")


class Hcs20PointsTransaction(_Hcs20Model):
    id: str
    operation: str
    tick: str
    amount: str | None = None
    from_account: str | None = Field(default=None, alias="from")
    to: str | None = None
    timestamp: str
    sequence_number: int = Field(alias="sequenceNumber")
    topic_id: str = Field(alias="topicId")
    transaction_id: str = Field(alias="transactionId")
    memo: str | None = None
