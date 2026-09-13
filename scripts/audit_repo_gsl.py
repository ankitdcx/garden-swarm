#!/usr/bin/env python3
from __future__ import annotations

import argparse
from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_MODULES = {
    "SOURCE_IDENTITY", "GSL_TYPING", "DESIGN_EPOCH", "SOURCE_OBLIGATION",
    "DEPENDENCY", "FUNCTION_CONTRACT", "COMPARE", "REASON", "PROOF", "AAP",
    "AUTHORITY", "ACTION_GATE", "PROCESS_ALGEBRA", "POLICY_ALGEBRA",
    "DECISION_ALGEBRA", "CONFORMANCE_ALGEBRA", "EVIDENCE_ALGEBRA",
    "BRIDGE_ALGEBRA", "AUDIT", "COMPLIANCE", "HUMAN_SOVEREIGNTY", "SECURITY",
    "PRIVACY", "SAFETY", "PIPELINE_CONFIG_DELTA", "THEORY_PROFILE", "PROVENANCE",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iter_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        parts = path.relative_to(root).parts
        if ".git" in parts or "__pycache__" in parts:
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        out.append(path)
    return sorted(out, key=lambda p: p.relative_to(root).as_posix())


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--profile", default=str(ROOT / "gsl" / "REPO_PROFILE.json"))
    p.add_argument("--output", default="/tmp/garden-repo-gsl-audit.json")
    p.add_argument("--strict-frontier", action="store_true")
    args = p.parse_args()

    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    if profile.get("schema") != "GardenRepoConformanceProfile/v1":
        raise SystemExit("unsupported GardenRepoConformanceProfile schema")
    if profile.get("semantic_compliance_proved") is not False:
        raise SystemExit("classification profile cannot self-claim semantic compliance")

    rules = profile.get("rules") or []
    ids = [str(r.get("rule_id")) for r in rules]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate repo-profile rule id")

    profile_errors: list[str] = []
    for rule in rules:
        modules = list(rule.get("required_change_modules") or []) + list(rule.get("conditional_change_modules") or [])
        unknown = sorted(set(modules) - ALLOWED_MODULES)
        if unknown:
            profile_errors.append(f"{rule.get('rule_id')}: unknown Garden modules {unknown}")

    artifacts: list[dict[str, Any]] = []
    frontier: list[str] = []
    for path in iter_files(ROOT):
        rel = path.relative_to(ROOT).as_posix()
        matches = [r for r in rules if fnmatchcase(rel, str(r.get("pattern", "")))]
        if not matches:
            frontier.append(rel)
            artifacts.append({"path": rel, "sha256": sha256(path), "coverage_state": "FRONTIER", "rule_id": None})
            continue
        selected = matches[0]
        coverage = str(selected.get("coverage_state", "DECLARED"))
        if coverage == "FRONTIER":
            frontier.append(rel)
        artifacts.append({
            "path": rel,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "artifact_class": selected.get("artifact_class"),
            "coverage_state": coverage,
            "rule_id": selected.get("rule_id"),
            "required_change_modules": selected.get("required_change_modules") or [],
            "conditional_change_modules": selected.get("conditional_change_modules") or [],
            "shadowed_rule_ids": [str(r.get("rule_id")) for r in matches[1:]],
        })

    report = {
        "schema": "GardenRepoConformanceReport/v1",
        "profile_id": profile.get("profile_id"),
        "design_epoch_ref": profile.get("design_epoch_ref"),
        "artifact_count": len(artifacts),
        "explicit_artifact_count": len(artifacts) - len(frontier),
        "frontier_artifact_count": len(frontier),
        "frontier_paths": frontier,
        "profile_errors": profile_errors,
        "semantic_compliance_proved": False,
        "artifacts": artifacts,
        "boundary": "Full classification is necessary but not sufficient for semantic Garden/GSL conformance.",
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "artifact_count": len(artifacts),
        "frontier_artifact_count": len(frontier),
        "profile_error_count": len(profile_errors),
        "output": str(out),
    }, sort_keys=True))
    if profile_errors:
        return 2
    if args.strict_frontier and frontier:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
