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
    label: str | None = None
    score: float | None = None
    metadata: SearchHitMetadata | None = None

    def _mapping_payload(self) -> dict[str, object]:
        payload = self.model_dump(by_alias=True, exclude_unset=True)
        extras = self.model_extra or {}
        if extras:
            payload.update(extras)
        return payload

    def __getitem__(self, key: str) -> object:
        payload = self._mapping_payload()
        return payload[key]

    def get(self, key: str, default: object | None = None) -> object | None:
        payload = self._mapping_payload()
        return payload.get(key, default)

    def keys(self) -> list[str]:
        payload = self._mapping_payload()
        return list(payload.keys())

    def items(self) -> list[tuple[str, object]]:
        payload = self._mapping_payload()
        return list(payload.items())

    def values(self) -> list[object]:
        payload = self._mapping_payload()
        return list(payload.values())


class SearchHitMetadata(RegistryBrokerResponse):
    """Structured search hit metadata for delegation-aware broker responses."""

    delegation_roles: list[str] = Field(default_factory=list, alias="delegationRoles")
    delegation_task_tags: list[str] = Field(default_factory=list, alias="delegationTaskTags")
    delegation_protocols: list[str] = Field(default_factory=list, alias="delegationProtocols")
    delegation_summary: str | None = Field(default=None, alias="delegationSummary")
    delegation_signals: dict[str, object] = Field(default_factory=dict, alias="delegationSignals")


class SearchResponse(RegistryBrokerResponse):
    """Search response model."""

    hits: list[SearchHit] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    limit: int = 20


class DelegationPlanCandidate(RegistryBrokerResponse):
    """Delegation candidate returned by the planner."""

    uaid: str
    label: str | None = None
    registry: str | None = None
    agent: dict[str, object] = Field(default_factory=dict)
    score: float | None = None
    trust_score: float | None = Field(default=None, alias="trustScore")
    verified: bool | None = None
    communication_supported: bool | None = Field(default=None, alias="communicationSupported")
    availability: str | None = None
    explanation: str | None = None
    matched_queries: list[str] = Field(default_factory=list, alias="matchedQueries")
    matched_roles: list[str] = Field(default_factory=list, alias="matchedRoles")
    matched_protocols: list[str] = Field(default_factory=list, alias="matchedProtocols")
    matched_surfaces: list[str] = Field(default_factory=list, alias="matchedSurfaces")
    matched_languages: list[str] = Field(default_factory=list, alias="matchedLanguages")
    matched_artifacts: list[str] = Field(default_factory=list, alias="matchedArtifacts")
    matched_task_tags: list[str] = Field(default_factory=list, alias="matchedTaskTags")
    reasons: list[str] = Field(default_factory=list)
    suggested_message: str | None = Field(default=None, alias="suggestedMessage")


class DelegationOpportunity(RegistryBrokerResponse):
    """Recommended delegation opportunity for a subtask."""

    id: str
    title: str
    reason: str
    role: str | None = None
    type: str | None = None
    suggested_mode: str | None = Field(default=None, alias="suggestedMode")
    search_queries: list[str] = Field(default_factory=list, alias="searchQueries")
    protocols: list[str] = Field(default_factory=list)
    surfaces: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    candidates: list[DelegationPlanCandidate] = Field(default_factory=list)


class DelegationPlanRecommendation(RegistryBrokerResponse):
    """Top-level delegation recommendation payload."""

    summary: str | None = None
    mode: str | None = None


class DelegationPlanResponse(RegistryBrokerResponse):
    """Typed delegation planner response."""

    task: str
    context: str | None = None
    summary: str | None = None
    intents: list[str] = Field(default_factory=list)
    surfaces: list[str] = Field(default_factory=list)
    protocols: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    should_delegate: bool = Field(default=False, alias="shouldDelegate")
    local_first_reason: str | None = Field(default=None, alias="localFirstReason")
    recommendation: DelegationPlanRecommendation | None = None
    opportunities: list[DelegationOpportunity] = Field(default_factory=list)


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
