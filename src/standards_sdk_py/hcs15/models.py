"""Typed request/response models for HCS-15 operations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Hcs15Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Hcs15CreateBaseAccountOptions(_Hcs15Model):
    initial_balance: float = Field(default=10.0, alias="initialBalance")
    max_automatic_token_associations: int | None = Field(
        default=None, alias="maxAutomaticTokenAssociations"
    )
    account_memo: str | None = Field(default=None, alias="accountMemo")
    transaction_memo: str | None = Field(default=None, alias="transactionMemo")


class Hcs15CreatePetalAccountOptions(_Hcs15Model):
    base_private_key: str = Field(alias="basePrivateKey")
    initial_balance: float = Field(default=1.0, alias="initialBalance")
    max_automatic_token_associations: int | None = Field(
        default=None, alias="maxAutomaticTokenAssociations"
    )
    account_memo: str | None = Field(default=None, alias="accountMemo")
    transaction_memo: str | None = Field(default=None, alias="transactionMemo")


class Hcs15BaseAccountCreateResult(_Hcs15Model):
    account_id: str = Field(alias="accountId")
    private_key: str = Field(alias="privateKey")
    private_key_hex: str = Field(alias="privateKeyHex")
    public_key: str = Field(alias="publicKey")
    evm_address: str = Field(alias="evmAddress")
    transaction_id: str | None = Field(default=None, alias="transactionId")


class Hcs15PetalAccountCreateResult(_Hcs15Model):
    account_id: str = Field(alias="accountId")
    transaction_id: str | None = Field(default=None, alias="transactionId")
