#!/usr/bin/env python3
"""Deterministic Garden branch lifecycle scanner.

Implements CHECK-BRANCH-LIFECYCLE-001 and emits BranchLifecycleReceipt/v1.
The classification logic is pure over a supplied snapshot. Live GitHub access
is only a snapshot acquisition layer.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Any, Iterable

RULE_ID = "RULE-BRANCH-LIFECYCLE-001"
CHECK_ID = "CHECK-BRANCH-LIFECYCLE-001"
SCHEMA = "BranchLifecycleReceipt/v1"


def _norm_sha(value: Any) -> str:
    return str(value or "").strip()


def _pr_head(pr: dict[str, Any]) -> str:
    head = pr.get("head") or {}
    if isinstance(head, dict):
        return str(head.get("ref") or "")
    return str(pr.get("head_ref") or "")


def _pr_number(pr: dict[str, Any]) -> int | None:
    value = pr.get("number")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def classify_snapshot(
    *, repository: str, default_branch: str, head_sha: str,
    branches: Iterable[dict[str, Any]], pull_requests: Iterable[dict[str, Any]],
    retention_exceptions: dict[str, dict[str, Any]] | None = None,
    active_branch_budget: int = 9, observed_at: str | None = None,
) -> dict[str, Any]:
    """Return a deterministic receipt for one repository snapshot."""
    exceptions = retention_exceptions or {}
    prs_by_head: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pr in pull_requests:
        head = _pr_head(pr)
        if head:
            prs_by_head[head].append(pr)

    normalized_branches = []
    sha_to_branches: dict[str, list[str]] = defaultdict(list)
    for b in branches:
        name = str(b.get("name") or "")
        commit = b.get("commit")
        sha = _norm_sha(commit.get("sha") if isinstance(commit, dict) else b.get("sha"))
        if not name:
            continue
        normalized_branches.append({"name": name, "sha": sha})
        if name != default_branch and sha:
            sha_to_branches[sha].append(name)

    dispositions: list[dict[str, Any]] = []
    retained_count = active_count = deletable_count = unresolved_count = 0
    for branch in sorted(normalized_branches, key=lambda x: x["name"]):
        name, sha = branch["name"], branch["sha"]
        if name == default_branch:
            continue
        evidence: list[str] = []
        exception = exceptions.get(name)
        branch_prs = sorted(prs_by_head.get(name, []), key=lambda pr: (_pr_number(pr) or -1), reverse=True)
        open_prs = [pr for pr in branch_prs if str(pr.get("state") or "").lower() == "open"]
        merged_prs = [pr for pr in branch_prs if pr.get("merged_at")]
        closed_unmerged = [pr for pr in branch_prs if str(pr.get("state") or "").lower() == "closed" and not pr.get("merged_at")]

        if exception:
            disposition = str(exception.get("disposition") or "FROZEN").upper()
            if disposition not in {"ACTIVE", "FROZEN"}:
                disposition = "FROZEN"
            evidence.append("explicit_retention_exception")
            retained_count += 1
            active_count += int(disposition == "ACTIVE")
        elif open_prs:
            disposition = "ACTIVE"
            active_count += 1
            retained_count += 1
            evidence.extend(f"open_pr:{_pr_number(pr)}" for pr in open_prs if _pr_number(pr) is not None)
        elif merged_prs:
            disposition = "MERGED_DELETE_ELIGIBLE"
            deletable_count += 1
            evidence.extend(f"merged_pr:{_pr_number(pr)}" for pr in merged_prs if _pr_number(pr) is not None)
        elif closed_unmerged:
            disposition = "CLOSED_UNRESOLVED"
            unresolved_count += 1
            retained_count += 1
            evidence.extend(f"closed_unmerged_pr:{_pr_number(pr)}" for pr in closed_unmerged if _pr_number(pr) is not None)
        else:
            disposition = "UNCLASSIFIED"
            unresolved_count += 1
            retained_count += 1
            evidence.append("no_open_or_historical_pr_binding")

        duplicates = sorted(x for x in sha_to_branches.get(sha, []) if x != name)
        if duplicates:
            evidence.append("same_commit_as:" + ",".join(duplicates))
        dispositions.append({
            "branch": name, "sha": sha, "disposition": disposition, "evidence": evidence,
            "destructive_action_authorized": disposition == "MERGED_DELETE_ELIGIBLE",
        })

    budget_pass = active_count <= active_branch_budget
    status = "PASS" if not unresolved_count and budget_pass else "REVIEW_REQUIRED"
    return {
        "schema": SCHEMA, "rule_id": RULE_ID, "check_id": CHECK_ID,
        "repository": repository, "default_branch": default_branch,
        "repository_head_sha": head_sha, "observed_at": observed_at,
        "status": status, "active_branch_budget": active_branch_budget,
        "counts": {
            "non_default_branches": len(dispositions), "active": active_count,
            "retained_total": retained_count, "merged_delete_eligible": deletable_count,
            "unresolved": unresolved_count,
        },
        "budget_check": {
            "operator": "<=", "limit": active_branch_budget, "observed_active": active_count,
            "result": "PASS" if budget_pass else "FAIL",
        },
        "dispositions": dispositions,
        "safety": {
            "delete_only_when": "disposition == MERGED_DELETE_ELIGIBLE",
            "closed_unmerged_is_not_auto_delete": True,
            "unclassified_is_not_auto_delete": True,
            "retention_exception_precedence": True,
        },
    }


class GitHubClient:
    def __init__(self, token: str | None): self.token = token
    def get_json(self, url: str) -> Any:
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "garden-branch-lifecycle-check"}
        if self.token: headers["Authorization"] = f"Bearer {self.token}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    def get_all(self, url: str) -> list[Any]:
        out, page = [], 1
        while True:
            sep = "&" if "?" in url else "?"
            data = self.get_json(f"{url}{sep}per_page=100&page={page}")
            if not isinstance(data, list): raise RuntimeError(f"expected list from {url}")
            out.extend(data)
            if len(data) < 100: return out
            page += 1


def fetch_snapshot(repository: str, token: str | None) -> dict[str, Any]:
    owner, repo = repository.split("/", 1)
    base = f"https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}"
    client = GitHubClient(token)
    repo_meta = client.get_json(base)
    default_branch = repo_meta["default_branch"]
    branches = client.get_all(f"{base}/branches")
    pulls = client.get_all(f"{base}/pulls?state=all")
    default = next((b for b in branches if b.get("name") == default_branch), None)
    if not default: raise RuntimeError("default branch not found in branch snapshot")
    return {"repository": repository, "default_branch": default_branch, "head_sha": default["commit"]["sha"], "branches": branches, "pull_requests": pulls}


def _load_json(path: str | None) -> Any:
    if not path: return None
    with open(path, "r", encoding="utf-8") as handle: return json.load(handle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo")
    parser.add_argument("--snapshot")
    parser.add_argument("--exceptions")
    parser.add_argument("--budget", type=int, default=9)
    parser.add_argument("--observed-at", default=None)
    parser.add_argument("--output", default="-")
    args = parser.parse_args(argv)
    if bool(args.repo) == bool(args.snapshot): parser.error("provide exactly one of --repo or --snapshot")
    snapshot = _load_json(args.snapshot) if args.snapshot else fetch_snapshot(args.repo, os.getenv("GITHUB_TOKEN"))
    exceptions_data = _load_json(args.exceptions) or {}
    exceptions = exceptions_data.get("branches", exceptions_data)
    receipt = classify_snapshot(repository=snapshot["repository"], default_branch=snapshot["default_branch"], head_sha=snapshot["head_sha"], branches=snapshot["branches"], pull_requests=snapshot["pull_requests"], retention_exceptions=exceptions, active_branch_budget=args.budget, observed_at=args.observed_at)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output == "-": sys.stdout.write(rendered)
    else:
        with open(args.output, "w", encoding="utf-8") as handle: handle.write(rendered)
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
