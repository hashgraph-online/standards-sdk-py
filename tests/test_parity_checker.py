from pathlib import Path

from standards_sdk_py.parity.checker import check_manifest


def test_parity_manifest_resolves_done_symbols() -> None:
    manifest = Path("src/standards_sdk_py/parity/parity-manifest.json")
    total, errors = check_manifest(manifest)
    assert total > 0
    assert errors == []
