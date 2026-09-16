"""Secret-free continuation for the independent-branch OpenRouter worker.

Main-branch changes can require a new ChatGPT baseline, but never create inference
work by themselves. Only a staged external ChatGPT directive may begin a phase.
Within BLIND, FINAL or CONFIRM phases, recorded results may dispatch the next
isolated family because every reviewer in that phase receives the same packet.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time

from tools import independent_branch_protocol as protocol
from tools import single_review_worker as legacy

WORKER = "single-openrouter-review.yml"
DISPATCHER = "continue-openrouter-review.yml"


def _digest_files(root: Path, paths: list[str]) -> str:
    rows = []
    for rel in paths:
        path = root / rel
        rows.append([rel, hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "MISSING"])
    return protocol.sha256_value(rows)


def host_check() -> str:
    if os.environ.get("GITHUB_REPOSITORY") != legacy.REPO or os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise ValueError("untrusted continuation host")
    ref = os.environ.get("GITHUB_WORKFLOW_REF")
    event = os.environ.get("GITHUB_EVENT_NAME")
    worker_ref = legacy.REPO + "/.github/workflows/" + WORKER + "@refs/heads/main"
    dispatcher_ref = legacy.REPO + "/.github/workflows/" + DISPATCHER + "@refs/heads/main"
    if ref == worker_ref and event == "workflow_dispatch":
        return "completion"
    if ref == dispatcher_ref and event in ("push", "schedule", "workflow_dispatch"):
        return event
    raise ValueError("unregistered continuation host")


def dispatch(root: Path = Path(".")) -> None:
    event = host_check()
    token = os.environ["GH_REVIEW_TOKEN"]
    ledger = legacy.GitLedger(token)
    state = ledger.value
    if state.get("paused") is not False or state.get("scope") != "PUBLIC_MATRIX_REVIEW_ONLY":
        print("PAUSED; no model call or dispatch")
        return

    executor_revision = _digest_files(root, [
        "tools/context_capsule.py",
        "tools/independent_branch_worker.py",
        "tools/review_context.py",
        "tools/review_budget.py",
        "agents/review-context-policy.json",
        "SOURCE_MANIFEST.json",
        "tools/independent_branch_protocol.py",
        "tools/independent_branch_continuation.py",
        "agents/garden-architecture-context-capsule-policy.json",
        "agents/independent-branch-convergence-policy.json",
        "agents/event-driven-context-policy.json",
        "agents/openrouter-paid-review-policy.json",
        "agents/provider-exclusion-policy.json",
        "agents/design-review-matrix.json",
    ])
    current_commit = os.environ.get("GITHUB_SHA")
    continuation = state.get("continuation") or {}

    if event == "push" and (state.get("admitted_source_commit") != current_commit or state.get("executor_revision_v3") != executor_revision):
        state["admitted_source_commit"] = current_commit
        state["executor_revision_v3"] = executor_revision
        state["continuation"] = {
            "status": "AWAITING_CHATGPT_BASELINE_OR_DIRECTIVE",
            "reason": "NEW_SOURCE_OR_PROTOCOL_BINDING",
            "updated": time.time(),
        }
        ledger.save(state)
        print("New material binding requires private ChatGPT baseline and source-bound Garden context capsule before OpenRouter inference")
        return

    status = continuation.get("status")
    if status == "DEFERRED_DAILY" and time.time() < float(continuation.get("resume_after", 0)):
        return
    if status == 'DISPATCHED':
        if event != 'schedule' or time.time() - float(continuation.get('updated', 0)) < 3600:
            return
    if status not in ("READY", "DEFERRED_DAILY", "DISPATCHED"):
        print("Queue state: " + str(status) + "; no automatic dispatch")
        return
    if any(row.get("status") in ("RESERVED", "UNKNOWN") for row in state.get("attempts", [])):
        print("Outstanding call requires worker reconciliation; no continuation dispatch")
        return

    attempts = int(continuation.get("dispatch_attempts", 0))
    if attempts >= 2:
        state["continuation"] = {
            "status": "BLOCKED",
            "reason": "DISPATCH_DELIVERY_UNCONFIRMED",
            "updated": time.time(),
        }
        ledger.save(state)
        return
    state["continuation"] = {
        **continuation,
        "status": "DISPATCHED",
        "dispatch_attempts": attempts + 1,
        "updated": time.time(),
    }
    ledger.save(state)
    legacy.http(legacy.API + "/actions/workflows/" + WORKER + "/dispatches", token, {"ref": "main"})
    print("Next isolated reviewer dispatched")


if __name__ == "__main__":
    try:
        dispatch()
    except Exception as exc:
        print("INDEPENDENT_BRANCH_CONTINUATION_STOPPED: " + type(exc).__name__ + "; no inference was made by dispatcher")
        raise SystemExit(2)
