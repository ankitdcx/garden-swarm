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
FILE_SUFFIXES = (".md", ".json", ".py", ".txt", ".yml", ".yaml", ".cff")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked_files() -> set[str]:
    proc = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=True
    )
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def local_file_candidate(value: str) -> str | None:
    # A machine file reference is path-like, not an arbitrary sentence containing
    # a filename. Preserve leading dots because `.github/...` is a real path.
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


def generated_reference_policy() -> dict[str, dict[str, Any]]:
    payload = json.loads((ROOT / "gsl" / "REFERENCE_POLICY.json").read_text(encoding="utf-8"))
    if payload.get("schema") != "GardenRepositoryReferencePolicy/v1":
        raise SystemExit("unsupported GardenRepositoryReferencePolicy schema")
    return {
        str(row["reference"]): row
        for row in payload.get("generated_or_runtime_references") or []
    }


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
            owner = str(row.get("owner", ""))
            if not owner or owner not in tracked:
                return None, "GENERATED_OWNER_MISSING", row
            return owner, str(row.get("class", "GENERATED_OR_RUNTIME")), row

    return None, "UNRESOLVED", None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="/tmp/reference_closure_receipt.json")
    args = p.parse_args()

    tracked = tracked_files()
    basenames: dict[str, list[str]] = {}
    for rel in tracked:
        basenames.setdefault(Path(rel).name, []).append(rel)
    generated = generated_reference_policy()

    canonical = {
        rel for rel in tracked
        if rel.startswith("Garden_") and "_v15.5_FULL_" in rel and rel.endswith(".txt")
    }
    scanned: list[dict[str, str]] = []
    refs: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []

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
        except (OSError, json.JSONDecodeError):
            unresolved.append({"source": rel, "reference": "<unreadable source>"})
            continue

        for ref in sorted(set(found)):
            resolved, resolution_kind, policy = resolve_reference(
                ref,
                source=rel,
                tracked=tracked,
                basenames=basenames,
                generated=generated,
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
            "source-relative and unique-basename resolution",
            "declared generated/runtime references with tracked generating owner",
            "MCP tool allowlist against actual @mcp.tool decorators"
        ],
        "excluded_from_claim": [
            "semantic equivalence of identifiers",
            "natural-language references that are not machine-detectable path-like references",
            "canonical five-file semantic reference closure (owned by the canonical release receipt)",
            "external URLs"
        ],
        "scanner_version": "garden-repo-reference-closure/2",
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
