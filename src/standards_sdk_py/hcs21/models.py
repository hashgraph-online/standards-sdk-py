"""Typed request/response models for HCS-21 operations."""

from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class _Hcs21Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Hcs21Operation(StrEnum):
    REGISTER = "register"
    UPDATE = "update"
    DELETE = "delete"


class Hcs21TopicType(IntEnum):
    ADAPTER_REGISTRY = 0
    REGISTRY_OF_REGISTRIES = 1
    ADAPTER_CATEGORY = 2


class Hcs21AdapterPackage(_Hcs21Model):
    registry: str = Field(min_length=1)
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    integrity: str = Field(min_length=1)


class Hcs21BuildDeclarationParams(_Hcs21Model):
    op: Hcs21Operation
    adapter_id: str = Field(
        alias="adapter_id",
        validation_alias=AliasChoices("adapter_id", "adapterId"),
        min_length=1,
    )
    entity: str = Field(min_length=1)
    package: Hcs21AdapterPackage = Field(
        alias="package",
        validation_alias=AliasChoices("package", "adapterPackage"),
    )
    manifest: str = Field(min_length=1)
    manifest_sequence: int | None = Field(
        default=None,
        alias="manifest_sequence",
        validation_alias=AliasChoices("manifest_sequence", "manifestSequence"),
    )
    config: dict[str, object]
    state_model: str | None = Field(
        default=None,
        alias="state_model",
        validation_alias=AliasChoices("state_model", "stateModel"),
    )
    signature: str | None = None


class Hcs21AdapterDeclaration(_Hcs21Model):
    p: Literal["hcs-21"] = "hcs-21"
    op: Hcs21Operation
    adapter_id: str = Field(
        alias="adapter_id",
        validation_alias=AliasChoices("adapter_id", "adapterId"),
        min_length=1,
    )
    entity: str = Field(min_length=1)
    package: Hcs21AdapterPackage
    manifest: str = Field(min_length=1)
    manifest_sequence: int | None = Field(
        default=None,
        alias="manifest_sequence",
        validation_alias=AliasChoices("manifest_sequence", "manifestSequence"),
    )
    config: dict[str, object]
    state_model: str | None = Field(
        default=None,
        alias="state_model",
        validation_alias=AliasChoices("state_model", "stateModel"),
    )
    signature: str | None = None


class Hcs21CreateRegistryTopicOptions(_Hcs21Model):
    ttl: int = 86400
    indexed: int | bool = 0
    topic_type: Hcs21TopicType = Field(
        default=Hcs21TopicType.ADAPTER_REGISTRY,
        alias="type",
        validation_alias=AliasChoices("type", "topicType"),
    )
    meta_topic_id: str | None = Field(
        default=None,
        alias="metaTopicId",
    )
    admin_key: str | bool | None = Field(default=None, alias="adminKey")
    submit_key: str | bool | None = Field(default=None, alias="submitKey")
    use_operator_as_admin: bool = Field(default=False, alias="useOperatorAsAdmin")
    use_operator_as_submit: bool = Field(default=False, alias="useOperatorAsSubmit")
    transaction_memo: str | None = Field(default=None, alias="transactionMemo")


class Hcs21CreateAdapterVersionPointerTopicOptions(_Hcs21Model):
    ttl: int = 86400
    admin_key: str | bool | None = Field(default=None, alias="adminKey")
    submit_key: str | bool | None = Field(default=None, alias="submitKey")
    use_operator_as_admin: bool = Field(default=False, alias="useOperatorAsAdmin")
    use_operator_as_submit: bool = Field(default=False, alias="useOperatorAsSubmit")
    transaction_memo: str | None = Field(default=None, alias="transactionMemo")
    memo_override: str | None = Field(default=None, alias="memoOverride")


class Hcs21CreateRegistryDiscoveryTopicOptions(_Hcs21Model):
    ttl: int = 86400
    admin_key: str | bool | None = Field(default=None, alias="adminKey")
    submit_key: str | bool | None = Field(default=None, alias="submitKey")
    use_operator_as_admin: bool = Field(default=False, alias="useOperatorAsAdmin")
    use_operator_as_submit: bool = Field(default=False, alias="useOperatorAsSubmit")
    transaction_memo: str | None = Field(default=None, alias="transactionMemo")
    memo_override: str | None = Field(default=None, alias="memoOverride")


class Hcs21CreateAdapterCategoryTopicOptions(_Hcs21Model):
    ttl: int = 86400
    indexed: int | bool = 0
    meta_topic_id: str | None = Field(default=None, alias="metaTopicId")
    admin_key: str | bool | None = Field(default=None, alias="adminKey")
    submit_key: str | bool | None = Field(default=None, alias="submitKey")
    use_operator_as_admin: bool = Field(default=False, alias="useOperatorAsAdmin")
    use_operator_as_submit: bool = Field(default=False, alias="useOperatorAsSubmit")
    transaction_memo: str | None = Field(default=None, alias="transactionMemo")


class Hcs21PublishDeclarationOptions(_Hcs21Model):
    topic_id: str = Field(alias="topicId")
    declaration: Hcs21AdapterDeclaration | Hcs21BuildDeclarationParams | dict[str, object]
    transaction_memo: str | None = Field(default=None, alias="transactionMemo")


class Hcs21PublishVersionPointerOptions(_Hcs21Model):
    version_topic_id: str = Field(alias="versionTopicId")
    declaration_topic_id: str = Field(alias="declarationTopicId")
    memo: str | None = None
    transaction_memo: str | None = Field(default=None, alias="transactionMemo")


class Hcs21RegisterCategoryTopicOptions(_Hcs21Model):
    discovery_topic_id: str = Field(alias="discoveryTopicId")
    category_topic_id: str = Field(alias="categoryTopicId")
    metadata: str | None = None
    memo: str | None = None
    transaction_memo: str | None = Field(default=None, alias="transactionMemo")


class Hcs21PublishCategoryEntryOptions(_Hcs21Model):
    category_topic_id: str = Field(alias="categoryTopicId")
    adapter_id: str = Field(alias="adapterId")
    version_topic_id: str = Field(alias="versionTopicId")
    metadata: str | None = None
    memo: str | None = None
    transaction_memo: str | None = Field(default=None, alias="transactionMemo")


class Hcs21InscribeMetadataOptions(_Hcs21Model):
    document: dict[str, object]
    file_name: str | None = Field(default=None, alias="fileName")
    inscription_options: dict[str, object] | None = Field(default=None, alias="inscriptionOptions")


class Hcs21CreateTopicResult(_Hcs21Model):
    topic_id: str = Field(alias="topicId")
    transaction_id: str | None = Field(default=None, alias="transactionId")


class Hcs21PublishResult(_Hcs21Model):
    sequence_number: int = Field(alias="sequenceNumber")
    transaction_id: str = Field(alias="transactionId")
    topic_id: str = Field(alias="topicId")


class Hcs21VersionPointerResolution(_Hcs21Model):
    version_topic_id: str = Field(alias="versionTopicId")
    declaration_topic_id: str = Field(alias="declarationTopicId")
    sequence_number: int = Field(alias="sequenceNumber")
    payer: str | None = None
    memo: str | None = None
    op: str | None = None


class Hcs21ManifestPointer(_Hcs21Model):
    pointer: str
    topic_id: str = Field(alias="topicId")
    sequence_number: int = Field(alias="sequenceNumber")
    manifest_sequence: int | None = Field(default=None, alias="manifestSequence")
    job_id: str | None = Field(default=None, alias="jobId")
    transaction_id: str | None = Field(default=None, alias="transactionId")
    total_cost_hbar: str | None = Field(default=None, alias="totalCostHbar")
