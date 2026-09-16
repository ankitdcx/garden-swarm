#!/usr/bin/env python3
"""Render and verify Garden Git operating-context views from one structured source."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SOURCE = Path("GIT_OPERATING_CONTEXT_SOURCE.json")
MACHINE = Path("GIT_OPERATING_CONTEXT.json")
HUMAN = Path("GIT_OPERATING_CONTEXT.md")
SCHEMA = "GardenGitOperatingContextSource/v2"


def canonical_source(path: Path = SOURCE):
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"expected {SCHEMA}")
    revision = data.get("document_revision")
    if not isinstance(revision, int) or revision < 1:
        raise ValueError("document_revision must be a positive integer")
    return data, hashlib.sha256(raw).hexdigest()


def machine_view(data: dict, source_sha256: str) -> dict:
    return {
        "schema": "GardenGitOperatingContext/v2",
        "document_revision": data["document_revision"],
        "revision_id": data["revision_id"],
        "source_sha256": source_sha256,
        "normative_source": data["authority"]["normative_source"],
        "live_github_rules_override_snapshot": data["authority"]["live_github_rules_override_snapshot"],
        "loading_order": data["loading_order"],
        "process_binding": data["process_binding"],
        "repositories": data["repository_snapshots"],
        "preflight": data["preflight"],
        "workstreams": data["workstreams"],
        "reviewer_quality": data["reviewer_quality"],
        "recovery": data["recovery"],
        "secret_scanning": data["secret_scanning"],
        "branch_cleanup": data["branch_cleanup"],
        "github_field_notes": data["github_field_notes"],
        "request_efficiency": data["request_efficiency"],
        "boundaries": data["boundaries"],
        "failure_catalogue_count": len(data["failure_catalogue"]),
    }


def _bullets(values, indent=""):
    return "\n".join(f"{indent}- {v}" for v in values)


def human_view(data: dict, source_sha256: str) -> str:
    a = data["authority"]; p = data["preflight"]; ws = data["workstreams"]; rq = data["reviewer_quality"]; recovery = data["recovery"]["bad_merge"]
    lines = [
        f"# Garden Git Operating Context — revision {data['document_revision']}", "",
        f"**Revision ID:** `{data['revision_id']}`  ", f"**Source SHA-256:** `{source_sha256}`  ",
        f"**Normative source:** `{a['normative_source']}`  ", f"**Status:** {data['status']}", "",
        "> This Markdown is generated. Do not edit it by hand. Edit `GIT_OPERATING_CONTEXT_SOURCE.json` and regenerate.", "",
        "Live GitHub rules and current repository heads override stale snapshot values in this document.", "",
        "## 1. Mandatory loading order", "", _bullets(data["loading_order"]), "",
        "The Git operating context is loaded first for mutation mechanics, but the current Garden process pointer and the process file it names must be loaded before routing semantic/design work.", "", "## 2. Repository snapshots", "",
    ]
    for repo, meta in data["repository_snapshots"].items():
        lines += [f"### `{repo}`", ""]
        for k, v in meta.items(): lines.append(f"- **{k}:** `{v}`" if not isinstance(v, list) else f"- **{k}:** {', '.join(f'`{x}`' for x in v)}")
        lines.append("")
    lines += [
        "## 3. Preflight receipt", "", f"Future ChatGPT workstreams require `{p['schema']}` before substantial editing.",
        "The only allowed pre-receipt mutation is the small intent-only bootstrap commit needed to create the draft PR.",
        "The receipt proves bounded preflight facts and acknowledgement; it does not prove private cognition or that a model literally 'read' a file.", "", "**Required fields:**", "", _bullets(p["required_fields"]), "",
        f"ChatGPT work branches use `{p['branch_prefixes']['chatgpt']}`; integration branches use `{p['branch_prefixes']['integration']}`.", "",
        "## 4. Parallel ChatGPT workstreams and merge train", "", f"Workstream unit: **{ws['unit']}**.", "", "**Statuses:** " + ", ".join(f"`{x}`" for x in ws["statuses"]), "",
        f"- Stale draft: {ws['stale_draft_after_hours_without_activity']} hours without activity.", f"- Abandoned-review threshold: {ws['abandoned_review_after_days_without_activity']} days without activity.",
        "- Time thresholds are evaluated only on a new event or maintenance scan; no polling loop is created.", "- Stale/abandoned work is never auto-deleted.", "", "**Merge train:**", "",
        f"- Driver: `{ws['merge_train']['driver']}`.", f"- Scheduling: `{ws['merge_train']['scheduling']}`.", f"- Order: `{ws['merge_train']['default_order']}`.", _bullets(ws["merge_train"]["entry_conditions"]),
        f"- Dependency invalidation moves affected work to `{ws['merge_train']['dependency_invalidation']}`.", f"- Exit: `{ws['merge_train']['exit_condition']}`.", "- Final admission to `main` is serial.", "",
        "## 5. Reviewer-quality lifecycle", "", f"Normative metric/threshold definition: `{rq['normative_metric_file']}`.", "This document intentionally does not duplicate those weights as authority; the referenced policy is normative.", "",
        "**Recovery:**", "", f"- DEGRADED → ACTIVE: {rq['recovery']['DEGRADED_to_ACTIVE']}.", f"- QUARANTINED → ACTIVE: {rq['recovery']['QUARANTINED_to_ACTIVE']}.", "- No direct state jump back to ACTIVE.", "",
        "**If a required reviewer becomes non-ACTIVE while a task is in flight:**", "", f"- Default: `{rq['inflight_non_active_slot']['default']}`.", "- No silent model swap.", "- The same exact model may resume only after governed return to ACTIVE and a fresh source-binding check.", "- A replacement model starts a new convergence cycle.", "",
        "**Quality queue retention/backpressure:**", "", f"- Soft pending limit: {rq['queue_retention']['pending_soft_limit']}.", f"- Hard pending limit: {rq['queue_retention']['pending_hard_limit']}.", f"- Overdue after: {rq['queue_retention']['overdue_after_hours']} hours.", f"- Closed archive hash limit: {rq['queue_retention']['closed_archive_hash_limit']}.", "- Unadjudicated items are never silently deleted.", "- Crossing the hard limit blocks new convergence admission until quality debt is reduced.", "",
        "## 6. Bad-merge recovery", "", "A bad merge is recovered without rewriting protected history.", "", _bullets(recovery["required_path"]), "", "- `main` must never be reset or force-pushed as rollback.", f"- Prefer a revert when: {recovery['revert_preferred_when']}.", f"- Prefer a forward fix when: {recovery['forward_fix_preferred_when']}.", "",
        "## 7. Secret scanning", "", "- Central CI scanning is mandatory; local hooks are optional and not authoritative.", "- Scan changed text files for high-confidence credential patterns.", "- Allowlisting requires exact rule + exact path + reason.", "- Fake fixtures may be allowlisted; real credentials may not.", "",
        "## 8. Branch cleanup", "", "- A merged branch may be deleted only after `MERGED_DELETE_ELIGIBLE` classification.", "- `garden-review-state` is never auto-deleted.", "- Stale or abandoned workstreams are never auto-deleted.", "- Cleanup is event-driven and requires a cleanup receipt.", "",
        "## 9. GitHub ruleset field note", "", data["github_field_notes"]["extra_approval_for_unattributed_changes"], "", "## 10. Request efficiency", "", _bullets(data["request_efficiency"]), "", "## 11. Failure catalogue", "",
    ]
    for row in data["failure_catalogue"]: lines += [f"### {row['id']}. {row['name']}", "", f"**Rule:** {row['rule']}", ""]
    lines += ["## 12. Boundaries", "", "- This is an operational Git/process source, not canonical Garden semantics.", "- Receipts are evidence, not Proof, authority, human approval, or promotion.", "- Request efficiency never weakens correctness, assurance, authority, privacy, safety, or process gates.", "", "## 13. Source-of-truth rule", "", f"`{a['normative_source']}` is authoritative. `GIT_OPERATING_CONTEXT.md` and `GIT_OPERATING_CONTEXT.json` are generated views.", "The `garden-swarm` source copy is an exact pinned mirror and must match the authoritative source SHA-256 for the same revision.", "For ChatGPT Project Sources, use the generated Markdown view rather than maintaining a separate manually edited copy.", ""]
    return "\n".join(lines)


def render(source: Path = SOURCE):
    data, sha = canonical_source(source)
    return json.dumps(machine_view(data, sha), indent=2, sort_keys=True) + "\n", human_view(data, sha)


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--check", action="store_true"); args = parser.parse_args(); machine, human = render()
    if args.check:
        failures = []
        if not MACHINE.exists() or MACHINE.read_text(encoding="utf-8") != machine: failures.append(str(MACHINE))
        if not HUMAN.exists() or HUMAN.read_text(encoding="utf-8") != human: failures.append(str(HUMAN))
        if failures: raise SystemExit("generated Git operating-context drift: " + ", ".join(failures))
        print("Git operating-context generated views match source"); return 0
    MACHINE.write_text(machine, encoding="utf-8"); HUMAN.write_text(human, encoding="utf-8"); print("Rendered Git operating-context views"); return 0

if __name__ == "__main__": raise SystemExit(main())
