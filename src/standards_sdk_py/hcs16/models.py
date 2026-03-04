"""Typed request/response models for HCS-16 operations."""

from __future__ import annotations

from enum import IntEnum, StrEnum

from pydantic import BaseModel, ConfigDict, Field


class _Hcs16Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class FloraTopicType(IntEnum):
    COMMUNICATION = 0
    TRANSACTION = 1
    STATE = 2


class FloraOperation(StrEnum):
    FLORA_CREATED = "flora_created"
    TRANSACTION = "transaction"
    STATE_UPDATE = "state_update"
    FLORA_JOIN_REQUEST = "flora_join_request"
    FLORA_JOIN_VOTE = "flora_join_vote"
    FLORA_JOIN_ACCEPTED = "flora_join_accepted"


class Hcs16KeyList(_Hcs16Model):
    keys: list[str]
    threshold: int = 1


class Hcs16FloraTopics(_Hcs16Model):
    communication: str
    transaction: str
    state: str


class Hcs16FloraMember(_Hcs16Model):
    account_id: str = Field(alias="accountId")
    public_key: str | None = Field(default=None, alias="publicKey")
    weight: int | None = None


class Hcs16AssembleKeyListOptions(_Hcs16Model):
    members: list[str]
    threshold: int


class Hcs16CreateFloraAccountOptions(_Hcs16Model):
    key_list: Hcs16KeyList | list[str] | dict[str, object] = Field(alias="keyList")
    initial_balance_hbar: float | None = Field(default=None, alias="initialBalanceHbar")
    max_automatic_token_associations: int | None = Field(
        default=None, alias="maxAutomaticTokenAssociations"
    )


class Hcs16CreateFloraTopicOptions(_Hcs16Model):
    flora_account_id: str = Field(alias="floraAccountId")
    topic_type: FloraTopicType = Field(alias="topicType")
    admin_key: Hcs16KeyList | str | bool | dict[str, object] | None = Field(
        default=None, alias="adminKey"
    )
    submit_key: Hcs16KeyList | str | bool | dict[str, object] | None = Field(
        default=None, alias="submitKey"
    )
    auto_renew_account_id: str | None = Field(default=None, alias="autoRenewAccountId")
    signer_keys: list[str] | None = Field(default=None, alias="signerKeys")
    transaction_memo: str | None = Field(default=None, alias="transactionMemo")


class Hcs16CreateFloraAccountWithTopicsOptions(_Hcs16Model):
    members: list[str]
    threshold: int
    initial_balance_hbar: float | None = Field(default=None, alias="initialBalanceHbar")
    auto_renew_account_id: str | None = Field(default=None, alias="autoRenewAccountId")


class Hcs16SendFloraCreatedOptions(_Hcs16Model):
    topic_id: str = Field(alias="topicId")
    operator_id: str = Field(alias="operatorId")
    flora_account_id: str = Field(alias="floraAccountId")
    topics: Hcs16FloraTopics


class Hcs16SendTransactionOptions(_Hcs16Model):
    topic_id: str = Field(alias="topicId")
    operator_id: str = Field(alias="operatorId")
    schedule_id: str = Field(alias="scheduleId")
    data: str | None = None


class Hcs16SendStateUpdateOptions(_Hcs16Model):
    topic_id: str = Field(alias="topicId")
    operator_id: str = Field(alias="operatorId")
    hash: str
    epoch: int | None = None
    account_id: str | None = Field(default=None, alias="accountId")
    topics: list[str] | None = None
    memo: str | None = None
    transaction_memo: str | None = Field(default=None, alias="transactionMemo")
    signer_keys: list[str] | None = Field(default=None, alias="signerKeys")


class Hcs16SendFloraJoinRequestOptions(_Hcs16Model):
    topic_id: str = Field(alias="topicId")
    operator_id: str = Field(alias="operatorId")
    account_id: str = Field(alias="accountId")
    connection_request_id: int = Field(alias="connectionRequestId")
    connection_topic_id: str = Field(alias="connectionTopicId")
    connection_seq: int = Field(alias="connectionSeq")
    signer_key: str | None = Field(default=None, alias="signerKey")


class Hcs16SendFloraJoinVoteOptions(_Hcs16Model):
    topic_id: str = Field(alias="topicId")
    operator_id: str = Field(alias="operatorId")
    account_id: str = Field(alias="accountId")
    approve: bool
    connection_request_id: int = Field(alias="connectionRequestId")
    connection_seq: int = Field(alias="connectionSeq")
    signer_key: str | None = Field(default=None, alias="signerKey")


class Hcs16SendFloraJoinAcceptedOptions(_Hcs16Model):
    topic_id: str = Field(alias="topicId")
    operator_id: str = Field(alias="operatorId")
    members: list[str]
    epoch: int | None = None
    signer_keys: list[str] | None = Field(default=None, alias="signerKeys")


class Hcs16SignScheduleOptions(_Hcs16Model):
    schedule_id: str = Field(alias="scheduleId")
    signer_key: str = Field(alias="signerKey")


class Hcs16CreateFloraProfileOptions(_Hcs16Model):
    flora_account_id: str = Field(alias="floraAccountId")
    display_name: str = Field(alias="displayName")
    members: list[Hcs16FloraMember]
    threshold: int
    topics: Hcs16FloraTopics
    inbound_topic_id: str | None = Field(default=None, alias="inboundTopicId")
    outbound_topic_id: str | None = Field(default=None, alias="outboundTopicId")
    bio: str | None = None
    metadata: dict[str, object] | None = None
    policies: dict[str, str] | None = None
    signer_keys: list[str] = Field(alias="signerKeys")
    inscription_options: dict[str, object] | None = Field(default=None, alias="inscriptionOptions")


class Hcs16TopicMemoParseResult(_Hcs16Model):
    protocol: str
    flora_account_id: str = Field(alias="floraAccountId")
    topic_type: FloraTopicType = Field(alias="topicType")


class Hcs16CreateFloraAccountResult(_Hcs16Model):
    account_id: str = Field(alias="accountId")
    transaction_id: str = Field(alias="transactionId")


class Hcs16CreateFloraAccountWithTopicsResult(_Hcs16Model):
    flora_account_id: str = Field(alias="floraAccountId")
    topics: Hcs16FloraTopics


class Hcs16TransactionResult(_Hcs16Model):
    transaction_id: str = Field(alias="transactionId")
    sequence_number: int | None = Field(default=None, alias="sequenceNumber")
    topic_id: str | None = Field(default=None, alias="topicId")


class Hcs16CreateFloraProfileResult(_Hcs16Model):
    profile_topic_id: str = Field(alias="profileTopicId")
    transaction_id: str = Field(alias="transactionId")
