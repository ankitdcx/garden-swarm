#!/usr/bin/env python3
"""Validate Garden ChatGPT workstream preflight receipts on pull-request events.

This gate proves only that required preflight facts were declared and bound to the
PR base. It cannot prove a model's private cognitive state or that it literally
"read" a document.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

WORKSTREAM_MARKER = "<!-- GARDEN_CHATGPT_WORKSTREAM -->"
PREFLIGHT_MARKER = "<!-- GARDEN_GIT_PREFLIGHT_RECEIPT -->"
SOURCE = Path("GIT_OPERATING_CONTEXT_SOURCE.json")


def _block(body: str | None, marker: str) -> dict[str, Any] | None:
    if not body or marker not in body:
        return None
    tail = body.split(marker, 1)[1]
    m = re.search(r"```(?:json)?\s*\n(.*?)\n```", tail, flags=re.DOTALL | re.IGNORECASE)
    if not m:
        raise ValueError(f"{marker} must be followed by fenced JSON")
    value = json.loads(m.group(1))
    if not isinstance(value, dict):
        raise ValueError(f"{marker} must contain an object")
    return value


def _sha40(value: Any) -> str:
    text = str(value or "").lower()
    if not re.fullmatch(r"[0-9a-f]{40}", text):
        raise ValueError("expected full git sha")
    return text


def validate_event(event: dict[str, Any], source: dict[str, Any], source_sha256: str | None = None) -> dict[str, Any]:
    pr = event.get("pull_request")
    if not pr:
        return {"schema": "GardenGitPreflightGate/v1", "status": "SKIP_NON_PR"}
    head = str(pr["head"]["ref"])
    base = _sha40(pr["base"]["sha"])
    body = pr.get("body") or ""
    chatgpt_prefix = source["preflight"]["branch_prefixes"]["chatgpt"]
    integration_prefix = source["preflight"]["branch_prefixes"]["integration"]
    if not (head.startswith(chatgpt_prefix) or head.startswith(integration_prefix)):
        return {"schema": "GardenGitPreflightGate/v1", "status": "LEGACY_OR_NON_CHATGPT_BRANCH_NOT_IN_V2_SCOPE"}

    ws = _block(body, WORKSTREAM_MARKER)
    receipt = _block(body, PREFLIGHT_MARKER)
    failures: list[str] = []
    if ws is None:
        failures.append("MISSING_CHATGPT_WORKSTREAM_INTENT")
    if receipt is None:
        failures.append("MISSING_GIT_PREFLIGHT_RECEIPT")
    if failures:
        return {"schema": "GardenGitPreflightGate/v1", "status": "BLOCKED", "failures": failures}

    if ws.get("schema") != "GardenChatGPTWorkstreamIntent/v1":
        failures.append("INVALID_WORKSTREAM_SCHEMA")
    if ws.get("branch") != head:
        failures.append("WORKSTREAM_BRANCH_MISMATCH")
    if str(ws.get("base_sha", "")).lower() != base:
        failures.append("WORKSTREAM_BASE_MISMATCH")
    if ws.get("draft_pr_created_before_substantial_edit") is not True:
        failures.append("DRAFT_PR_NOT_DECLARED_BEFORE_SUBSTANTIAL_EDIT")
    if head.startswith(integration_prefix) and ws.get("status") != "INTEGRATING":
        failures.append("INTEGRATION_BRANCH_REQUIRES_INTEGRATING_STATUS")
    if head.startswith(chatgpt_prefix) and ws.get("status") not in {"ACTIVE", "REVALIDATE_REQUIRED"}:
        failures.append("CHATGPT_BRANCH_NOT_ACTIVE_OR_REVALIDATING")

    if receipt.get("schema") != source["preflight"]["schema"]:
        failures.append("INVALID_PREFLIGHT_SCHEMA")
    repo = str(event.get("repository", {}).get("full_name") or os.environ.get("GITHUB_REPOSITORY") or "")
    for field in source["preflight"]["required_fields"]:
        if field == "git_context_source_sha256" and int(receipt.get("git_context_revision", 0) or 0) == 1:
            if not receipt.get("git_context_blob_sha"):
                failures.append("MISSING_LEGACY_CONTEXT_BINDING")
            continue
        if field not in receipt:
            failures.append("MISSING_PREFLIGHT_FIELD:" + field)
    if receipt.get("repository") != repo:
        failures.append("PREFLIGHT_REPOSITORY_MISMATCH")
    if str(receipt.get("base_sha", "")).lower() != base:
        failures.append("PREFLIGHT_BASE_MISMATCH")
    revision = int(receipt.get("git_context_revision", 0) or 0)
    if revision < 1 or revision > int(source["document_revision"]):
        failures.append("PREFLIGHT_CONTEXT_REVISION_INVALID")
    if revision >= 2:
        if source_sha256 is None or receipt.get("git_context_source_sha256") != source_sha256:
            failures.append("PREFLIGHT_CONTEXT_SOURCE_HASH_MISMATCH")
    if receipt.get("process_version") != source["process_binding"]["expected_version_at_revision"]:
        failures.append("PREFLIGHT_PROCESS_VERSION_MISMATCH")
    repo_rules = source["repository_snapshots"].get(repo) or {}
    if receipt.get("verified_merge_ruleset_id") != repo_rules.get("verified_merge_ruleset_id"):
        failures.append("PREFLIGHT_RULESET_MISMATCH")
    if receipt.get("overlap_result") not in source["preflight"]["allowed_overlap_results"]:
        failures.append("PREFLIGHT_OVERLAP_RESULT_INVALID")
    if receipt.get("created_before_substantial_edit") is not True:
        failures.append("PREFLIGHT_NOT_CREATED_BEFORE_SUBSTANTIAL_EDIT")
    if receipt.get("authority_effect") != "NONE":
        failures.append("PREFLIGHT_MAY_NOT_CLAIM_AUTHORITY")

    return {
        "schema": "GardenGitPreflightGate/v1",
        "status": "BLOCKED" if failures else "PASS",
        "repository": repo,
        "head": head,
        "base_sha": base,
        "document_revision": source["document_revision"],
        "failures": failures,
        "boundary": "Preflight receipt is auditable acknowledgement evidence, not proof of cognition, authority or semantic correctness.",
    }


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise SystemExit("GITHUB_EVENT_PATH required")
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    raw = SOURCE.read_bytes()
    source = json.loads(raw.decode("utf-8"))
    result = validate_event(event, source, hashlib.sha256(raw).hexdigest())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] != "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
