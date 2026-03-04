"""Tests for checker module's new _load_core_inventory and core inventory enforcement."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from standards_sdk_py.parity.checker import (
    TS_CLASS_TO_PYTHON_CLASS,
    TS_INSCRIBER_FUNCTION_TO_PYTHON,
    _camel_to_snake,
    _load_core_inventory,
    _resolve_symbol,
    check_manifest,
)

# ── _camel_to_snake ──────────────────────────────────────────────────


def test_checker_camel_to_snake() -> None:
    assert _camel_to_snake("getAccountBalance") == "get_account_balance"
    assert _camel_to_snake("simple") == "simple"


# ── _resolve_symbol ──────────────────────────────────────────────────


def test_resolve_symbol_valid() -> None:
    result = _resolve_symbol("standards_sdk_py.exceptions.SdkError")
    assert result is not None


def test_resolve_symbol_invalid_short() -> None:
    with pytest.raises(ValueError, match="Invalid python symbol path"):
        _resolve_symbol("onlyone")


def test_resolve_symbol_module_not_found() -> None:
    with pytest.raises(ModuleNotFoundError, match="Unable to import"):
        _resolve_symbol("nonexistent.module.Symbol")


def test_resolve_symbol_missing_attr() -> None:
    with pytest.raises(AttributeError, match="Missing attribute"):
        _resolve_symbol("standards_sdk_py.exceptions.NonExistentThing")


# ── _load_core_inventory ────────────────────────────────────────────


def test_load_core_inventory_valid() -> None:
    data = {
        "classes": {"RegistryBrokerClient": ["search", "stats"]},
        "inscriber_functions": ["inscribe", "generateQuote"],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        classes, funcs = _load_core_inventory(Path(f.name))
    assert classes == {"RegistryBrokerClient": ["search", "stats"]}
    assert funcs == ["inscribe", "generateQuote"]
    Path(f.name).unlink(missing_ok=True)


def test_load_core_inventory_invalid_classes() -> None:
    data = {"classes": "not-a-dict", "inscriber_functions": []}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        with pytest.raises(ValueError, match="Invalid core inventory classes format"):
            _load_core_inventory(Path(f.name))
    Path(f.name).unlink(missing_ok=True)


def test_load_core_inventory_invalid_functions() -> None:
    data = {"classes": {}, "inscriber_functions": "not-a-list"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        with pytest.raises(ValueError, match="Invalid core inventory inscriber_functions format"):
            _load_core_inventory(Path(f.name))
    Path(f.name).unlink(missing_ok=True)


# ── check_manifest with ts_core_inventory ────────────────────────────


def test_check_manifest_core_inventory_missing_entry() -> None:
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [],
    }
    core_inventory = {
        "classes": {"RegistryBrokerClient": ["search"]},
        "inscriber_functions": ["inscribe"],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as mf:
        json.dump(manifest_data, mf)
        mf.flush()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as cf:
            json.dump(core_inventory, cf)
            cf.flush()
            total, errors = check_manifest(
                Path(mf.name),
                ts_core_inventory_path=Path(cf.name),
                enforce_ts_inventory=True,
            )
    assert any("Missing TS parity manifest entry" in e for e in errors)
    Path(mf.name).unlink(missing_ok=True)
    Path(cf.name).unlink(missing_ok=True)


def test_check_manifest_core_inventory_not_completed() -> None:
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "e-1",
                "source_sdk": "ts",
                "source_symbol": "RegistryBrokerClient.search",
                "python_symbol": "standards_sdk_py.registry_broker.RegistryBrokerClient.search",
                "status": "todo",
            },
        ],
    }
    core_inventory = {
        "classes": {"RegistryBrokerClient": ["search"]},
        "inscriber_functions": [],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as mf:
        json.dump(manifest_data, mf)
        mf.flush()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as cf:
            json.dump(core_inventory, cf)
            cf.flush()
            total, errors = check_manifest(
                Path(mf.name),
                ts_core_inventory_path=Path(cf.name),
                enforce_ts_inventory=True,
            )
    assert any("not completed" in e for e in errors)
    Path(mf.name).unlink(missing_ok=True)
    Path(cf.name).unlink(missing_ok=True)


def test_check_manifest_core_inventory_done_resolves() -> None:
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "e-1",
                "source_sdk": "ts",
                "source_symbol": "RegistryBrokerClient.search",
                "python_symbol": "standards_sdk_py.registry_broker.RegistryBrokerClient.search",
                "status": "done",
            },
        ],
    }
    core_inventory = {
        "classes": {"RegistryBrokerClient": ["search"]},
        "inscriber_functions": [],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as mf:
        json.dump(manifest_data, mf)
        mf.flush()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as cf:
            json.dump(core_inventory, cf)
            cf.flush()
            total, errors = check_manifest(
                Path(mf.name),
                ts_core_inventory_path=Path(cf.name),
                enforce_ts_inventory=True,
            )
    # search exists on RegistryBrokerClient, so no errors for it
    assert not any("search" in e for e in errors)
    Path(mf.name).unlink(missing_ok=True)
    Path(cf.name).unlink(missing_ok=True)


def test_check_manifest_inscriber_function_missing_mapping() -> None:
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "e-1",
                "source_sdk": "ts",
                "source_symbol": "inscriber.unknownFunction",
                "python_symbol": "standards_sdk_py.inscriber.client.inscribe",
                "status": "done",
            },
        ],
    }
    core_inventory = {
        "classes": {},
        "inscriber_functions": ["unknownFunction"],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as mf:
        json.dump(manifest_data, mf)
        mf.flush()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as cf:
            json.dump(core_inventory, cf)
            cf.flush()
            total, errors = check_manifest(
                Path(mf.name),
                ts_core_inventory_path=Path(cf.name),
                enforce_ts_inventory=True,
            )
    assert any("Missing Python mapping" in e for e in errors)
    Path(mf.name).unlink(missing_ok=True)
    Path(cf.name).unlink(missing_ok=True)


def test_check_manifest_inscriber_function_valid() -> None:
    manifest_data = {
        "version": "1.0",
        "metadata": {"sdk": "py"},
        "entries": [
            {
                "id": "e-1",
                "source_sdk": "ts",
                "source_symbol": "inscriber.inscribe",
                "python_symbol": "standards_sdk_py.inscriber.client.inscribe",
                "status": "done",
            },
        ],
    }
    core_inventory = {
        "classes": {},
        "inscriber_functions": ["inscribe"],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as mf:
        json.dump(manifest_data, mf)
        mf.flush()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as cf:
            json.dump(core_inventory, cf)
            cf.flush()
            total, errors = check_manifest(
                Path(mf.name),
                ts_core_inventory_path=Path(cf.name),
                enforce_ts_inventory=True,
            )
    # inscribe has a valid Python mapping, so no missing Python function errors
    assert not any("Missing Python function" in e for e in errors)
    Path(mf.name).unlink(missing_ok=True)
    Path(cf.name).unlink(missing_ok=True)


# ── TS_CLASS_TO_PYTHON_CLASS / TS_INSCRIBER_FUNCTION_TO_PYTHON ───────


def test_ts_class_mapping_keys() -> None:
    assert "RegistryBrokerClient" in TS_CLASS_TO_PYTHON_CLASS
    assert "HederaMirrorNode" in TS_CLASS_TO_PYTHON_CLASS


def test_ts_inscriber_function_mapping_keys() -> None:
    assert "inscribe" in TS_INSCRIBER_FUNCTION_TO_PYTHON
    assert "generateQuote" in TS_INSCRIBER_FUNCTION_TO_PYTHON
