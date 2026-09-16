"""Secret-free preflight for the active independent-branch OpenRouter worker."""
from __future__ import annotations

import json
import os
from pathlib import Path

from tools import independent_branch_protocol as protocol
from tools import select_paid_matrix_reviewers as reviewer_selector
from tools import single_review_worker as legacy
from tools.provider_exclusion import load_policy as load_exclusion_policy


def preflight() -> None:
    legacy.host_check()
    token = os.environ.get("GH_REVIEW_TOKEN")
    if not token:
        raise ValueError("state access token missing")
    ledger = legacy.GitLedger(token)
    state = ledger.value
    if state.get("paused") is not False or state.get("scope") != "PUBLIC_MATRIX_REVIEW_ONLY":
        raise ValueError("review state paused or outside public scope")
    policy = json.loads(Path("agents/independent-branch-convergence-policy.json").read_text(encoding="utf-8"))
    protocol.load_policy(policy)
    model_policy = json.loads(Path("agents/openrouter-paid-review-policy.json").read_text(encoding="utf-8"))
    registry = json.loads(Path("agents/reviewer-slot-registry.json").read_text(encoding="utf-8"))
    exclusion_policy = load_exclusion_policy(Path("agents/provider-exclusion-policy.json"))
    selected = reviewer_selector.active_reviewers(model_policy, registry, exclusion_policy)
    families = [row["family"] for row in selected]
    if len(families) != 4 or len(set(families)) != 4:
        raise ValueError("active board must contain exactly four distinct families")
    if int(model_policy["execution_limits"]["max_model_calls_per_dispatch"]) != 1:
        raise ValueError("one OpenRouter call per dispatch is required")
    if int(model_policy["execution_limits"]["max_concurrent_model_calls"]) != 1:
        raise ValueError("OpenRouter calls must remain sequential")
    print("Independent-branch preflight passed; active reviewer slots, ChatGPT directive and live budget checks remain required")


if __name__ == "__main__":
    try:
        preflight()
    except Exception as exc:
        print("INDEPENDENT_BRANCH_PREFLIGHT_BLOCKED: " + type(exc).__name__)
        raise SystemExit(2)
