"""Registry Broker operation specifications."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class OperationSpec:
    """HTTP operation metadata for dynamic dispatch."""

    method: str
    path: str
    text_response: bool = False


REGISTRY_BROKER_OPERATIONS: dict[str, OperationSpec] = {
    "get_agent_feedback": OperationSpec("GET", "/agents/{uaid}/feedback"),
    "list_agent_feedback_index": OperationSpec("GET", "/agents/feedback"),
    "list_agent_feedback_entries_index": OperationSpec("GET", "/agents/feedback/entries"),
    "check_agent_feedback_eligibility": OperationSpec(
        "POST",
        "/agents/{uaid}/feedback/eligibility",
    ),
    "submit_agent_feedback": OperationSpec("POST", "/agents/{uaid}/feedback"),
    "search": OperationSpec("GET", "/search"),
    "delegate": OperationSpec("POST", "/delegate"),
    "stats": OperationSpec("GET", "/stats"),
    "registries": OperationSpec("GET", "/registries"),
    "get_additional_registries": OperationSpec("GET", "/register/additional-registries"),
    "popular_searches": OperationSpec("GET", "/popular"),
    "list_protocols": OperationSpec("GET", "/protocols"),
    "detect_protocol": OperationSpec("POST", "/detect-protocol"),
    "registry_search_by_namespace": OperationSpec("GET", "/registries/{registry}/search"),
    "vector_search": OperationSpec("POST", "/search"),
    "search_status": OperationSpec("GET", "/search/status"),
    "websocket_stats": OperationSpec("GET", "/websocket/stats"),
    "metrics_summary": OperationSpec("GET", "/metrics"),
    "facets": OperationSpec("GET", "/search/facets"),
    "resolve_uaid": OperationSpec("GET", "/resolve/{uaid}"),
    "register_agent": OperationSpec("POST", "/register"),
    "get_registration_quote": OperationSpec("POST", "/register/quote"),
    "update_agent": OperationSpec("PUT", "/register/{uaid}"),
    "get_registration_progress": OperationSpec("GET", "/register/progress/{attempt_id}"),
    "wait_for_registration_completion": OperationSpec("GET", "/register/progress/{attempt_id}"),
    "validate_uaid": OperationSpec("GET", "/uaids/validate/{uaid}"),
    "get_uaid_connection_status": OperationSpec("GET", "/uaids/connections/{uaid}/status"),
    "close_uaid_connection": OperationSpec("DELETE", "/uaids/connections/{uaid}"),
    "dashboard_stats": OperationSpec("GET", "/dashboard/stats"),
    "create_session": OperationSpec("POST", "/chat/session"),
    "send_message": OperationSpec("POST", "/chat/message"),
    "end_session": OperationSpec("DELETE", "/chat/session/{session_id}"),
    "fetch_history_snapshot": OperationSpec("GET", "/chat/session/{session_id}/history"),
    "compact_history": OperationSpec("POST", "/chat/session/{session_id}/compact"),
    "fetch_encryption_status": OperationSpec("GET", "/chat/session/{session_id}/encryption"),
    "post_encryption_handshake": OperationSpec(
        "POST",
        "/chat/session/{session_id}/encryption-handshake",
    ),
    "register_encryption_key": OperationSpec("POST", "/encryption/keys"),
    "create_ledger_challenge": OperationSpec("POST", "/auth/ledger/challenge"),
    "verify_ledger_challenge": OperationSpec("POST", "/auth/ledger/verify"),
    "get_verification_status": OperationSpec("GET", "/verification/status/{uaid}"),
    "create_verification_challenge": OperationSpec("POST", "/verification/challenge"),
    "get_verification_challenge": OperationSpec("GET", "/verification/challenge/{challenge_id}"),
    "verify_verification_challenge": OperationSpec("POST", "/verification/verify"),
    "get_verification_ownership": OperationSpec("GET", "/verification/ownership/{uaid}"),
    "verify_sender_ownership": OperationSpec("POST", "/verification/verify-sender"),
    "verify_uaid_dns_txt": OperationSpec("POST", "/verification/dns/verify"),
    "get_verification_dns_status": OperationSpec("GET", "/verification/dns/status/{uaid}"),
    "get_register_status": OperationSpec("GET", "/register/status/{uaid}"),
    "register_owned_moltbook_agent": OperationSpec("PUT", "/register/{uaid}"),
    "purchase_credits_with_hbar": OperationSpec("POST", "/credits/purchase"),
    "get_x402_minimums": OperationSpec("GET", "/credits/purchase/x402/minimums"),
    "purchase_credits_with_x402": OperationSpec("POST", "/credits/purchase/x402"),
    "adapters": OperationSpec("GET", "/adapters"),
    "adapters_detailed": OperationSpec("GET", "/adapters/details"),
    "adapter_registry_categories": OperationSpec("GET", "/adapters/registry/categories"),
    "adapter_registry_adapters": OperationSpec("GET", "/adapters/registry/adapters"),
    "create_adapter_registry_category": OperationSpec("POST", "/adapters/registry/categories"),
    "submit_adapter_registry_adapter": OperationSpec("POST", "/adapters/registry/adapters"),
    "adapter_registry_submission_status": OperationSpec(
        "GET",
        "/adapters/registry/submissions/{submission_id}",
    ),
    "skills_config": OperationSpec("GET", "/skills/config"),
    "list_skills": OperationSpec("GET", "/skills"),
    "get_skill_security_breakdown": OperationSpec(
        "GET",
        "/skills/{job_id}/security-breakdown",
    ),
    "get_skills_catalog": OperationSpec("GET", "/skills/catalog"),
    "list_skill_versions": OperationSpec("GET", "/skills/versions"),
    "list_my_skills": OperationSpec("GET", "/skills/mine"),
    "get_my_skills_list": OperationSpec("GET", "/skills/my-list"),
    "quote_skill_publish": OperationSpec("POST", "/skills/quote"),
    "publish_skill": OperationSpec("POST", "/skills/publish"),
    "get_skill_publish_job": OperationSpec("GET", "/skills/jobs/{job_id}"),
    "get_skill_ownership": OperationSpec("GET", "/skills/ownership"),
    "get_recommended_skill_version": OperationSpec("GET", "/skills/recommended"),
    "set_recommended_skill_version": OperationSpec("POST", "/skills/recommended"),
    "get_skill_deprecations": OperationSpec("GET", "/skills/deprecations"),
    "set_skill_deprecation": OperationSpec("POST", "/skills/deprecate"),
    "get_skill_badge": OperationSpec("GET", "/skills/badge"),
    "get_skill_status": OperationSpec("GET", "/skills/status"),
    "get_skill_status_by_repo": OperationSpec("GET", "/skills/status/by-repo"),
    "upload_skill_preview_from_github_oidc": OperationSpec("POST", "/skills/preview/github-oidc"),
    "get_skill_preview": OperationSpec("GET", "/skills/preview"),
    "get_skill_preview_by_repo": OperationSpec("GET", "/skills/preview/by-repo"),
    "get_skill_preview_by_id": OperationSpec("GET", "/skills/preview/{preview_id}"),
    "get_skill_install": OperationSpec("GET", "/skills/{skill_ref}/install"),
    "record_skill_install_copy": OperationSpec(
        "POST",
        "/skills/{skill_ref}/telemetry/install-copy",
    ),
    "list_skill_tags": OperationSpec("GET", "/skills/tags"),
    "list_skill_categories": OperationSpec("GET", "/skills/categories"),
    "resolve_skill_markdown": OperationSpec(
        "GET",
        "/skills/{skill_ref}/SKILL.md",
        text_response=True,
    ),
    "resolve_skill_manifest": OperationSpec("GET", "/skills/{skill_ref}/manifest"),
    "get_skill_vote_status": OperationSpec("GET", "/skills/vote"),
    "set_skill_vote": OperationSpec("POST", "/skills/vote"),
    "request_skill_verification": OperationSpec("POST", "/skills/verification/request"),
    "get_skill_verification_status": OperationSpec("GET", "/skills/verification/status"),
    "create_skill_domain_proof_challenge": OperationSpec(
        "POST",
        "/skills/verification/domain/challenge",
    ),
    "verify_skill_domain_proof": OperationSpec("POST", "/skills/verification/domain/verify"),
}


def operation_names() -> list[str]:
    """Return sorted operation names for manifest generation and validation."""
    return sorted(REGISTRY_BROKER_OPERATIONS.keys())
