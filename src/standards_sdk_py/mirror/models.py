"""Mirror node typed models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MirrorTopicMessage(BaseModel):
    """Mirror topic message representation."""

    model_config = ConfigDict(extra="allow")

    consensus_timestamp: str = Field(alias="consensus_timestamp")
    message: str
    running_hash: str | None = Field(default=None, alias="running_hash")
    sequence_number: int | None = Field(default=None, alias="sequence_number")


class MirrorTopicMessagesResponse(BaseModel):
    """Topic messages response."""

    model_config = ConfigDict(extra="allow")

    messages: list[MirrorTopicMessage]
    links: dict[str, str | None] = Field(default_factory=dict)
