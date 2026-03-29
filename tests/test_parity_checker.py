import json
from pathlib import Path

from standards_sdk_py.parity.checker import check_manifest


def test_parity_manifest_resolves_done_symbols() -> None:
    manifest = Path("src/standards_sdk_py/parity/parity-manifest.json")
    total, errors = check_manifest(manifest)
    assert total > 0
    assert errors == []


def test_parity_manifest_tracks_delegate_entry() -> None:
    manifest = Path("src/standards_sdk_py/parity/parity-manifest.json")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    entries = payload["entries"]
    delegate_entry = next(entry for entry in entries if entry["id"] == "ts-registry-delegate")
    assert delegate_entry["source_symbol"] == "RegistryBrokerClient.delegate"
    assert delegate_entry["python_symbol"] == (
        "standards_sdk_py.registry_broker.RegistryBrokerClient.delegate"
    )
