import httpx

from standards_sdk_py.registry_broker import RegistryBrokerClient
from standards_sdk_py.shared.http import SyncHttpTransport


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/search":
        return httpx.Response(200, json={"hits": [], "total": 0, "page": 1, "limit": 20})
    if request.url.path == "/protocols":
        return httpx.Response(200, json={"protocols": [{"name": "hcs10"}]})
    if request.url.path == "/chat/session":
        return httpx.Response(200, json={"sessionId": "s-1", "encryption": None})
    if request.url.path == "/skills/publish":
        return httpx.Response(200, json={"jobId": "job-1", "accepted": True})
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
                "nextSteps": [
                    {
                        "kind": "share_status",
                        "priority": 1,
                        "id": "share-skill",
                        "label": "Share status",
                        "description": "Share the canonical page",
                    }
                ],
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
                "publisher": {
                    "cliPackageUrl": "https://www.npmjs.com/package/skill-publish",
                    "cliCommand": "npx skill-publish",
                    "actionMarketplaceUrl": "https://github.com/marketplace/actions/skill-publish",
                    "repositoryUrl": "https://github.com/hashgraph-online/skill-publish",
                    "quickstartCommands": [],
                    "templatePresets": [],
                },
                "preview": {
                    "previewId": "preview-1",
                    "repoUrl": "https://github.com/hashgraph-online/registry-broker-skill",
                    "repoOwner": "hashgraph-online",
                    "repoName": "registry-broker-skill",
                    "commitSha": "abc123",
                    "ref": "refs/pull/5/head",
                    "eventName": "pull_request",
                    "skillDir": ".",
                    "generatedAt": "2026-04-04T10:00:00.000Z",
                    "expiresAt": "2026-04-11T10:00:00.000Z",
                    "statusUrl": "https://hol.org/registry/skills/preview/preview-1",
                },
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
    if request.url.path == "/verification/status/test-uaid":
        return httpx.Response(200, json={"verified": True, "method": "dns"})
    return httpx.Response(200, json={"ok": True})


def test_registry_broker_core_flows_sync() -> None:
    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(_handler)),
    )
    client = RegistryBrokerClient(transport=transport)

    search = client.search(query="hcs")
    assert search.total == 0

    protocols = client.list_protocols()
    assert protocols.protocols[0]["name"] == "hcs10"

    session = client.create_session({"uaid": "test-uaid"})
    assert session.session_id == "s-1"

    publish = client.publish_skill({"name": "skill-a", "version": "1.0.0"})
    assert publish.job_id == "job-1"

    verification = client.get_verification_status("test-uaid")
    assert verification.verified is True

    status = client.get_skill_status(name="registry-broker", version="1.2.3")
    assert status.trust_tier == "verified"
    assert status.preview is not None
    assert status.preview.preview_id == "preview-1"

    status_by_repo = client.get_skill_status_by_repo(
        repo="hashgraph-online/registry-broker-skill",
        skill_dir=".",
        ref="refs/pull/5/head",
    )
    assert status_by_repo.published is False

    preview = client.get_skill_preview(name="registry-broker", version="1.2.3")
    assert preview.found is True
    assert preview.preview is not None
    assert preview.preview.preview_id == "preview-1"

    preview_by_repo = client.get_skill_preview_by_repo(
        repo="hashgraph-online/registry-broker-skill",
        skill_dir=".",
        ref="refs/pull/5/head",
    )
    assert preview_by_repo.found is False

    preview_by_id = client.get_skill_preview_by_id("preview-1")
    assert preview_by_id.preview is not None
    assert preview_by_id.preview.id == "record-1"

    uploaded_preview = client.upload_skill_preview_from_github_oidc(
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
    assert uploaded_preview.source == "github-oidc"

    install = client.get_skill_install("registry-broker@1.2.3")
    assert install.skillRef == "registry-broker@1.2.3"

    install_copy = client.record_skill_install_copy(
        "registry-broker@1.2.3",
        {"source": "detail_install_card", "installType": "cli"},
    )
    assert install_copy.accepted is True

    dynamic = client.adapter_registry_categories()
    assert isinstance(dynamic, dict)
