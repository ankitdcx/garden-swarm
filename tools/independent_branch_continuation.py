"""Secret-free continuation for the independent-branch OpenRouter worker.

Main-branch changes can require a new ChatGPT baseline, but never create inference
work by themselves. Only a staged external ChatGPT directive may begin a phase.
Within BLIND, FINAL or CONFIRM phases, recorded results may dispatch the next
isolated family because every reviewer in that phase receives the same packet.
Recorded reviews are also queued for external ChatGPT quality adjudication in the
same durable-state transaction used by continuation.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time

from tools import independent_branch_protocol as protocol
from tools import reviewer_quality_runtime
from tools import single_review_worker as legacy
from tools import review_campaign

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


def _save_if_quality_changed(ledger: legacy.GitLedger, state: dict, quality_added: int) -> None:
    if quality_added:
        ledger.save(state)


def admitted_campaign_start(root: Path, token: str) -> dict | None:
    """A push may start only an explicitly staged, fully bound BLIND directive."""
    if review_campaign.load_campaign(root) is None:
        return None
    from tools import independent_branch_worker as worker
    directive = worker.load_directive(token)
    if not directive or directive.get('start_on_matching_source_event') is not True:
        return None
    if directive.get('phase') != 'BLIND':
        raise ValueError('source-event campaign launch must be BLIND')
    _, target, _, trace, packet_hash, _, _ = worker._target_by_id(root, directive['target_id'], directive)
    campaign = review_campaign.bind_campaign(directive, trace['source_sha256'], root)
    if campaign is None:
        raise ValueError('source-event launch requires an authorized campaign')
    policy = json.loads((root / 'agents/openrouter-paid-review-policy.json').read_text())
    protocol.validate_directive(directive, families=worker._families(policy),
                                target_id=target['target_id'], source_packet_sha256=packet_hash)
    if directive['private_baseline_commitment']['neutral_query_sha256'] != protocol.sha256_text(protocol.neutral_query(target)):
        raise ValueError('campaign baseline query mismatch')
    return {'status': 'READY', 'campaign_id': campaign['campaign_id'],
            'target_id': target['target_id'], 'source_packet_sha256': packet_hash,
            'reason': 'EXPLICIT_SOURCE_BOUND_CAMPAIGN_DIRECTIVE'}


def dispatch(root: Path = Path(".")) -> None:
    event = host_check()
    token = os.environ["GH_REVIEW_TOKEN"]
    ledger = legacy.GitLedger(token)
    state = ledger.value
    if state.get("paused") is not False or state.get("scope") != "PUBLIC_MATRIX_REVIEW_ONLY":
        print("PAUSED; no model call or dispatch")
        return

    registry = reviewer_quality_runtime.load_registry(root)
    quality_added = reviewer_quality_runtime.queue_pending_assessments(state, registry, limit=20)

    executor_revision = _digest_files(root, [
        "tools/context_capsule.py",
        "tools/independent_branch_worker.py",
        "tools/single_review_worker.py",
        "tools/review_context.py",
        "tools/review_budget.py",
        "tools/review_campaign.py",
        "agents/v159-review-campaign.json",
        "tools/reviewer_quality_runtime.py",
        "agents/review-context-policy.json",
        "SOURCE_MANIFEST.json",
        "tools/independent_branch_protocol.py",
        "tools/independent_branch_continuation.py",
        "agents/garden-architecture-context-capsule-policy.json",
        "agents/independent-branch-convergence-policy.json",
        "agents/event-driven-context-policy.json",
        "agents/openrouter-paid-review-policy.json",
        "agents/reviewer-quality-policy.json",
        "agents/reviewer-slot-registry.json",
        "agents/provider-exclusion-policy.json",
        "agents/design-review-matrix.json",
    ])
    current_commit = os.environ.get("GITHUB_SHA")
    continuation = state.get("continuation") or {}

    outstanding = review_campaign.blocking_attempts(state, review_campaign.load_campaign(root))
    if outstanding:
        state["continuation"] = {
            "status": "BLOCKED_UNRESOLVED_CALL",
            "reason": "GENERATION_OR_BILLING_EVIDENCE_REQUIRED",
            "attempts": [{k: a.get(k) for k in ("run_id", "model", "status", "response_id", "started")}
                         for a in outstanding],
            "updated": time.time(),
        }
        ledger.save(state)
        print("Outstanding call requires reconciliation; no continuation dispatch")
        return

    if state.get("admitted_source_commit") != current_commit or state.get("executor_revision_v3") != executor_revision:
        launch = admitted_campaign_start(root, token) if event in ('push', 'workflow_dispatch') else None
        state["admitted_source_commit"] = current_commit
        state["executor_revision_v3"] = executor_revision
        state["continuation"] = {
            "status": "AWAITING_CHATGPT_BASELINE_OR_DIRECTIVE",
            "reason": "NEW_SOURCE_OR_PROTOCOL_BINDING",
            "updated": time.time(),
        }
        if launch is None:
            ledger.save(state)
            print("New material binding requires private ChatGPT baseline and source-bound Garden context capsule before OpenRouter inference")
            return
        state['continuation'] = {**launch, 'updated': time.time()}
        continuation = state['continuation']
        ledger.save(state)

    status = continuation.get("status")
    if status == "DEFERRED_DAILY" and time.time() < float(continuation.get("resume_after", 0)):
        _save_if_quality_changed(ledger, state, quality_added)
        return
    if status == 'DISPATCHED':
        if event != 'schedule' or time.time() - float(continuation.get('updated', 0)) < 3600:
            _save_if_quality_changed(ledger, state, quality_added)
            return
    if status not in ("READY", "DEFERRED_DAILY", "DISPATCHED"):
        _save_if_quality_changed(ledger, state, quality_added)
        print("Queue state: " + str(status) + "; no automatic dispatch")
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
    if quality_added:
        print("Queued " + str(quality_added) + " reviewer response(s) for ChatGPT quality adjudication")
    print("Next isolated reviewer dispatched")


if __name__ == "__main__":
    try:
        dispatch()
    except Exception as exc:
        print("INDEPENDENT_BRANCH_CONTINUATION_STOPPED: " + type(exc).__name__ + "; no inference was made by dispatcher")
        raise SystemExit(2)
