"""Parity manifest checker."""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from pathlib import Path

from standards_sdk_py.parity.models import ParityManifest, ParityStatus

_FIRST_CAP_RE = re.compile("(.)([A-Z][a-z]+)")
_ALL_CAP_RE = re.compile("([a-z0-9])([A-Z])")

TS_CLASS_TO_PYTHON_CLASS = {
    "RegistryBrokerClient": "standards_sdk_py.registry_broker.RegistryBrokerClient",
    "HederaMirrorNode": "standards_sdk_py.mirror.HederaMirrorNode",
    "HCS2Client": "standards_sdk_py.hcs2.HCS2Client",
    "HCS": "standards_sdk_py.hcs3.HCS",
    "HCS5Client": "standards_sdk_py.hcs5.HCS5Client",
    "HCS6Client": "standards_sdk_py.hcs6.HCS6Client",
    "HCS7Client": "standards_sdk_py.hcs7.HCS7Client",
    "HCS10Client": "standards_sdk_py.hcs10.HCS10Client",
    "HCS11Client": "standards_sdk_py.hcs11.HCS11Client",
    "HCS12Client": "standards_sdk_py.hcs12.HCS12Client",
    "HCS14Client": "standards_sdk_py.hcs14.HCS14Client",
    "HCS15Client": "standards_sdk_py.hcs15.HCS15Client",
    "HCS16Client": "standards_sdk_py.hcs16.HCS16Client",
    "HCS17Client": "standards_sdk_py.hcs17.HCS17Client",
    "HCS18Client": "standards_sdk_py.hcs18.HCS18Client",
    "HCS20Client": "standards_sdk_py.hcs20.HCS20Client",
    "HCS21Client": "standards_sdk_py.hcs21.HCS21Client",
    "HCS26Client": "standards_sdk_py.hcs26.HCS26Client",
}

TS_INSCRIBER_FUNCTION_TO_PYTHON = {
    "generateQuote": "standards_sdk_py.inscriber.generate_quote",
    "getRegistryBrokerQuote": "standards_sdk_py.inscriber.get_registry_broker_quote",
    "inscribe": "standards_sdk_py.inscriber.inscribe",
    "inscribeViaRegistryBroker": "standards_sdk_py.inscriber.inscribe_via_registry_broker",
    "inscribeWithSigner": "standards_sdk_py.inscriber.inscribe_with_signer",
    "retrieveInscription": "standards_sdk_py.inscriber.retrieve_inscription",
    "waitForInscriptionConfirmation": (
        "standards_sdk_py.inscriber.wait_for_inscription_confirmation"
    ),
}


def _resolve_symbol(path: str) -> object:
    parts = path.split(".")
    if len(parts) < 2:
        raise ValueError(f"Invalid python symbol path: {path}")

    module: object | None = None
    attr_parts: list[str] = []
    for index in range(len(parts) - 1, 0, -1):
        module_name = ".".join(parts[:index])
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
        attr_parts = parts[index:]
        break

    if module is None or not attr_parts:
        raise ModuleNotFoundError(f"Unable to import module for symbol path: {path}")

    current: object = module
    for part in attr_parts:
        if not hasattr(current, part):
            raise AttributeError(f"Missing attribute {part} in symbol path {path}")
        current = getattr(current, part)
    return current


def _load_methods(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    methods = payload.get("methods")
    if not isinstance(methods, list):
        raise ValueError(f"Invalid method inventory format: {path}")
    return [name for name in methods if isinstance(name, str)]


def _camel_to_snake(name: str) -> str:
    first_pass = _FIRST_CAP_RE.sub(r"\1_\2", name)
    return _ALL_CAP_RE.sub(r"\1_\2", first_pass).lower()


def _load_core_inventory(path: Path) -> tuple[dict[str, list[str]], list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    classes_raw = payload.get("classes")
    if not isinstance(classes_raw, dict):
        raise ValueError(f"Invalid core inventory classes format: {path}")
    classes: dict[str, list[str]] = {}
    for class_name, methods in classes_raw.items():
        if isinstance(class_name, str) and isinstance(methods, list):
            classes[class_name] = [method for method in methods if isinstance(method, str)]
    functions_raw = payload.get("inscriber_functions")
    if not isinstance(functions_raw, list):
        raise ValueError(f"Invalid core inventory inscriber_functions format: {path}")
    functions = [name for name in functions_raw if isinstance(name, str)]
    return classes, functions


def check_manifest(
    manifest_path: Path,
    ts_inventory_path: Path | None = None,
    ts_core_inventory_path: Path | None = None,
    *,
    enforce_ts_inventory: bool = False,
) -> tuple[int, list[str]]:
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = ParityManifest.model_validate(raw)
    errors: list[str] = []

    seen_ids: set[str] = set()
    for entry in manifest.entries:
        if entry.id in seen_ids:
            errors.append(f"Duplicate entry id: {entry.id}")
        seen_ids.add(entry.id)

        if entry.status in {ParityStatus.done, ParityStatus.verified}:
            try:
                _resolve_symbol(entry.python_symbol)
            except Exception as exc:
                errors.append(f"{entry.id}: failed to resolve {entry.python_symbol}: {exc}")

    if enforce_ts_inventory and ts_inventory_path is not None and ts_inventory_path.exists():
        ts_methods = _load_methods(ts_inventory_path)
        by_source_symbol: dict[str, list[ParityStatus]] = {}
        for entry in manifest.entries:
            if entry.source_sdk != "ts":
                continue
            by_source_symbol.setdefault(entry.source_symbol, []).append(entry.status)
        for method in ts_methods:
            source_symbol = f"RegistryBrokerClient.{method}"
            statuses = by_source_symbol.get(source_symbol)
            if not statuses:
                errors.append(f"Missing TS parity manifest entry for {source_symbol}")
                continue
            if not any(status in {ParityStatus.done, ParityStatus.verified} for status in statuses):
                errors.append(f"TS parity entry not completed for {source_symbol}")
            try:
                _resolve_symbol(f"standards_sdk_py.registry_broker.RegistryBrokerClient.{method}")
            except Exception as exc:
                errors.append(f"Missing Python method for TS symbol {source_symbol}: {exc}")

    if (
        enforce_ts_inventory
        and ts_core_inventory_path is not None
        and ts_core_inventory_path.exists()
    ):
        class_methods, inscriber_functions = _load_core_inventory(ts_core_inventory_path)
        by_source_symbol_core: dict[str, list[ParityStatus]] = {}
        for entry in manifest.entries:
            if entry.source_sdk != "ts":
                continue
            by_source_symbol_core.setdefault(entry.source_symbol, []).append(entry.status)

        for class_name, methods in class_methods.items():
            python_class = TS_CLASS_TO_PYTHON_CLASS.get(class_name)
            if python_class is None:
                continue
            for method in methods:
                source_symbol = f"{class_name}.{method}"
                statuses = by_source_symbol_core.get(source_symbol)
                if not statuses:
                    errors.append(f"Missing TS parity manifest entry for {source_symbol}")
                elif not any(
                    status in {ParityStatus.done, ParityStatus.verified} for status in statuses
                ):
                    errors.append(f"TS parity entry not completed for {source_symbol}")
                method_symbol = f"{python_class}.{method}"
                snake_method_symbol = f"{python_class}.{_camel_to_snake(method)}"
                try:
                    _resolve_symbol(method_symbol)
                except Exception:
                    try:
                        _resolve_symbol(snake_method_symbol)
                    except Exception as exc:
                        errors.append(
                            f"Missing Python method for TS symbol {source_symbol}: {exc}",
                        )

        for function_name in inscriber_functions:
            source_symbol = f"inscriber.{function_name}"
            statuses = by_source_symbol_core.get(source_symbol)
            if not statuses:
                errors.append(f"Missing TS parity manifest entry for {source_symbol}")
            elif not any(
                status in {ParityStatus.done, ParityStatus.verified} for status in statuses
            ):
                errors.append(f"TS parity entry not completed for {source_symbol}")
            python_symbol = TS_INSCRIBER_FUNCTION_TO_PYTHON.get(function_name)
            if python_symbol is None:
                errors.append(f"Missing Python mapping for TS inscriber function {function_name}")
                continue
            try:
                _resolve_symbol(python_symbol)
            except Exception as exc:
                errors.append(
                    f"Missing Python function for TS symbol {source_symbol}: {exc}",
                )

    return len(manifest.entries), errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate standards-sdk-py parity manifest.")
    parser.add_argument(
        "--manifest",
        default="src/standards_sdk_py/parity/parity-manifest.json",
        help="Path to parity manifest JSON.",
    )
    parser.add_argument(
        "--ts-inventory",
        default="src/standards_sdk_py/parity/generated/ts-registry-broker-methods.json",
        help="Path to TypeScript registry broker inventory JSON.",
    )
    parser.add_argument(
        "--ts-core-inventory",
        default="src/standards_sdk_py/parity/generated/ts-core-client-methods.json",
        help="Path to TypeScript core class/function inventory JSON.",
    )
    parser.add_argument(
        "--strict-ts-inventory",
        action="store_true",
        help="Require full TS inventory coverage checks against the manifest.",
    )
    args = parser.parse_args()
    manifest_path = Path(args.manifest)
    ts_inventory_path = Path(args.ts_inventory)
    ts_core_inventory_path = Path(args.ts_core_inventory)
    if not manifest_path.exists():
        print(f"Manifest file not found: {manifest_path}", file=sys.stderr)
        raise SystemExit(1)
    strict_default_manifest = args.manifest == "src/standards_sdk_py/parity/parity-manifest.json"
    total, errors = check_manifest(
        manifest_path,
        ts_inventory_path=ts_inventory_path,
        ts_core_inventory_path=ts_core_inventory_path,
        enforce_ts_inventory=args.strict_ts_inventory or strict_default_manifest,
    )
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        raise SystemExit(1)
    print(f"Parity manifest valid ({total} entries).")


if __name__ == "__main__":
    main()
