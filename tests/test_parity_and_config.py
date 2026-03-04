"""Tests for parity checker and inventory modules."""

import json
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from standards_sdk_py.parity.checker import _resolve_symbol, check_manifest
from standards_sdk_py.parity.checker import main as checker_main
from standards_sdk_py.parity.inventory import (
    _extract_method_names,
    generate_inventories,
    validate_manifest,
)
from standards_sdk_py.parity.inventory import (
    main as inventory_main,
)
from standards_sdk_py.parity.models import ParityEntry, ParityManifest, ParityStatus

# ── _resolve_symbol tests ────────────────────────────────────────────


def test_resolve_symbol_valid() -> None:
    result = _resolve_symbol("standards_sdk_py.exceptions.SdkError")
    from standards_sdk_py.exceptions import SdkError

    assert result is SdkError


def test_resolve_symbol_class_method() -> None:
    result = _resolve_symbol("standards_sdk_py.shared.config.SdkConfig.from_env")
    assert callable(result)


def test_resolve_symbol_too_short() -> None:
    with pytest.raises(ValueError, match="Invalid python symbol path"):
        _resolve_symbol("single")


def test_resolve_symbol_bad_module() -> None:
    with pytest.raises(ModuleNotFoundError, match="Unable to import"):
        _resolve_symbol("nonexistent_module_xyz.FakeClass")


def test_resolve_symbol_bad_attribute() -> None:
    with pytest.raises(AttributeError, match="Missing attribute"):
        _resolve_symbol("standards_sdk_py.exceptions.SdkError.nonexistent_attribute_xyz")


# ── check_manifest tests ─────────────────────────────────────────────


def test_check_manifest_valid() -> None:
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "entry-1",
                "source_sdk": "ts",
                "source_symbol": "SomeClass.method",
                "python_symbol": "standards_sdk_py.exceptions.SdkError",
                "status": "done",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(manifest_data, f)
        f.flush()
        total, errors = check_manifest(Path(f.name))
        assert total == 1
        assert errors == []
    Path(f.name).unlink(missing_ok=True)


def test_check_manifest_duplicate_ids() -> None:
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "dup-1",
                "source_sdk": "ts",
                "source_symbol": "A.b",
                "python_symbol": "standards_sdk_py.exceptions.SdkError",
                "status": "todo",
            },
            {
                "id": "dup-1",
                "source_sdk": "go",
                "source_symbol": "C.d",
                "python_symbol": "standards_sdk_py.exceptions.ApiError",
                "status": "todo",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(manifest_data, f)
        f.flush()
        total, errors = check_manifest(Path(f.name))
        assert total == 2
        assert any("Duplicate" in e for e in errors)
    Path(f.name).unlink(missing_ok=True)


def test_check_manifest_bad_symbol_for_done() -> None:
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "bad-sym",
                "source_sdk": "ts",
                "source_symbol": "A.b",
                "python_symbol": "standards_sdk_py.nonexistent_module.FakeClass",
                "status": "done",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(manifest_data, f)
        f.flush()
        total, errors = check_manifest(Path(f.name))
        assert total == 1
        assert len(errors) == 1
        assert "failed to resolve" in errors[0]
    Path(f.name).unlink(missing_ok=True)


def test_check_manifest_verified_status_resolves() -> None:
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "verified-1",
                "source_sdk": "ts",
                "source_symbol": "A.b",
                "python_symbol": "standards_sdk_py.exceptions.ApiError",
                "status": "verified",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(manifest_data, f)
        f.flush()
        total, errors = check_manifest(Path(f.name))
        assert total == 1
        assert errors == []
    Path(f.name).unlink(missing_ok=True)


def test_check_manifest_todo_skips_resolve() -> None:
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "todo-1",
                "source_sdk": "ts",
                "source_symbol": "A.b",
                "python_symbol": "completely.fake.symbol.that.does.not.exist",
                "status": "todo",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(manifest_data, f)
        f.flush()
        total, errors = check_manifest(Path(f.name))
        # Should not error because status is 'todo' (not done/verified)
        assert total == 1
        assert errors == []
    Path(f.name).unlink(missing_ok=True)


# ── checker main() tests ─────────────────────────────────────────────


def test_checker_main_success(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "e-1",
                "source_sdk": "ts",
                "source_symbol": "A.b",
                "python_symbol": "standards_sdk_py.exceptions.SdkError",
                "status": "done",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(manifest_data, f)
        f.flush()
        monkeypatch.setattr(sys, "argv", ["checker", "--manifest", f.name])
        checker_main()
    Path(f.name).unlink(missing_ok=True)


def test_checker_main_missing_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["checker", "--manifest", "/nonexistent/file.json"])
    with pytest.raises(SystemExit):
        checker_main()


def test_checker_main_with_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "bad-sym",
                "source_sdk": "ts",
                "source_symbol": "A.b",
                "python_symbol": "standards_sdk_py.nonexistent.Fake",
                "status": "done",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(manifest_data, f)
        f.flush()
        monkeypatch.setattr(sys, "argv", ["checker", "--manifest", f.name])
        with pytest.raises(SystemExit):
            checker_main()
    Path(f.name).unlink(missing_ok=True)


def test_checker_main_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover the `if __name__ == '__main__'` block in checker.py (line 82)."""
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "e-1",
                "source_sdk": "ts",
                "source_symbol": "A.b",
                "python_symbol": "standards_sdk_py.exceptions.SdkError",
                "status": "done",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(manifest_data, f)
        f.flush()
        monkeypatch.setattr(sys, "argv", ["checker", "--manifest", f.name])
        runpy.run_module(
            "standards_sdk_py.parity.checker",
            run_name="__main__",
            alter_sys=True,
        )
    Path(f.name).unlink(missing_ok=True)


# ── _extract_method_names tests ───────────────────────────────────────


def test_extract_method_names_basic() -> None:
    matches = [
        {"metaVariables": {"single": {"M": {"text": "doStuff"}}}},
        {"metaVariables": {"single": {"M": {"text": "doOther"}}}},
        {"metaVariables": {"single": {"M": {"text": "doStuff"}}}},  # duplicate
    ]
    names = _extract_method_names(matches)
    assert names == ["doOther", "doStuff"]


def test_extract_method_names_empty() -> None:
    assert _extract_method_names([]) == []


def test_extract_method_names_missing_fields() -> None:
    matches = [
        {"metaVariables": {}},
        {"metaVariables": {"single": {}}},
        {"metaVariables": {"single": {"M": {}}}},
        {"metaVariables": {"single": {"M": {"text": ""}}}},
        {"metaVariables": {"single": {"M": {"text": None}}}},
        {},
    ]
    assert _extract_method_names(matches) == []


# ── validate_manifest tests ──────────────────────────────────────────


def test_validate_manifest() -> None:
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "e-1",
                "source_sdk": "ts",
                "source_symbol": "A.b",
                "python_symbol": "x.y",
                "status": "todo",
            },
            {
                "id": "e-2",
                "source_sdk": "go",
                "source_symbol": "C.d",
                "python_symbol": "x.z",
                "status": "in_progress",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(manifest_data, f)
        f.flush()
        count = validate_manifest(Path(f.name))
        assert count == 2
    Path(f.name).unlink(missing_ok=True)


# ── generate_inventories tests ───────────────────────────────────────


def test_generate_inventories(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test generate_inventories with mocked subprocess."""
    ts_class_data = json.dumps({"RegistryBrokerClient": ["fetchData"]})
    ts_registry_data = json.dumps(["fetchData"])
    ts_inscriber_data = json.dumps(["generateQuote"])
    go_data = json.dumps({"metaVariables": {"single": {"M": {"text": "GetData"}}}})
    outputs = [ts_class_data, ts_registry_data, ts_inscriber_data, go_data]

    class _FakeResult:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    def _fake_run(command: list[str], **kwargs: object) -> _FakeResult:
        del command, kwargs
        if outputs:
            return _FakeResult(outputs.pop(0))
        return _FakeResult(go_data)

    monkeypatch.setattr("standards_sdk_py.parity.inventory.subprocess.run", _fake_run)

    # Create the expected directory structure
    repo_root = tmp_path / "repo"
    ts_dir = repo_root / "standards-sdk" / "src" / "services" / "registry-broker" / "client"
    ts_dir.mkdir(parents=True)
    (ts_dir / "base-client.ts").write_text("// TS")
    go_dir = repo_root / "standards-sdk-go" / "pkg" / "registrybroker"
    go_dir.mkdir(parents=True)
    (go_dir / "client.go").write_text("// Go")

    output_dir = tmp_path / "output"
    ts_count, go_count = generate_inventories(repo_root, output_dir)
    assert ts_count == 2
    assert go_count == 1
    assert (output_dir / "ts-registry-broker-methods.json").exists()
    assert (output_dir / "ts-core-client-methods.json").exists()
    assert (output_dir / "go-registry-broker-methods.json").exists()


# ── inventory main() tests ───────────────────────────────────────────


def test_inventory_main(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test inventory main with mocked functions."""
    monkeypatch.setattr(
        "standards_sdk_py.parity.inventory.generate_inventories",
        lambda repo_root, output_dir: (5, 3),
    )
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "e-1",
                "source_sdk": "ts",
                "source_symbol": "A.b",
                "python_symbol": "x.y",
                "status": "todo",
            },
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "inventory",
            "--repo-root",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "out"),
            "--manifest",
            str(manifest_path),
        ],
    )
    inventory_main()


def test_inventory_main_guard(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Cover the `if __name__ == '__main__'` block in inventory.py (line 129).

    runpy.run_module re-executes the module from disk, so we need to mock
    everything at the module level that the fresh execution will call.
    We do this by patching subprocess.run (which generate_inventories calls)
    so that it returns valid JSON output.
    """
    ts_class_data = json.dumps({"RegistryBrokerClient": ["fetchData"]})
    ts_registry_data = json.dumps(["fetchData"])
    ts_inscriber_data = json.dumps(["generateQuote"])
    go_data = json.dumps({"metaVariables": {"single": {"M": {"text": "GetData"}}}})
    outputs = [ts_class_data, ts_registry_data, ts_inscriber_data, go_data]

    class _FakeResult:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    def _fake_run(command: list[str], **kwargs: object) -> _FakeResult:
        del command, kwargs
        if outputs:
            return _FakeResult(outputs.pop(0))
        return _FakeResult(go_data)

    # Create required directory structure for generate_inventories
    repo_root = tmp_path / "repo"
    ts_dir = repo_root / "standards-sdk" / "src" / "services" / "registry-broker" / "client"
    ts_dir.mkdir(parents=True)
    (ts_dir / "base-client.ts").write_text("// TS")
    go_dir = repo_root / "standards-sdk-go" / "pkg" / "registrybroker"
    go_dir.mkdir(parents=True)
    (go_dir / "client.go").write_text("// Go")

    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "e-1",
                "source_sdk": "ts",
                "source_symbol": "A.b",
                "python_symbol": "x.y",
                "status": "todo",
            },
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data))
    monkeypatch.setattr(subprocess, "run", _fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "inventory",
            "--repo-root",
            str(repo_root),
            "--output-dir",
            str(tmp_path / "out"),
            "--manifest",
            str(manifest_path),
        ],
    )
    runpy.run_module(
        "standards_sdk_py.parity.inventory",
        run_name="__main__",
        alter_sys=True,
    )


# ── Parity models tests ──────────────────────────────────────────────


def test_parity_status_enum() -> None:
    assert ParityStatus.todo.value == "todo"
    assert ParityStatus.in_progress.value == "in_progress"
    assert ParityStatus.done.value == "done"
    assert ParityStatus.verified.value == "verified"


def test_parity_entry_model() -> None:
    entry = ParityEntry(
        id="test",
        source_sdk="ts",
        source_symbol="A.b",
        python_symbol="x.y",
        status="todo",
        notes="test note",
    )
    assert entry.id == "test"
    assert entry.notes == "test note"


def test_parity_manifest_model() -> None:
    manifest = ParityManifest(
        version="1.0",
        metadata={"sdk": "py"},
        entries=[],
    )
    assert manifest.version == "1.0"
    assert manifest.entries == []


# ── Config edge cases ────────────────────────────────────────────────


def test_config_clean_whitespace() -> None:
    from standards_sdk_py.shared.config import _clean

    assert _clean(None) is None
    assert _clean("") is None
    assert _clean("   ") is None
    assert _clean("  hello  ") == "hello"


def test_config_from_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    from standards_sdk_py.shared.config import (
        DEFAULT_MIRROR_NODE_BASE_URL,
        DEFAULT_REGISTRY_BROKER_BASE_URL,
        SdkConfig,
    )

    # Clear all relevant env vars
    for key in [
        "STANDARDS_SDK_PY_REGISTRY_BROKER_BASE_URL",
        "STANDARDS_SDK_PY_MIRROR_NODE_BASE_URL",
        "STANDARDS_SDK_PY_API_KEY",
        "STANDARDS_SDK_PY_ACCOUNT_ID",
        "STANDARDS_SDK_PY_LEDGER_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)
    config = SdkConfig.from_env()
    assert config.network.registry_broker_base_url == DEFAULT_REGISTRY_BROKER_BASE_URL
    assert config.network.mirror_node_base_url == DEFAULT_MIRROR_NODE_BASE_URL
    assert config.registry_auth.api_key is None


def test_config_from_mapping_empty() -> None:
    from standards_sdk_py.shared.config import (
        DEFAULT_MIRROR_NODE_BASE_URL,
        DEFAULT_REGISTRY_BROKER_BASE_URL,
        SdkConfig,
    )

    config = SdkConfig.from_mapping({})
    assert config.network.registry_broker_base_url == DEFAULT_REGISTRY_BROKER_BASE_URL
    assert config.network.mirror_node_base_url == DEFAULT_MIRROR_NODE_BASE_URL


def test_registry_auth_headers_no_keys() -> None:
    from standards_sdk_py.shared.config import RegistryBrokerAuthConfig

    headers = RegistryBrokerAuthConfig().headers()
    assert headers == {}


def test_registry_auth_headers_ledger_sets_api_key() -> None:
    from standards_sdk_py.shared.config import RegistryBrokerAuthConfig

    headers = RegistryBrokerAuthConfig(ledger_api_key="ledger-k").headers()
    assert headers["x-ledger-api-key"] == "ledger-k"
    assert headers["x-api-key"] == "ledger-k"  # setdefault from ledger


def test_registry_auth_headers_api_key_precedence() -> None:
    from standards_sdk_py.shared.config import RegistryBrokerAuthConfig

    headers = RegistryBrokerAuthConfig(api_key="real-key", ledger_api_key="ledger-k").headers()
    assert headers["x-api-key"] == "real-key"  # api_key takes precedence (set first)
    assert headers["x-ledger-api-key"] == "ledger-k"


# ── _load_methods tests (checker.py lines 42-46) ────────────────────


def test_load_methods_valid() -> None:
    from standards_sdk_py.parity.checker import _load_methods

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"methods": ["method_a", "method_b"]}, f)
        f.flush()
        result = _load_methods(Path(f.name))
    assert result == ["method_a", "method_b"]
    Path(f.name).unlink(missing_ok=True)


def test_load_methods_invalid_format() -> None:
    from standards_sdk_py.parity.checker import _load_methods

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"methods": "not-a-list"}, f)
        f.flush()
        with pytest.raises(ValueError, match="Invalid method inventory format"):
            _load_methods(Path(f.name))
    Path(f.name).unlink(missing_ok=True)


def test_load_methods_filters_non_strings() -> None:
    from standards_sdk_py.parity.checker import _load_methods

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"methods": ["good", 123, None, "also_good"]}, f)
        f.flush()
        result = _load_methods(Path(f.name))
    assert result == ["good", "also_good"]
    Path(f.name).unlink(missing_ok=True)


def test_load_core_inventory_valid() -> None:
    from standards_sdk_py.parity.checker import _load_core_inventory

    payload = {
        "classes": {"HederaMirrorNode": ["getTopicMessages", 123]},
        "inscriber_functions": ["generateQuote", None],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        f.flush()
        classes, functions = _load_core_inventory(Path(f.name))
    assert classes == {"HederaMirrorNode": ["getTopicMessages"]}
    assert functions == ["generateQuote"]
    Path(f.name).unlink(missing_ok=True)


def test_load_core_inventory_invalid_format() -> None:
    from standards_sdk_py.parity.checker import _load_core_inventory

    payload = {"classes": [], "inscriber_functions": []}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        f.flush()
        with pytest.raises(ValueError, match="Invalid core inventory classes format"):
            _load_core_inventory(Path(f.name))
    Path(f.name).unlink(missing_ok=True)


# ── enforce_ts_inventory tests (checker.py lines 72-89) ──────────────


def test_check_manifest_enforce_ts_inventory_missing_entry() -> None:
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [],
    }
    ts_inventory = {"methods": ["someMethod"]}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as mf:
        json.dump(manifest_data, mf)
        mf.flush()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
            json.dump(ts_inventory, tf)
            tf.flush()
            total, errors = check_manifest(
                Path(mf.name),
                ts_inventory_path=Path(tf.name),
                enforce_ts_inventory=True,
            )
    assert any("Missing TS parity manifest entry" in e for e in errors)
    Path(mf.name).unlink(missing_ok=True)
    Path(tf.name).unlink(missing_ok=True)


def test_check_manifest_enforce_ts_inventory_not_completed() -> None:
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "e-1",
                "source_sdk": "ts",
                "source_symbol": "RegistryBrokerClient.someMethod",
                "python_symbol": "standards_sdk_py.exceptions.SdkError",
                "status": "todo",
            },
        ],
    }
    ts_inventory = {"methods": ["someMethod"]}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as mf:
        json.dump(manifest_data, mf)
        mf.flush()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
            json.dump(ts_inventory, tf)
            tf.flush()
            total, errors = check_manifest(
                Path(mf.name),
                ts_inventory_path=Path(tf.name),
                enforce_ts_inventory=True,
            )
    assert any("not completed" in e for e in errors)
    Path(mf.name).unlink(missing_ok=True)
    Path(tf.name).unlink(missing_ok=True)


def test_check_manifest_enforce_ts_inventory_done_but_missing_python() -> None:
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "e-1",
                "source_sdk": "ts",
                "source_symbol": "RegistryBrokerClient.nonExistentMethod",
                "python_symbol": "standards_sdk_py.exceptions.SdkError",
                "status": "done",
            },
        ],
    }
    ts_inventory = {"methods": ["nonExistentMethod"]}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as mf:
        json.dump(manifest_data, mf)
        mf.flush()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
            json.dump(ts_inventory, tf)
            tf.flush()
            total, errors = check_manifest(
                Path(mf.name),
                ts_inventory_path=Path(tf.name),
                enforce_ts_inventory=True,
            )
    assert any("Missing Python method" in e for e in errors)
    Path(mf.name).unlink(missing_ok=True)
    Path(tf.name).unlink(missing_ok=True)
