"""Typed models for common Registry Broker responses."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RegistryBrokerResponse(BaseModel):
    """Fallback base response model."""

    model_config = ConfigDict(extra="allow")


class SearchHit(BaseModel):
    """Search hit model."""

    model_config = ConfigDict(extra="allow")

    uaid: str | None = None
    score: float | None = None


class SearchResponse(RegistryBrokerResponse):
    """Search response model."""

    hits: list[dict[str, object]] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    limit: int = 20


class ProtocolsResponse(RegistryBrokerResponse):
    """Protocols response model."""

    protocols: list[dict[str, object]] = Field(default_factory=list)


class RegistriesResponse(RegistryBrokerResponse):
    """Registries response model."""

    registries: list[dict[str, object]] = Field(default_factory=list)


class StatsResponse(RegistryBrokerResponse):
    """Registry stats response model."""

    total_agents: int | None = None
    active_agents: int | None = None


class CreateSessionResponse(RegistryBrokerResponse):
    """Chat session response model."""

    session_id: str = Field(alias="sessionId")
    encryption: dict[str, object] | None = None


class SendMessageResponse(RegistryBrokerResponse):
    """Chat send response model."""

    session_id: str | None = Field(default=None, alias="sessionId")
    message_id: str | None = Field(default=None, alias="messageId")


class RegistrationProgressResponse(RegistryBrokerResponse):
    """Registration progress response model."""

    status: str | None = None
    attempt_id: str | None = Field(default=None, alias="attemptId")
    uaid: str | None = None


class VerificationStatusResponse(RegistryBrokerResponse):
    """Verification status response model."""

    verified: bool | None = None
    method: str | None = None


class SkillPublishResponse(RegistryBrokerResponse):
    """Skill publish response model."""

    job_id: str | None = Field(default=None, alias="jobId")
    accepted: bool | None = None
