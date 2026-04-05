import httpx
import pytest

from standards_sdk_py.registry_broker import AsyncRegistryBrokerClient
from standards_sdk_py.shared.http import AsyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/search":
        return httpx.Response(200, json={"hits": [], "total": 1, "page": 1, "limit": 20})
    if request.url.path == "/chat/session":
        return httpx.Response(200, json={"sessionId": "s-2", "encryption": None})
    if request.url.path == "/skills/publish":
        return httpx.Response(200, json={"jobId": "job-2", "accepted": True})
    if request.url.path == "/skills/status":
        return httpx.Response(
            200,
            json={
                "name": "registry-broker",
                "version": "1.2.3",
                "published": True,
                "verifiedDomain": True,
                "trustTier": "verified",
                "badgeMetric": "tier",
                "checks": {
                    "repoCommitIntegrity": True,
                    "manifestIntegrity": True,
                    "domainProof": True,
                },
                "nextSteps": [],
                "verificationSignals": {
                    "publisherBound": True,
                    "domainProof": True,
                    "verifiedDomain": True,
                    "previewValidated": True,
                },
                "provenanceSignals": {
                    "repoCommitIntegrity": True,
                    "manifestIntegrity": True,
                    "canonicalRelease": True,
                    "previewAvailable": True,
                    "previewAuthoritative": False,
                },
                "publisher": None,
                "preview": None,
                "statusUrl": "https://hol.org/registry/skills/registry-broker?version=1.2.3",
            },
        )
    if request.url.path == "/skills/status/by-repo":
        return httpx.Response(
            200,
            json={
                "name": "registry-broker",
                "version": "1.2.3",
                "published": False,
                "verifiedDomain": False,
                "trustTier": "validated",
                "badgeMetric": "tier",
                "checks": {
                    "repoCommitIntegrity": True,
                    "manifestIntegrity": True,
                    "domainProof": False,
                },
                "nextSteps": [],
                "verificationSignals": {
                    "publisherBound": False,
                    "domainProof": False,
                    "verifiedDomain": False,
                    "previewValidated": True,
                },
                "provenanceSignals": {
                    "repoCommitIntegrity": True,
                    "manifestIntegrity": True,
                    "canonicalRelease": False,
                    "previewAvailable": True,
                    "previewAuthoritative": False,
                },
                "publisher": None,
                "preview": None,
                "statusUrl": "https://hol.org/registry/skills/preview/preview-1",
            },
        )
    if request.url.path == "/skills/quote-preview":
        return httpx.Response(
            200,
            json={
                "estimatedCredits": {"min": 589, "max": 678},
                "estimatedHbar": {"min": 4.11, "max": 4.73},
                "pricingVersion": "2026-04-05",
                "assumptions": ["2 files", "3 KB total"],
                "purchaseUrl": "https://hol.org/registry/skills/publish",
                "publishUrl": "https://hol.org/registry/skills/submit",
                "verificationUrl": "https://hol.org/registry/skills/registry-broker?tab=verification",
            },
        )
    if request.url.path == "/skills/conversion-signals/by-repo":
        return httpx.Response(
            200,
            json={
                "repoUrl": "https://github.com/hashgraph-online/registry-broker-skill",
                "skillDir": ".",
                "trustTier": "validated",
                "actionInstalled": True,
                "previewUploaded": True,
                "previewId": "preview-1",
                "lastValidateSuccessAt": "2026-04-05T12:00:00.000Z",
                "stalePreviewAgeDays": 0,
                "published": False,
                "verified": False,
                "publishReady": True,
                "publishBlockedByMissingAuth": False,
                "statusUrl": "https://hol.org/registry/skills/preview/preview-1",
                "purchaseUrl": "https://hol.org/registry/skills/publish",
                "publishUrl": "https://hol.org/registry/skills/submit",
                "verificationUrl": "https://hol.org/registry/skills/registry-broker?tab=verification",
                "nextSteps": [],
            },
        )
    if request.url.path == "/skills/preview":
        return httpx.Response(
            200,
            json={
                "found": True,
                "authoritative": False,
                "preview": {
                    "id": "record-1",
                    "previewId": "preview-1",
                    "source": "github-oidc",
                    "report": {
                        "schema_version": "skill-preview.v1",
                        "tool_version": "1.0.0",
                        "preview_id": "preview-1",
                        "repo_url": "https://github.com/hashgraph-online/registry-broker-skill",
                        "repo_owner": "hashgraph-online",
                        "repo_name": "registry-broker-skill",
                        "default_branch": "main",
                        "commit_sha": "abc123",
                        "ref": "refs/pull/5/head",
                        "event_name": "pull_request",
                        "workflow_run_url": "https://github.com/hashgraph-online/registry-broker-skill/actions/runs/1",
                        "skill_dir": ".",
                        "name": "registry-broker",
                        "version": "1.2.3",
                        "validation_status": "passed",
                        "findings": [],
                        "package_summary": {"files": 2},
                        "suggested_next_steps": [],
                        "generated_at": "2026-04-04T10:00:00.000Z",
                    },
                    "generatedAt": "2026-04-04T10:00:00.000Z",
                    "expiresAt": "2026-04-11T10:00:00.000Z",
                    "statusUrl": "https://hol.org/registry/skills/preview/preview-1",
                    "authoritative": False,
                },
                "statusUrl": "https://hol.org/registry/skills/preview/preview-1",
                "expiresAt": "2026-04-11T10:00:00.000Z",
            },
        )
    if request.url.path == "/skills/preview/by-repo":
        return httpx.Response(
            200,
            json={
                "found": False,
                "authoritative": False,
                "preview": None,
                "statusUrl": None,
                "expiresAt": None,
            },
        )
    if request.url.path == "/skills/preview/preview-1":
        return httpx.Response(
            200,
            json={
                "found": True,
                "authoritative": False,
                "preview": {
                    "id": "record-1",
                    "previewId": "preview-1",
                    "source": "github-oidc",
                    "report": {
                        "schema_version": "skill-preview.v1",
                        "tool_version": "1.0.0",
                        "preview_id": "preview-1",
                        "repo_url": "https://github.com/hashgraph-online/registry-broker-skill",
                        "repo_owner": "hashgraph-online",
                        "repo_name": "registry-broker-skill",
                        "default_branch": "main",
                        "commit_sha": "abc123",
                        "ref": "refs/pull/5/head",
                        "event_name": "pull_request",
                        "workflow_run_url": "https://github.com/hashgraph-online/registry-broker-skill/actions/runs/1",
                        "skill_dir": ".",
                        "name": "registry-broker",
                        "version": "1.2.3",
                        "validation_status": "passed",
                        "findings": [],
                        "package_summary": {"files": 2},
                        "suggested_next_steps": [],
                        "generated_at": "2026-04-04T10:00:00.000Z",
                    },
                    "generatedAt": "2026-04-04T10:00:00.000Z",
                    "expiresAt": "2026-04-11T10:00:00.000Z",
                    "statusUrl": "https://hol.org/registry/skills/preview/preview-1",
                    "authoritative": False,
                },
                "statusUrl": "https://hol.org/registry/skills/preview/preview-1",
                "expiresAt": "2026-04-11T10:00:00.000Z",
            },
        )
    if request.url.path == "/skills/preview/github-oidc":
        assert request.headers["authorization"] == "Bearer github-token"
        return httpx.Response(
            200,
            json={
                "id": "record-1",
                "previewId": "preview-1",
                "source": "github-oidc",
                "report": {
                    "schema_version": "skill-preview.v1",
                    "tool_version": "1.0.0",
                    "preview_id": "preview-1",
                    "repo_url": "https://github.com/hashgraph-online/registry-broker-skill",
                    "repo_owner": "hashgraph-online",
                    "repo_name": "registry-broker-skill",
                    "default_branch": "main",
                    "commit_sha": "abc123",
                    "ref": "refs/pull/5/head",
                    "event_name": "pull_request",
                    "workflow_run_url": "https://github.com/hashgraph-online/registry-broker-skill/actions/runs/1",
                    "skill_dir": ".",
                    "name": "registry-broker",
                    "version": "1.2.3",
                    "validation_status": "passed",
                    "findings": [],
                    "package_summary": {"files": 2},
                    "suggested_next_steps": [],
                    "generated_at": "2026-04-04T10:00:00.000Z",
                },
                "generatedAt": "2026-04-04T10:00:00.000Z",
                "expiresAt": "2026-04-11T10:00:00.000Z",
                "statusUrl": "https://hol.org/registry/skills/preview/preview-1",
                "authoritative": False,
            },
        )
    if request.url.path == "/skills/registry-broker@1.2.3/install":
        return httpx.Response(
            200,
            json={
                "name": "registry-broker",
                "version": "1.2.3",
                "skillRef": "registry-broker@1.2.3",
            },
        )
    if request.url.path == "/skills/registry-broker@1.2.3/telemetry/install-copy":
        return httpx.Response(200, json={"accepted": True})
    return httpx.Response(200, json={"ok": True})


@pytest.mark.asyncio
async def test_registry_broker_core_flows_async() -> None:
    transport = AsyncHttpTransport(
        "https://example.test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(_handler)),
    )
    client = AsyncRegistryBrokerClient(transport=transport)

    search = await client.search(query="hcs")
    assert search.total == 1

    session = await client.create_session({"uaid": "test-uaid"})
    assert session.session_id == "s-2"

    publish = await client.publish_skill({"name": "skill-b", "version": "1.0.0"})
    assert publish.job_id == "job-2"

    status = await client.get_skill_status(name="registry-broker", version="1.2.3")
    assert status.trust_tier == "verified"

    repo_status = await client.get_skill_status_by_repo(
        repo="https://github.com/hashgraph-online/registry-broker-skill",
        skill_dir=".",
    )
    assert repo_status.trust_tier == "validated"

    quote = await client.quote_skill_publish_preview(
        file_count=2,
        total_bytes=3072,
        name="registry-broker",
        version="1.2.3",
        repo_url="https://github.com/hashgraph-online/registry-broker-skill",
        skill_dir=".",
    )
    assert quote.estimated_credits.min == 589

    signals = await client.get_skill_conversion_signals_by_repo(
        repo="https://github.com/hashgraph-online/registry-broker-skill",
        skill_dir=".",
        ref="refs/heads/main",
    )
    assert signals.publish_ready is True

    preview = await client.get_skill_preview(name="registry-broker", version="1.2.3")
    assert preview.preview is not None
    assert preview.preview.preview_id == "preview-1"

    preview_by_repo = await client.get_skill_preview_by_repo(
        repo="https://github.com/hashgraph-online/registry-broker-skill",
        skill_dir=".",
    )
    assert preview_by_repo.found is False

    preview_by_id = await client.get_skill_preview_by_id("preview-1")
    assert preview_by_id.preview is not None

    uploaded_preview = await client.upload_skill_preview_from_github_oidc(
        token="github-token",
        report={
            "schema_version": "skill-preview.v1",
            "tool_version": "1.0.0",
            "preview_id": "preview-1",
            "repo_url": "https://github.com/hashgraph-online/registry-broker-skill",
            "repo_owner": "hashgraph-online",
            "repo_name": "registry-broker-skill",
            "default_branch": "main",
            "commit_sha": "abc123",
            "ref": "refs/pull/5/head",
            "event_name": "pull_request",
            "workflow_run_url": "https://github.com/hashgraph-online/registry-broker-skill/actions/runs/1",
            "skill_dir": ".",
            "name": "registry-broker",
            "version": "1.2.3",
            "validation_status": "passed",
            "findings": [],
            "package_summary": {"files": 2},
            "suggested_next_steps": [],
            "generated_at": "2026-04-04T10:00:00.000Z",
        },
    )
    assert uploaded_preview.id == "record-1"

    install = await client.get_skill_install("registry-broker@1.2.3")
    assert install.skill_ref == "registry-broker@1.2.3"

    install_copy = await client.record_skill_install_copy(
        "registry-broker@1.2.3",
        {"source": "detail_install_card", "installType": "cli"},
    )
    assert install_copy.accepted is True

    dynamic = await client.adapter_registry_categories()
    assert isinstance(dynamic, dict)

    await client.close()
