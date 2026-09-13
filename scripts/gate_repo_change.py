#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_BASE = "d42f31b426a75fa90ddce561ae4a1c44418efb11"
BOOTSTRAP_APPROVAL = "HUMAN-APPROVAL-GSL-FULL-COMPLIANCE-2026-09-13"
EXCLUDED_CHANGE_PREFIXES = ("gsl/changes/", "gsl/receipts/")
MATERIAL_CLASSES = {"CANONICAL_SOURCE", "WORKFLOW", "IMPLEMENTATION", "TOOLING", "CONFIGURATION", "RECEIPT_OR_CONFIG", "DATA_OR_CONFIG"}


def run(*args: str) -> str:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=True).stdout


def git_json(ref: str, path: str) -> dict[str, Any]:
    return json.loads(run("git", "show", f"{ref}:{path}"))


def git_path_exists(ref: str, path: str) -> bool:
    proc = subprocess.run(["git", "cat-file", "-e", f"{ref}:{path}"], cwd=ROOT, text=True, capture_output=True)
    return proc.returncode == 0


def head_json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def protected_json(base: str, canonical_path: str, legacy_flat_path: str | None = None) -> dict[str, Any]:
    """Resolve governance only from the protected base.

    During the one-time flat->nested namespace migration, a protected base may
    still contain the legacy flat path. That is a safe compatibility source
    because it is read from BASE, never from the proposed head.
    """
    if git_path_exists(base, canonical_path):
        return git_json(base, canonical_path)
    if legacy_flat_path and git_path_exists(base, legacy_flat_path):
        return git_json(base, legacy_flat_path)
    raise RuntimeError(f"protected-base governance artifact missing: {canonical_path}")


def changed_rows(base: str, head: str) -> list[dict[str, str]]:
    text = run("git", "diff", "--name-status", base, head)
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        rows.append({"status": parts[0], "path": parts[-1]})
    return rows


def change_content_root(base: str, head: str, rows: list[dict[str, str]]) -> str:
    material = []
    for row in rows:
        path = row["path"]
        if path.startswith(EXCLUDED_CHANGE_PREFIXES):
            continue
        object_id = "DELETED" if row["status"].startswith("D") else run("git", "rev-parse", f"{head}:{path}").strip()
        material.append({"path": path, "status": row["status"], "object": object_id})
    payload = json.dumps(sorted(material, key=lambda x: x["path"]), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_envelope(rows: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
    candidates = sorted(
        row["path"] for row in rows
        if row["path"].startswith("gsl/changes/") and row["path"].endswith(".json")
    )
    if len(candidates) != 1:
        raise ValueError(f"exactly one changed gsl/changes/*.json envelope required, found {candidates}")
    return candidates[0], head_json(candidates[0])


def load_protected_profile_rules(base: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    if git_path_exists(base, "gsl/profile/REPO_PROFILE.json"):
        profile = git_json(base, "gsl/profile/REPO_PROFILE.json")
        tree = run("git", "ls-tree", "-r", "--name-only", base, "gsl/profile").splitlines()
        shard_paths = sorted(
            path for path in tree
            if Path(path).name.startswith("REPO_PROFILE_") and path.endswith(".json")
        )
        rules: list[dict[str, Any]] = []
        for path in shard_paths:
            shard = git_json(base, path)
            if shard.get("schema") != "GardenRepoConformanceProfileShard/v1":
                raise RuntimeError(f"invalid protected-base profile shard: {path}")
            if shard.get("design_epoch_ref") != profile.get("design_epoch_ref"):
                raise RuntimeError(f"stale protected-base profile shard: {path}")
            rules.extend(shard.get("rules") or [])
        rules.extend(profile.get("rules") or [])
        return profile, rules, shard_paths
    if git_path_exists(base, "gsl/REPO_PROFILE.json"):
        profile = git_json(base, "gsl/REPO_PROFILE.json")
        return profile, list(profile.get("rules") or []), []
    raise RuntimeError("protected-base repository profile missing")


def classified_rule(path: str, rules: list[dict[str, Any]]) -> dict[str, Any] | None:
    for rule in rules:
        if fnmatch.fnmatchcase(path, str(rule.get("pattern", ""))):
            return rule
    return None


def approval_by_id(payload: dict[str, Any], approval_id: str | None) -> dict[str, Any] | None:
    if not approval_id:
        return None
    return next((x for x in payload.get("approvals") or [] if x.get("approval_id") == approval_id), None)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-sha", required=True)
    p.add_argument("--head-sha", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    failures: list[str] = []
    base, head = args.base_sha, args.head_sha
    rows = changed_rows(base, head)
    observed_paths = sorted(row["path"] for row in rows if not row["path"].startswith(EXCLUDED_CHANGE_PREFIXES))
    content_root = change_content_root(base, head, rows)

    try:
        envelope_path, envelope = load_envelope(rows)
    except Exception as exc:
        envelope_path, envelope = "<missing>", {}
        failures.append(f"CHANGE_ENVELOPE_INVALID:{exc}")

    base_policy = protected_json(base, "gsl/policy/CHANGE_POLICY.json", "gsl/CHANGE_POLICY.json")
    base_authority = protected_json(base, "gsl/envelopes/AUTHORITY_REGISTRY.json", "gsl/AUTHORITY_REGISTRY.json")
    base_profile, profile_rules, profile_shards = load_protected_profile_rules(base)
    obligations = protected_json(base, "gsl/profile/SOURCE_OBLIGATIONS.json", "gsl/SOURCE_OBLIGATIONS.json")
    approvals = protected_json(base, "gsl/policy/HUMAN_APPROVALS.json", "gsl/HUMAN_APPROVALS.json")

    if envelope.get("schema") != "RepoChangeEnvelope/v1":
        failures.append("CHANGE_ENVELOPE_SCHEMA_INVALID")
    if envelope.get("repository") != "ankitdcx/garden-swarm":
        failures.append("CHANGE_ENVELOPE_REPOSITORY_MISMATCH")
    if envelope.get("base_commit") != base:
        failures.append("CHANGE_ENVELOPE_BASE_MISMATCH")
    if envelope.get("design_epoch_ref") != base_policy.get("design_epoch_ref"):
        failures.append("CHANGE_ENVELOPE_DESIGN_EPOCH_MISMATCH")
    if sorted(envelope.get("changed_paths") or []) != observed_paths:
        failures.append("CHANGE_ENVELOPE_PATH_SET_MISMATCH")
    if envelope.get("change_content_root") != content_root:
        failures.append(f"CHANGE_CONTENT_ROOT_MISMATCH:observed={content_root}")

    constitutional_paths = set(base_policy.get("constitutional_paths") or [])
    touched_constitutional = sorted(path for path in observed_paths if path in constitutional_paths)
    derived_tier = "CONSTITUTIONAL" if touched_constitutional else "ORDINARY"
    if envelope.get("governance_tier") != derived_tier:
        failures.append(f"GOVERNANCE_TIER_MISMATCH:derived={derived_tier}")

    authority_ref = envelope.get("authority_ref")
    grant = next((x for x in base_authority.get("grants") or [] if x.get("authority_id") == authority_ref), None)
    if grant is None:
        failures.append("AUTHORITY_REF_NOT_IN_PROTECTED_BASE")
    elif "PROPOSE" not in (grant.get("actions") or []):
        failures.append("AUTHORITY_REF_LACKS_PROPOSE")

    approval = approval_by_id(approvals, envelope.get("human_approval_ref"))
    if derived_tier == "CONSTITUTIONAL":
        if approval is None:
            failures.append("CONSTITUTIONAL_CHANGE_REQUIRES_TRUSTED_HUMAN_APPROVAL")
        else:
            if approval.get("canonical_promotion_authorized") is not False:
                failures.append("HUMAN_APPROVAL_MUST_NOT_GRANT_CANONICAL_PROMOTION")
            if base == BOOTSTRAP_BASE and approval.get("approval_id") != BOOTSTRAP_APPROVAL:
                failures.append("BOOTSTRAP_APPROVAL_ID_MISMATCH")
            if base == BOOTSTRAP_BASE and approval.get("base_commit") != BOOTSTRAP_BASE:
                failures.append("BOOTSTRAP_APPROVAL_BASE_MISMATCH")

    obligation_ids = {x.get("obligation_id") for x in obligations.get("obligations") or []}
    supplied_obligations = set(envelope.get("source_obligation_refs") or [])
    unknown_obligations = sorted(supplied_obligations - obligation_ids)
    if unknown_obligations:
        failures.append("UNKNOWN_SOURCE_OBLIGATIONS:" + ",".join(unknown_obligations))

    required_modules: set[str] = set()
    material_change = False
    profile_rows = []
    for path in observed_paths:
        rule = classified_rule(path, profile_rules)
        if rule is None:
            failures.append(f"UNCLASSIFIED_CHANGED_PATH:{path}")
            continue
        profile_rows.append({"path": path, "rule_id": rule.get("rule_id"), "artifact_class": rule.get("artifact_class")})
        required_modules.update(rule.get("required_change_modules") or [])
        if rule.get("artifact_class") in MATERIAL_CLASSES:
            material_change = True
    dispositions = envelope.get("module_dispositions") or {}
    missing_modules = sorted(m for m in required_modules if (dispositions.get(m) or {}).get("status") != "APPLIED")
    if missing_modules:
        failures.append("REQUIRED_MODULES_NOT_APPLIED:" + ",".join(missing_modules))
    if material_change and not supplied_obligations:
        failures.append("MATERIAL_CHANGE_REQUIRES_SOURCE_OBLIGATION")

    compare = envelope.get("compare") or {}
    reason = envelope.get("reason") or {}
    if material_change:
        if not compare.get("do_nothing") or not compare.get("proposed") or not compare.get("selection"):
            failures.append("MATERIAL_CHANGE_REQUIRES_COMPARE_AND_DO_NOTHING")
        if not reason.get("rationale") or not reason.get("uncertainty") or not reason.get("what_would_overturn"):
            failures.append("MATERIAL_CHANGE_REQUIRES_TYPED_REASON")
        if not envelope.get("evidence_refs") or not envelope.get("proof_or_test_refs"):
            failures.append("MATERIAL_CHANGE_REQUIRES_EVIDENCE_AND_TEST_REFS")

    expected_assurance = "A3_CONSTITUTIONAL" if derived_tier == "CONSTITUTIONAL" else ("A2_MATERIAL" if material_change else "A1_LIGHT")
    if envelope.get("assurance_tier") != expected_assurance:
        failures.append(f"AAP_ASSURANCE_TIER_MISMATCH:expected={expected_assurance}")

    reviews = envelope.get("exact_review_bindings") or []
    for review in reviews:
        if review.get("schema") != "ExactReviewBinding/v1" or review.get("target_content_root") != content_root:
            failures.append("EXACT_REVIEW_BINDING_STALE_OR_MALFORMED")
    development_mode = envelope.get("development_mode")
    if development_mode in {"AI_ASSISTED", "AUTONOMOUS_AGENT"} and not reviews:
        failures.append("AI_ASSISTED_CHANGE_REQUIRES_EXACT_REVIEW_BINDING")

    independence = envelope.get("ai_independence_assessment") or {}
    if independence.get("schema") != "AIIndependenceAssessment/v1":
        failures.append("AI_INDEPENDENCE_ASSESSMENT_MISSING")
    elif derived_tier == "CONSTITUTIONAL" and approval is None and int(independence.get("independent_clusters", 0)) < 2:
        failures.append("CONSTITUTIONAL_AI_CHANGE_REQUIRES_INDEPENDENCE_OR_HUMAN_APPROVAL")

    projection = {
        "schema": "MachineProjectionReceipt/v1",
        "projection_id": f"MPR-{content_root[:16]}",
        "target_content_root": content_root,
        "observed_changed_paths": observed_paths,
        "function_contract_resolution": "DEFER_TO_CI_CONFORMANCE_PIPELINE",
        "source_obligation_resolution": sorted(supplied_obligations),
        "governance_tier": derived_tier,
        "protected_profile_shards": profile_shards,
        "required_modules": sorted(required_modules),
        "result": "PASS" if not failures else "FAIL",
    }
    receipt = {
        "schema": "RepoChangeGateReceipt/v1",
        "repository": "ankitdcx/garden-swarm",
        "base_commit": base,
        "head_commit": head,
        "change_envelope": envelope_path,
        "change_content_root": content_root,
        "governance_tier": derived_tier,
        "constitutional_paths_touched": touched_constitutional,
        "profile_resolution": profile_rows,
        "machine_projection": projection,
        "decision": "ALLOW" if not failures else "REJECT",
        "failures": failures,
        "canonical_promotion_authorized": False,
        "boundary": "ALLOW is scoped repository-change admission evidence only; it is not canonical Garden promotion or global semantic certification."
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"decision": receipt["decision"], "change_content_root": content_root, "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
