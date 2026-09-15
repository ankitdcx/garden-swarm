#!/usr/bin/env python3
"""Build one fail-closed coherent-complete GardenReviewPacket/v1.

The builder is deliberately conservative. Canonical-design targets carry the
complete current five-file canonical source set. Implementation targets carry a
fixed-point local reference/import closure. If required ledger/test evidence is
missing or the closure is ambiguous, completeness is INCOMPLETE rather than
silently filtering evidence.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from tools.validate_review_packet import canonical_hash

ROOT = Path(".").resolve()
MATRIX = ROOT / "agents/design-review-matrix.json"
SELECTION = ROOT / "agents/runtime/design-target-selection.json"
POLICY = ROOT / "agents/process-control-policy.json"
OUT = ROOT / "agents/runtime/review-packet.json"
RECEIPT = ROOT / "agents/runtime/packet-completeness-receipt.json"
TEST_RECEIPT = ROOT / "agents/runtime/pre-review-test-receipt.json"
LEDGER_SNAPSHOT = ROOT / "agents/runtime/review-ledger-snapshot.json"

TEXT_SUFFIXES = {".py", ".json", ".yml", ".yaml", ".md", ".txt", ".toml"}
CANONICAL_GLOB = "Garden_*_v15.5_FULL_2026-09-12.txt"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def bounded_target(target: dict[str, Any]) -> tuple[str, str, str]:
    path = ROOT / str(target["source_file"])
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    start = text.find(str(target["start_anchor"]))
    end = text.find(str(target["end_anchor"]), start + len(str(target["start_anchor"])))
    if start < 0 or end <= start:
        raise ValueError("target anchors do not resolve exactly")
    return text[start:end].strip(), path.relative_to(ROOT).as_posix(), sha256_bytes(raw)


def current_diff() -> tuple[str, str, str, list[str]]:
    head = git("rev-parse", "HEAD")
    try:
        base = git("rev-parse", "HEAD^1")
    except subprocess.CalledProcessError:
        base = head
    if base == head:
        diff = ""
        changed: list[str] = []
        mode = "NO_CHANGE"
    else:
        diff = subprocess.check_output(["git", "diff", "--no-ext-diff", "--binary", f"{base}..{head}"], text=True)
        changed = [x for x in git("diff", "--name-only", f"{base}..{head}").splitlines() if x]
        mode = "DIFF" if changed else "NO_CHANGE"
    digest = sha256_bytes(diff.encode("utf-8"))
    return base, head, mode, changed, digest, diff


def python_symbols_at(ref: str, path: str) -> dict[str, str]:
    try:
        text = subprocess.check_output(["git", "show", f"{ref}:{path}"], text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return {}
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            segment = ast.get_source_segment(text, node) or node.name
            out[f"{type(node).__name__}:{node.name}"] = sha256_bytes(segment.encode("utf-8"))
    return out


def changed_symbols(base: str, head: str, changed_files: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in changed_files:
        if path.endswith(".py"):
            before = python_symbols_at(base, path)
            after = python_symbols_at(head, path)
            for symbol in sorted(set(before) | set(after)):
                if before.get(symbol) != after.get(symbol):
                    rows.append({"path": path, "symbol": symbol, "derivation": "PYTHON_AST_DEFINITION_HASH_DIFF"})
        else:
            rows.append({"path": path, "symbol": f"file::{path}", "derivation": "FILE_LEVEL_FALLBACK_NON_PYTHON"})
    return rows


def safe_text(path: Path) -> str | None:
    if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
        return None
    try:
        raw = path.read_bytes()
        if len(raw) > 1_500_000:
            return None
        return raw.decode("utf-8")
    except Exception:
        return None


def local_python_refs(path: Path, text: str) -> set[Path]:
    refs: set[Path] = set()
    if path.suffix != ".py":
        return refs
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return refs
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    for mod in modules:
        candidate = ROOT / (mod.replace(".", "/") + ".py")
        pkg = ROOT / mod.replace(".", "/") / "__init__.py"
        if candidate.is_file(): refs.add(candidate)
        if pkg.is_file(): refs.add(pkg)
    return refs


def path_literal_refs(text: str) -> set[Path]:
    refs: set[Path] = set()
    for value in re.findall(r"[\"']([^\"']{1,180})[\"']", text):
        if value.startswith(("http://", "https://")) or "\n" in value:
            continue
        candidate = ROOT / value
        try:
            resolved = candidate.resolve()
        except Exception:
            continue
        if resolved.is_file() and ROOT in resolved.parents and resolved.suffix.lower() in TEXT_SUFFIXES:
            refs.add(resolved)
    return refs


def referencing_tests_and_workflows(seed: Path) -> set[Path]:
    refs: set[Path] = set()
    needle_options = {seed.as_posix(), seed.name, seed.stem, seed.as_posix().replace("/", ".").removesuffix(".py")}
    for base in [ROOT / "tests", ROOT / ".github/workflows"]:
        if not base.exists(): continue
        for path in base.rglob("*"):
            text = safe_text(path)
            if text is not None and any(needle and needle in text for needle in needle_options):
                refs.add(path.resolve())
    return refs


def implementation_closure(seed_rel: str) -> tuple[list[dict[str, Any]], list[str]]:
    seed = (ROOT / seed_rel).resolve()
    queue = [seed]
    seen: set[Path] = set()
    ambiguous: list[str] = []
    while queue:
        path = queue.pop(0)
        if path in seen: continue
        if ROOT not in path.parents and path != ROOT:
            ambiguous.append(f"outside-root:{path}")
            continue
        text = safe_text(path)
        if text is None:
            ambiguous.append(f"unreadable-or-oversize:{path.relative_to(ROOT)}")
            continue
        seen.add(path)
        new_refs = local_python_refs(path, text) | path_literal_refs(text)
        if path == seed:
            new_refs |= referencing_tests_and_workflows(seed)
        for ref in sorted(new_refs):
            if ref not in seen: queue.append(ref)
    objects = []
    for path in sorted(seen):
        raw = path.read_bytes()
        objects.append({
            "object_id": f"file:{path.relative_to(ROOT).as_posix()}",
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256_bytes(raw),
            "content": raw.decode("utf-8")
        })
    return objects, ambiguous


def canonical_closure() -> tuple[list[dict[str, Any]], list[str]]:
    paths = sorted(ROOT.glob(CANONICAL_GLOB))
    if len(paths) != 5:
        return [], [f"expected-5-canonical-files-found-{len(paths)}"]
    objects = []
    for path in paths:
        raw = path.read_bytes()
        objects.append({"object_id": f"file:{path.name}", "path": path.name, "sha256": sha256_bytes(raw), "content": raw.decode("utf-8")})
    return objects, []


def extract_affected(text: str) -> dict[str, list[str]]:
    schemas = sorted(set(re.findall(r"\bSCHEMA-[A-Z0-9-]+\b", text)))
    tests = sorted(set(re.findall(r"\bTEST-[A-Z0-9-]+\b", text)))
    registries = sorted(set(re.findall(r"\bREG-[A-Z0-9-]+\b", text)))
    invariants = sorted(set(re.findall(r"\b(?:[A-Z]{2,}(?:-[A-Z0-9]+)*)-\d{3}\b", text)) - set(tests) - set(registries))
    contracts = sorted(set(re.findall(r"\b[A-Z][A-Za-z0-9_]{2,}\b(?=.{0,40}\bFunctionContract\b)", text)))
    return {"schemas": schemas, "function_contracts": contracts, "invariants": invariants, "tests": tests, "registries": registries, "implementation_bindings": []}


def selected_ledger_entries(snapshot: Any, needles: set[str]) -> list[Any]:
    if not isinstance(snapshot, (list, dict)):
        return []
    rows = snapshot if isinstance(snapshot, list) else snapshot.get("items") or snapshot.get("issues") or snapshot.get("comments") or []
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows:
        blob = json.dumps(row, ensure_ascii=False)
        if any(n and n in blob for n in needles):
            out.append(row)
    return out


def main() -> int:
    matrix = read_json(MATRIX)
    selection = read_json(SELECTION)
    target_id = selection.get("target_id") or matrix.get("active_target_id")
    matches = [x for x in matrix.get("targets", []) if x.get("target_id") == target_id]
    if len(matches) != 1:
        raise SystemExit("selected target does not resolve exactly once")
    target = matches[0]
    target_text, target_path, target_source_hash = bounded_target(target)
    base, head, diff_mode, changed_files_list, diff_digest, raw_diff = current_diff()

    if target.get("target_kind") == "canonical_design":
        closure_objects, ambiguous = canonical_closure()
        closure_algorithm = "CANONICAL_FIVE_FILE_WHOLE_SOURCE_V1"
    else:
        closure_objects, ambiguous = implementation_closure(target_path)
        closure_algorithm = "LOCAL_IMPORT_PATH_TEST_WORKFLOW_FIXED_POINT_V1"

    closure_text = "\n".join(str(x.get("content", "")) for x in closure_objects)
    affected = extract_affected(closure_text)
    declared_ids = [str(x["object_id"]) for x in closure_objects]
    exclusions: list[dict[str, str]] = []
    completeness_blockers: list[str] = list(ambiguous)

    test_receipt: Any = None
    if TEST_RECEIPT.exists():
        test_receipt = read_json(TEST_RECEIPT)
    else:
        completeness_blockers.append("missing-pre-review-test-receipt")
        exclusions.append({"object_id": "exact-head-pre-review-test-receipt", "reason_code": "REQUIRED_EVIDENCE_UNAVAILABLE", "reason": "Workflow did not create the exact-head pre-review test receipt before packet construction."})

    ledger_entries: list[Any] = []
    if LEDGER_SNAPSHOT.exists():
        snapshot = read_json(LEDGER_SNAPSHOT)
        needles = {target_id, target_path, *affected["schemas"], *affected["function_contracts"], *affected["invariants"], *affected["tests"], *affected["registries"]}
        ledger_entries = selected_ledger_entries(snapshot, needles)
    else:
        completeness_blockers.append("missing-review-ledger-snapshot")
        exclusions.append({"object_id": "live-review-ledger-snapshot", "reason_code": "REQUIRED_EVIDENCE_UNAVAILABLE", "reason": "Workflow did not create the live governed issue/finding snapshot before packet construction."})

    process_version = "GardenProcess-v1-current"
    if POLICY.exists():
        process_version = str(read_json(POLICY).get("process_version") or process_version)

    cycle_id = f"garden-{int(time.time() // 3600)}-{target_id}-{head[:12]}"
    packet: dict[str, Any] = {
        "schema": "GardenReviewPacket/v1",
        "cycle_id": cycle_id,
        "public_repo": {"status": "BOUND", "repository": os.getenv("GITHUB_REPOSITORY", "ankitdcx/garden-swarm"), "commit": head},
        "private_repo": {"status": "PRIVATE_REPO_INACCESSIBLE", "reason": "Public GitHub Actions review lane has no approved private-repository credential."},
        "canonical_version": str(matrix.get("design_epoch")),
        "design_epoch": str(matrix.get("design_epoch")),
        "canonical_source_root_sha256": str(matrix.get("canonical_source_root_sha256")),
        "process_version": process_version,
        "target": {
            "target_id": target_id,
            "target_kind": target.get("target_kind"),
            "review_question": target.get("review_question"),
            "source_file": target_path,
            "source_hash": target_source_hash,
            "start_anchor": target.get("start_anchor"),
            "end_anchor": target.get("end_anchor"),
            "bounded_text": target_text
        },
        "diffs": [{"repo": "garden-swarm", "mode": diff_mode, "base": base, "head": head, "digest": diff_digest, "diff": raw_diff}],
        "changed_files": changed_files_list,
        "changed_symbols": changed_symbols(base, head, changed_files_list),
        "closure": {
            "algorithm": closure_algorithm,
            "declared_objects": declared_ids,
            "included_objects": declared_ids,
            "objects": closure_objects
        },
        "affected_objects": affected,
        "ci_test_evidence": [] if test_receipt is None else [test_receipt],
        "linked_findings": ledger_entries,
        "active_freezes": [x for x in ledger_entries if "freeze" in json.dumps(x, ensure_ascii=False).lower()],
        "exclusions": exclusions,
        "closure_frontier": {
            "status": "AMBIGUOUS" if ambiguous else "CLOSED_UNDER_DECLARED_ALGORITHM",
            "algorithm": closure_algorithm,
            "unresolved_candidates": ambiguous
        },
        "packet_construction_version": "GardenReviewPacketBuilder/v1",
        "construction_limitations": completeness_blockers
    }
    packet["packet_hash"] = canonical_hash(packet)

    status = "PASS" if not completeness_blockers else "PACKET_INCOMPLETE"
    receipt = {
        "schema": "PacketCompletenessReceipt/v1",
        "criterion": "COHERENT_COMPLETE",
        "cycle_id": cycle_id,
        "packet_hash": packet["packet_hash"],
        "status": status,
        "closure_algorithm": closure_algorithm,
        "declared_object_count": len(declared_ids),
        "included_object_count": len(declared_ids),
        "manual_unexplained_exclusions": 0,
        "exclusions": exclusions,
        "blockers": completeness_blockers,
        "semantic_delta_admitted": False
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"cycle_id": cycle_id, "packet_hash": packet["packet_hash"], "status": status, "closure_objects": len(declared_ids)}, sort_keys=True))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
