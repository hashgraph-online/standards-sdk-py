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

    status = client.get_skill_status(name="registry-broker", version="1.2.3")
    assert status.trust_tier == "verified"

    repo_status = client.get_skill_status_by_repo(
        repo="https://github.com/hashgraph-online/registry-broker-skill",
        skill_dir=".",
    )
    assert repo_status.trust_tier == "validated"

    quote = client.quote_skill_publish_preview(
        file_count=2,
        total_bytes=3072,
        name="registry-broker",
        version="1.2.3",
        repo_url="https://github.com/hashgraph-online/registry-broker-skill",
        skill_dir=".",
    )
    assert quote.estimated_credits.min == 589

    signals = client.get_skill_conversion_signals_by_repo(
        repo="https://github.com/hashgraph-online/registry-broker-skill",
        skill_dir=".",
        ref="refs/heads/main",
    )
    assert signals.publish_ready is True

    preview = client.get_skill_preview(name="registry-broker", version="1.2.3")
    assert preview.preview is not None
    assert preview.preview.preview_id == "preview-1"

    preview_by_repo = client.get_skill_preview_by_repo(
        repo="https://github.com/hashgraph-online/registry-broker-skill",
        skill_dir=".",
    )
    assert preview_by_repo.found is False

    preview_by_id = client.get_skill_preview_by_id("preview-1")
    assert preview_by_id.preview is not None

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
    assert uploaded_preview.id == "record-1"

    install = client.get_skill_install("registry-broker@1.2.3")
    assert install.skill_ref == "registry-broker@1.2.3"

    install_copy = client.record_skill_install_copy(
        "registry-broker@1.2.3",
        {"source": "detail_install_card", "installType": "cli"},
    )
    assert install_copy.accepted is True

    verification = client.get_verification_status("test-uaid")
    assert verification.verified is True

    dynamic = client.adapter_registry_categories()
    assert isinstance(dynamic, dict)


def test_registry_broker_sync_url_encodes_scoped_skill_refs() -> None:
    raw_paths: list[bytes] = []

    def scoped_handler(request: httpx.Request) -> httpx.Response:
        raw_paths.append(request.url.raw_path)
        if request.url.raw_path == b"/skills/%40hashgraph-online%2Fdemo-summarizer%401.0.0/install":
            return httpx.Response(
                200,
                json={
                    "name": "demo-summarizer",
                    "version": "1.0.0",
                    "skillRef": "@hashgraph-online/demo-summarizer@1.0.0",
                },
            )
        if request.url.raw_path == b"/skills/%40hashgraph-online%2Fdemo-summarizer%401.0.0/telemetry/install-copy":
            return httpx.Response(200, json={"accepted": True})
        return httpx.Response(404, json={"error": "unexpected path"})

    transport = SyncHttpTransport(
        "https://example.test",
        client=httpx.Client(transport=httpx.MockTransport(scoped_handler)),
    )
    client = RegistryBrokerClient(transport=transport)

    install = client.get_skill_install("@hashgraph-online/demo-summarizer@1.0.0")
    install_copy = client.record_skill_install_copy(
        "@hashgraph-online/demo-summarizer@1.0.0",
        {"source": "detail_install_card", "installType": "cli"},
    )

    assert install.skill_ref == "@hashgraph-online/demo-summarizer@1.0.0"
    assert install_copy.accepted is True
    assert raw_paths == [
        b"/skills/%40hashgraph-online%2Fdemo-summarizer%401.0.0/install",
        b"/skills/%40hashgraph-online%2Fdemo-summarizer%401.0.0/telemetry/install-copy",
    ]
