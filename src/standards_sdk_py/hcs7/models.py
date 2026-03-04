"""Typed request/response models for HCS-7 operations."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Hcs7Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Hcs7Operation(StrEnum):
    REGISTER_CONFIG = "register-config"
    REGISTER = "register"


class Hcs7ConfigType(StrEnum):
    EVM = "evm"
    WASM = "wasm"


class AbiIo(_Hcs7Model):
    name: str | None = None
    type: str


class AbiDefinition(_Hcs7Model):
    name: str
    inputs: list[AbiIo]
    outputs: list[AbiIo]
    state_mutability: str = Field(alias="stateMutability")
    type: str


class EvmConfigPayload(_Hcs7Model):
    contract_address: str = Field(alias="contractAddress")
    abi: AbiDefinition


class WasmInputType(_Hcs7Model):
    state_data: dict[str, str] = Field(alias="stateData")


class WasmOutputType(_Hcs7Model):
    type: str
    format: str


class WasmConfigPayload(_Hcs7Model):
    wasm_topic_id: str = Field(alias="wasmTopicId")
    input_type: WasmInputType = Field(alias="inputType")
    output_type: WasmOutputType = Field(alias="outputType")


class Hcs7Message(_Hcs7Model):
    p: Literal["hcs-7"] = "hcs-7"
    op: Hcs7Operation
    t: Hcs7ConfigType | None = None
    c: dict[str, object] | None = None
    t_id: str | None = None
    d: dict[str, object] | None = None
    m: str | None = None


class Hcs7CreateRegistryOptions(_Hcs7Model):
    ttl: int = 86400
    admin_key: str | bool | None = Field(default=None, alias="adminKey")
    submit_key: str | bool | None = Field(default=None, alias="submitKey")
    use_operator_as_admin: bool = Field(default=False, alias="useOperatorAsAdmin")
    use_operator_as_submit: bool = Field(default=False, alias="useOperatorAsSubmit")


class Hcs7RegisterConfigOptions(_Hcs7Model):
    registry_topic_id: str = Field(alias="registryTopicId")
    type: Hcs7ConfigType
    evm: EvmConfigPayload | None = None
    wasm: WasmConfigPayload | None = None
    memo: str | None = None
    analytics_memo: str | None = Field(default=None, alias="analyticsMemo")
    submit_key: str | None = Field(default=None, alias="submitKey")


class Hcs7RegisterMetadataOptions(_Hcs7Model):
    registry_topic_id: str = Field(alias="registryTopicId")
    metadata_topic_id: str = Field(alias="metadataTopicId")
    weight: int
    tags: list[str]
    data: dict[str, object] = Field(default_factory=dict)
    memo: str | None = None
    analytics_memo: str | None = Field(default=None, alias="analyticsMemo")
    submit_key: str | None = Field(default=None, alias="submitKey")


class Hcs7QueryRegistryOptions(_Hcs7Model):
    limit: int = 100
    order: Literal["asc", "desc"] = "asc"
    skip: int = 0


class Hcs7RegistryOperationResult(_Hcs7Model):
    success: bool
    transaction_id: str | None = Field(default=None, alias="transactionId")
    sequence_number: int | None = Field(default=None, alias="sequenceNumber")
    error: str | None = None


class Hcs7RegistryEntry(_Hcs7Model):
    sequence_number: int = Field(alias="sequenceNumber")
    timestamp: str
    payer: str
    message: Hcs7Message


class Hcs7RegistryTopic(_Hcs7Model):
    topic_id: str = Field(alias="topicId")
    ttl: int
    entries: list[Hcs7RegistryEntry]


class Hcs7CreateRegistryResult(_Hcs7Model):
    success: bool
    topic_id: str | None = Field(default=None, alias="topicId")
    transaction_id: str | None = Field(default=None, alias="transactionId")
    error: str | None = None
