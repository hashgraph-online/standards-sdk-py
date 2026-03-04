"""Parity inventory generation from TypeScript and Go source SDKs."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from standards_sdk_py.parity.models import ParityManifest


def _run_json_stream(command: list[str], cwd: Path) -> list[dict[str, Any]]:
    process = subprocess.run(
        command,
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [line for line in process.stdout.splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def _extract_method_names(matches: list[dict[str, Any]]) -> list[str]:
    names: set[str] = set()
    for item in matches:
        meta = item.get("metaVariables", {})
        single = meta.get("single", {})
        method = single.get("M", {})
        text = method.get("text")
        if isinstance(text, str) and text:
            names.add(text)
    return sorted(names)


def _extract_ts_registry_broker_public_methods(repo_root: Path) -> list[str]:
    script = """
const fs = require("fs");
const ts = require("typescript");
const filePath = "src/services/registry-broker/client/base-client.ts";
const source = fs.readFileSync(filePath, "utf8");
const sourceFile = ts.createSourceFile(
  filePath,
  source,
  ts.ScriptTarget.Latest,
  true,
  ts.ScriptKind.TS,
);
function hasModifier(node, kind) {
  return !!(node.modifiers && node.modifiers.some(mod => mod.kind === kind));
}
const methods = [];
function visit(node) {
  if (ts.isClassDeclaration(node) && node.name && node.name.text === "RegistryBrokerClient") {
    for (const member of node.members) {
      const isMethodLike =
        ts.isMethodDeclaration(member) ||
        ts.isGetAccessorDeclaration(member) ||
        ts.isSetAccessorDeclaration(member);
      if (!isMethodLike) continue;
      if (
        hasModifier(member, ts.SyntaxKind.PrivateKeyword) ||
        hasModifier(member, ts.SyntaxKind.ProtectedKeyword)
      ) {
        continue;
      }
      let name = null;
      if (member.name && ts.isIdentifier(member.name)) {
        name = member.name.text;
      } else if (member.name && ts.isStringLiteral(member.name)) {
        name = member.name.text;
      }
      if (name && name !== "constructor") {
        methods.push(name);
      }
    }
  }
  ts.forEachChild(node, visit);
}
visit(sourceFile);
console.log(JSON.stringify(Array.from(new Set(methods)).sort()));
"""
    process = subprocess.run(
        ["node", "-e", script],
        cwd=str(repo_root / "standards-sdk"),
        check=True,
        capture_output=True,
        text=True,
    )
    parsed = json.loads(process.stdout)
    if isinstance(parsed, list):
        return [name for name in parsed if isinstance(name, str)]
    if isinstance(parsed, dict):
        return _extract_method_names([parsed])
    raise ValueError("Expected public method list from TypeScript extractor")


def _extract_ts_class_methods(
    repo_root: Path,
    class_sources: dict[str, str],
) -> dict[str, list[str]]:
    script = f"""
const fs = require("fs");
const ts = require("typescript");
const classSources = {json.dumps(class_sources)};
function hasModifier(node, kind) {{
  return !!(node.modifiers && node.modifiers.some(mod => mod.kind === kind));
}}
function extractMethods(filePath, className) {{
  const source = fs.readFileSync(filePath, "utf8");
  const sourceFile = ts.createSourceFile(
    filePath,
    source,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TS,
  );
  const methods = [];
  function visit(node) {{
    if (ts.isClassDeclaration(node) && node.name && node.name.text === className) {{
      for (const member of node.members) {{
        const isMethodLike =
          ts.isMethodDeclaration(member) ||
          ts.isGetAccessorDeclaration(member) ||
          ts.isSetAccessorDeclaration(member);
        if (!isMethodLike) continue;
        if (
          hasModifier(member, ts.SyntaxKind.PrivateKeyword) ||
          hasModifier(member, ts.SyntaxKind.ProtectedKeyword)
        ) {{
          continue;
        }}
        let name = null;
        if (member.name && ts.isIdentifier(member.name)) {{
          name = member.name.text;
        }} else if (member.name && ts.isStringLiteral(member.name)) {{
          name = member.name.text;
        }}
        if (name && name !== "constructor") {{
          methods.push(name);
        }}
      }}
    }}
    ts.forEachChild(node, visit);
  }}
  visit(sourceFile);
  return Array.from(new Set(methods)).sort();
}}
const result = {{}};
for (const [className, filePath] of Object.entries(classSources)) {{
  result[className] = extractMethods(filePath, className);
}}
console.log(JSON.stringify(result));
"""
    process = subprocess.run(
        ["node", "-e", script],
        cwd=str(repo_root / "standards-sdk"),
        check=True,
        capture_output=True,
        text=True,
    )
    parsed = json.loads(process.stdout)
    if not isinstance(parsed, dict):
        raise ValueError("Expected class method map from TypeScript extractor")
    result: dict[str, list[str]] = {}
    for class_name, methods in parsed.items():
        if isinstance(class_name, str) and isinstance(methods, list):
            result[class_name] = [method for method in methods if isinstance(method, str)]
    return result


def _extract_ts_inscriber_functions(repo_root: Path) -> list[str]:
    script = """
const fs = require("fs");
const ts = require("typescript");
const filePath = "src/inscribe/inscriber.ts";
const source = fs.readFileSync(filePath, "utf8");
const sourceFile = ts.createSourceFile(
  filePath,
  source,
  ts.ScriptTarget.Latest,
  true,
  ts.ScriptKind.TS,
);
const functions = [];
for (const statement of sourceFile.statements) {
  if (!ts.isFunctionDeclaration(statement) || !statement.name) continue;
  if (
    !statement.modifiers ||
    !statement.modifiers.some(mod => mod.kind === ts.SyntaxKind.ExportKeyword)
  ) continue;
  functions.push(statement.name.text);
}
console.log(JSON.stringify(Array.from(new Set(functions)).sort()));
"""
    process = subprocess.run(
        ["node", "-e", script],
        cwd=str(repo_root / "standards-sdk"),
        check=True,
        capture_output=True,
        text=True,
    )
    parsed = json.loads(process.stdout)
    if not isinstance(parsed, list):
        raise ValueError("Expected exported function list from TypeScript extractor")
    return [name for name in parsed if isinstance(name, str)]


def generate_inventories(repo_root: Path, output_dir: Path) -> tuple[int, int]:
    ts_class_sources = {
        "RegistryBrokerClient": "src/services/registry-broker/client/base-client.ts",
        "HederaMirrorNode": "src/services/mirror-node.ts",
        "HCS2Client": "src/hcs-2/client.ts",
        "HCS": "src/hcs-3/src/index.ts",
        "HCS5Client": "src/hcs-5/sdk.ts",
        "HCS6Client": "src/hcs-6/sdk.ts",
        "HCS7Client": "src/hcs-7/sdk.ts",
        "HCS10Client": "src/hcs-10/sdk.ts",
        "HCS11Client": "src/hcs-11/client.ts",
        "HCS12Client": "src/hcs-12/sdk.ts",
        "HCS14Client": "src/hcs-14/sdk.ts",
        "HCS15Client": "src/hcs-15/sdk.ts",
        "HCS16Client": "src/hcs-16/sdk.ts",
        "HCS17Client": "src/hcs-17/sdk.ts",
        "HCS18Client": "src/hcs-18/sdk.ts",
        "HCS20Client": "src/hcs-20/sdk.ts",
        "HCS21Client": "src/hcs-21/sdk.ts",
        "HCS26Client": "src/hcs-26/sdk.ts",
    }
    ts_class_methods = _extract_ts_class_methods(repo_root, ts_class_sources)
    ts_methods = _extract_ts_registry_broker_public_methods(repo_root)
    ts_inscriber_functions = _extract_ts_inscriber_functions(repo_root)
    go_files = sorted(
        (repo_root / "standards-sdk-go" / "pkg" / "registrybroker").glob("*.go"),
    )
    go_cmd = [
        "ast-grep",
        "run",
        "--lang",
        "go",
        "-p",
        "func ($R) $M($$$A) $RET { $$$B }",
        *[str(path) for path in go_files],
        "--json=stream",
    ]

    go_matches = _run_json_stream(go_cmd, repo_root)
    go_methods = _extract_method_names(go_matches)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "ts-registry-broker-methods.json").write_text(
        json.dumps({"methods": ts_methods}, indent=2),
        encoding="utf-8",
    )
    (output_dir / "ts-core-client-methods.json").write_text(
        json.dumps(
            {
                "classes": ts_class_methods,
                "inscriber_functions": ts_inscriber_functions,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / "go-registry-broker-methods.json").write_text(
        json.dumps({"methods": go_methods}, indent=2),
        encoding="utf-8",
    )
    ts_count = sum(len(methods) for methods in ts_class_methods.values()) + len(
        ts_inscriber_functions
    )
    return ts_count, len(go_methods)


def validate_manifest(path: Path) -> int:
    raw = json.loads(path.read_text(encoding="utf-8"))
    ParityManifest.model_validate(raw)
    return len(raw["entries"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate cross-SDK parity inventories.")
    parser.add_argument(
        "--repo-root",
        default="..",
        help="Path to hashgraph-online repository root.",
    )
    parser.add_argument(
        "--output-dir",
        default="src/standards_sdk_py/parity/generated",
        help="Output directory for generated inventory files.",
    )
    parser.add_argument(
        "--manifest",
        default="src/standards_sdk_py/parity/parity-manifest.json",
        help="Parity manifest path to validate.",
    )
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    manifest_path = Path(args.manifest).resolve()
    ts_count, go_count = generate_inventories(repo_root, output_dir)
    manifest_count = validate_manifest(manifest_path)
    print(
        f"Generated inventories: ts={ts_count}, go={go_count}; manifest entries={manifest_count}",
    )


if __name__ == "__main__":
    main()
