#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FILE_SUFFIXES = (".md", ".json", ".py", ".txt", ".yml", ".yaml", ".cff", ".toml")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
LOCAL_PACKAGE_ROOTS = {"prototype", "server", "swarm", "tools", "scripts"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked_files() -> set[str]:
    proc = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=True
    )
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def local_file_candidate(value: str) -> str | None:
    value = value.strip().strip("'\"").rstrip(",:;)]}")
    if not value or value.startswith(("http://", "https://", "garden://", "/")):
        return None
    if any(ch.isspace() for ch in value):
        return None
    if any(ch in value for ch in ("{", "}", "*", "|")):
        return None
    if not value.lower().endswith(FILE_SUFFIXES):
        return None
    return value


def json_file_refs(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, dict):
        for child in value.values():
            refs.extend(json_file_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.extend(json_file_refs(child))
    elif isinstance(value, str):
        candidate = local_file_candidate(value)
        if candidate:
            refs.append(candidate)
    return refs


def markdown_file_refs(text: str) -> list[str]:
    refs: list[str] = []
    for raw in MARKDOWN_LINK_RE.findall(text):
        candidate = local_file_candidate(raw.split("#", 1)[0])
        if candidate:
            refs.append(candidate)
    for raw in INLINE_CODE_RE.findall(text):
        candidate = local_file_candidate(raw.split("#", 1)[0])
        if candidate:
            refs.append(candidate)
    return refs


def decorator_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return decorator_name(node.func)
    if isinstance(node, ast.Attribute):
        left = decorator_name(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def mcp_tool_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
            decorator_name(d) == "mcp.tool" for d in node.decorator_list
        ):
            out.add(node.name)
    return out


def module_candidates(module: str) -> tuple[str, str]:
    stem = module.replace(".", "/")
    return f"{stem}.py", f"{stem}/__init__.py"


def module_path(module: str, tracked: set[str]) -> str | None:
    for candidate in module_candidates(module):
        if candidate in tracked:
            return candidate
    return None


def source_package(source: str) -> str:
    path = Path(source)
    if path.suffix != ".py":
        return ""
    parts = list(path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    else:
        parts.pop()
    return ".".join(parts)


def resolve_relative_module(source: str, level: int, module: str | None) -> str:
    package = source_package(source).split(".") if source_package(source) else []
    keep = max(0, len(package) - max(0, level - 1))
    prefix = package[:keep]
    suffix = module.split(".") if module else []
    return ".".join(prefix + suffix)


def exported_symbols(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    symbols: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    symbols.add(target.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                symbols.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                symbols.add(alias.asname or alias.name)
    return symbols


def python_import_refs(source: str, path: Path, tracked: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    refs: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in LOCAL_PACKAGE_ROOTS:
                    continue
                target = module_path(alias.name, tracked)
                row = {"source": source, "reference": f"import {alias.name}", "resolved": target, "resolution_kind": "PYTHON_IMPORT_MODULE"}
                refs.append(row)
                if target is None:
                    unresolved.append({"source": source, "reference": f"import {alias.name}"})
        elif isinstance(node, ast.ImportFrom):
            module = resolve_relative_module(source, node.level, node.module) if node.level else (node.module or "")
            if not module:
                continue
            root = module.split(".")[0]
            if root not in LOCAL_PACKAGE_ROOTS:
                continue
            target = module_path(module, tracked)
            if target is None:
                refs.append({"source": source, "reference": f"from {module} import ...", "resolved": None, "resolution_kind": "PYTHON_IMPORT_MODULE"})
                unresolved.append({"source": source, "reference": f"from {module} import ..."})
                continue
            symbols = exported_symbols(ROOT / target)
            for alias in node.names:
                if alias.name == "*":
                    refs.append({"source": source, "reference": f"from {module} import *", "resolved": target, "resolution_kind": "PYTHON_IMPORT_STAR"})
                    continue
                submodule = module_path(f"{module}.{alias.name}", tracked)
                symbol_ok = alias.name in symbols or submodule is not None
                resolved = submodule or target if symbol_ok else None
                refs.append({"source": source, "reference": f"from {module} import {alias.name}", "resolved": resolved, "resolution_kind": "PYTHON_IMPORT_SYMBOL"})
                if not symbol_ok:
                    unresolved.append({"source": source, "reference": f"from {module} import {alias.name}"})
    return refs, unresolved


def generated_reference_policy(tracked: set[str]) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    policy_path = ROOT / "gsl" / "REFERENCE_POLICY.json"
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    defects: list[dict[str, str]] = []
    if payload.get("schema") != "GardenRepositoryReferencePolicy/v2":
        defects.append({"source": "gsl/REFERENCE_POLICY.json", "reference": "UNSUPPORTED_REFERENCE_POLICY_SCHEMA"})
    if not payload.get("source_obligation_refs"):
        defects.append({"source": "gsl/REFERENCE_POLICY.json", "reference": "REFERENCE_POLICY_SOURCE_OBLIGATION_MISSING"})
    allowed = set(payload.get("allowed_classes") or [])
    rows: dict[str, dict[str, Any]] = {}
    for row in payload.get("generated_or_runtime_references") or []:
        ref = str(row.get("reference", ""))
        owner = str(row.get("owner", ""))
        cls = str(row.get("class", ""))
        evidence = str(row.get("owner_evidence", ""))
        if not ref or ref in rows:
            defects.append({"source": "gsl/REFERENCE_POLICY.json", "reference": f"INVALID_OR_DUPLICATE_POLICY_REF:{ref}"})
            continue
        if cls not in allowed:
            defects.append({"source": "gsl/REFERENCE_POLICY.json", "reference": f"UNALLOWLISTED_POLICY_CLASS:{cls}"})
        if owner not in tracked:
            defects.append({"source": "gsl/REFERENCE_POLICY.json", "reference": f"GENERATED_OWNER_MISSING:{owner}"})
        elif not evidence or evidence not in (ROOT / owner).read_text(encoding="utf-8", errors="ignore"):
            defects.append({"source": "gsl/REFERENCE_POLICY.json", "reference": f"GENERATED_OWNER_EVIDENCE_MISSING:{ref}:{owner}"})
        rows[ref] = row
    return rows, defects


def resolve_reference(
    ref: str,
    *,
    source: str,
    tracked: set[str],
    basenames: dict[str, list[str]],
    generated: dict[str, dict[str, Any]],
) -> tuple[str | None, str, dict[str, Any] | None]:
    if ref in tracked:
        return ref, "TRACKED_EXACT", None
    source_relative = (Path(source).parent / ref).as_posix()
    if source_relative in tracked:
        return source_relative, "TRACKED_SOURCE_RELATIVE", None
    same_name = basenames.get(Path(ref).name, [])
    if len(same_name) == 1 and "/" not in ref:
        return same_name[0], "TRACKED_UNIQUE_BASENAME", None
    candidates = [ref, ref.removeprefix("./"), ref.removeprefix("/")]
    for candidate in candidates:
        if candidate in generated:
            row = generated[candidate]
            return str(row["owner"]), str(row["class"]), row
    return None, "UNRESOLVED", None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="/tmp/reference_closure_receipt.json")
    args = p.parse_args()

    tracked = tracked_files()
    basenames: dict[str, list[str]] = {}
    for rel in tracked:
        basenames.setdefault(Path(rel).name, []).append(rel)
    generated, policy_defects = generated_reference_policy(tracked)

    canonical = {
        rel for rel in tracked
        if rel.startswith("Garden_") and "_v15.5_FULL_" in rel and rel.endswith(".txt")
    }
    scanned: list[dict[str, str]] = []
    refs: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = list(policy_defects)

    for rel in sorted(tracked):
        path = ROOT / rel
        if rel in canonical or not path.is_file():
            continue
        if path.suffix.lower() not in FILE_SUFFIXES:
            continue
        scanned.append({"path": rel, "sha256": sha256(path)})
        found: list[str] = []
        try:
            if path.suffix.lower() == ".json":
                found = json_file_refs(json.loads(path.read_text(encoding="utf-8")))
            elif path.suffix.lower() in {".md", ".txt"}:
                found = markdown_file_refs(path.read_text(encoding="utf-8", errors="ignore"))
            elif path.suffix.lower() == ".py":
                py_refs, py_unresolved = python_import_refs(rel, path, tracked)
                refs.extend(py_refs)
                unresolved.extend(py_unresolved)
        except (OSError, json.JSONDecodeError, SyntaxError):
            unresolved.append({"source": rel, "reference": "<unreadable-or-unparseable-source>"})
            continue

        for ref in sorted(set(found)):
            resolved, resolution_kind, policy = resolve_reference(
                ref, source=rel, tracked=tracked, basenames=basenames, generated=generated
            )
            row: dict[str, Any] = {
                "source": rel,
                "reference": ref,
                "resolved": resolved,
                "resolution_kind": resolution_kind,
            }
            if policy is not None:
                row["reference_policy"] = policy
            refs.append(row)
            if resolved is None:
                unresolved.append({"source": rel, "reference": ref})

    envelope = json.loads((ROOT / "gsl" / "AGENT_ENVELOPES.json").read_text(encoding="utf-8"))
    public_mcp = next(
        (x for x in envelope.get("envelopes", []) if x.get("envelope_id") == "AGENT-ENVELOPE-GARDEN-PUBLIC-MCP-v1"),
        None,
    )
    expected_tools = set((public_mcp or {}).get("tool_allowlist") or [])
    observed_tools = mcp_tool_names(ROOT / "server" / "mcp_service.py")
    if expected_tools != observed_tools:
        unresolved.append({
            "source": "gsl/AGENT_ENVELOPES.json",
            "reference": f"MCP_TOOL_SET_MISMATCH expected={sorted(expected_tools)} observed={sorted(observed_tools)}",
        })

    receipt = {
        "schema": "ReferenceClosureReceipt/v1",
        "repository": "ankitdcx/garden-swarm",
        "design_epoch_ref": envelope.get("design_epoch_ref"),
        "coverage": [
            "path-like tracked JSON string references",
            "Markdown/text inline-code and Markdown-link local file references",
            "Python local module imports and from-import symbol resolution",
            "source-relative and unique-basename resolution",
            "generated/runtime references only when class allowlisted, owner tracked, and owner evidence present",
            "MCP tool allowlist against actual @mcp.tool decorators"
        ],
        "excluded_from_claim": [
            "semantic equivalence of arbitrary natural-language identifiers",
            "canonical five-file semantic reference closure (owned by the canonical release receipt)",
            "external URLs and external Python packages"
        ],
        "scanner_version": "garden-repo-reference-closure/3",
        "reference_policy_sha256": sha256(ROOT / "gsl" / "REFERENCE_POLICY.json"),
        "scanned_sources": scanned,
        "reference_count": len(refs),
        "references": refs,
        "unresolved_count": len(unresolved),
        "unresolved": unresolved,
        "status": "PASS" if not unresolved else "FAIL",
        "semantic_reference_closure_proved": False
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "references": len(refs), "unresolved": len(unresolved), "output": str(out)}, sort_keys=True))
    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
