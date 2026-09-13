#!/usr/bin/env python3
"""GitHub PR binding for Garden multi-agent integration provenance.

Requires an AgentWorkIntent/v1 JSON block in the PR body, binds declared paths to
actual changed files, compares against concurrent PR intents, and fails closed on
unresolved direct overlaps. Proposal-only: it never merges or grants authority.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Mapping
from urllib import request

from swarm.integration_provenance import AgentWorkIntent, assess_intents, normalize_path

INTENT_MARKER = "<!-- GARDEN_AGENT_WORK_INTENT -->"
RECEIPT_MARKER = "<!-- GARDEN_INTEGRATION_RECEIPT -->"


def extract_json_block(body: str | None, marker: str) -> Mapping[str, Any] | None:
    if not body or marker not in body:
        return None
    tail = body.split(marker, 1)[1]
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", tail, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError(f"{marker} must be followed by a fenced JSON object")
    data = json.loads(match.group(1))
    if not isinstance(data, dict):
        raise ValueError(f"{marker} block must contain a JSON object")
    return data


def _covers(declared: str, actual: str) -> bool:
    d, a = normalize_path(declared), normalize_path(actual)
    return d == a or a.startswith(d + "/")


def undeclared_paths(intent: AgentWorkIntent, changed_paths: list[str]) -> list[str]:
    return sorted(
        path for path in changed_paths
        if not any(_covers(declared, path) for declared in intent.target_paths)
    )


def direct_path_overlap(a: list[str], b: list[str]) -> bool:
    aa = [normalize_path(x) for x in a]
    bb = [normalize_path(x) for x in b]
    return any(x == y or x.startswith(y + "/") or y.startswith(x + "/") for x in aa for y in bb)


def evaluate_pr(
    *,
    current_pr_number: int,
    current_body: str | None,
    current_changed_paths: list[str],
    concurrent_prs: list[dict[str, Any]],
) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    intent_data = extract_json_block(current_body, INTENT_MARKER)
    if intent_data is None:
        return {
            "schema": "GardenPRIntegrationCheck/v1",
            "pr": current_pr_number,
            "disposition": "BLOCKED",
            "failures": ["MISSING_AGENT_WORK_INTENT"],
            "warnings": [],
            "authority_effect": "NONE_PROPOSAL_ONLY",
        }
    current = AgentWorkIntent.from_mapping(intent_data)
    undeclared = undeclared_paths(current, current_changed_paths)
    if undeclared:
        failures.append("UNDECLARED_CHANGED_PATHS:" + ",".join(undeclared))

    other_intents: list[AgentWorkIntent] = []
    unknown_direct: list[int] = []
    for pr in concurrent_prs:
        if int(pr["number"]) == current_pr_number:
            continue
        other_data = extract_json_block(pr.get("body"), INTENT_MARKER)
        if other_data is None:
            if direct_path_overlap(current_changed_paths, list(pr.get("changed_paths") or [])):
                unknown_direct.append(int(pr["number"]))
            else:
                warnings.append(f"PR#{pr['number']}:NO_DECLARED_INTENT_SEMANTIC_OVERLAP_UNKNOWN")
            continue
        other_intents.append(AgentWorkIntent.from_mapping(other_data))

    if unknown_direct:
        failures.append("UNKNOWN_CONCURRENT_INTENT_DIRECT_PATH_OVERLAP:" + ",".join(map(str, sorted(unknown_direct))))

    receipt = extract_json_block(current_body, RECEIPT_MARKER)
    guard = assess_intents(current, other_intents, receipt)
    if guard["disposition"] != "PASS":
        failures.append("INTEGRATION_GUARD:" + guard["disposition"])

    return {
        "schema": "GardenPRIntegrationCheck/v1",
        "pr": current_pr_number,
        "current_intent_id": current.intent_id,
        "current_intent_hash": current.evidence_hash(),
        "changed_paths": sorted(current_changed_paths),
        "guard": guard,
        "disposition": "BLOCKED" if failures else "PASS",
        "failures": failures,
        "warnings": warnings,
        "authority_effect": "NONE_PROPOSAL_ONLY",
        "uncertainty": "Concurrent PRs without AgentWorkIntent/v1 can only be checked for direct path overlap; cross-file semantic overlap remains unknown and is reported as a warning.",
    }


def _api_json(url: str, token: str) -> Any:
    req = request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "garden-integration-provenance",
    })
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _pr_files(api_url: str, token: str, number: int) -> list[str]:
    files: list[str] = []
    page = 1
    while True:
        data = _api_json(f"{api_url}/pulls/{number}/files?per_page=100&page={page}", token)
        files.extend(item["filename"] for item in data)
        if len(data) < 100:
            return files
        page += 1


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    api_root = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    if not event_path or not repository or not token:
        raise SystemExit("GITHUB_EVENT_PATH, GITHUB_REPOSITORY and GITHUB_TOKEN are required")
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    current_pr = event.get("pull_request")
    if not current_pr:
        raise SystemExit("pull_request event required")
    number = int(current_pr["number"])
    api_url = f"{api_root}/repos/{repository}"
    current_files = _pr_files(api_url, token, number)
    pulls = _api_json(f"{api_url}/pulls?state=open&per_page=100", token)
    concurrent: list[dict[str, Any]] = []
    for pr in pulls:
        pr_number = int(pr["number"])
        if pr_number == number:
            continue
        concurrent.append({
            "number": pr_number,
            "body": pr.get("body"),
            "changed_paths": _pr_files(api_url, token, pr_number),
        })
    result = evaluate_pr(
        current_pr_number=number,
        current_body=current_pr.get("body"),
        current_changed_paths=current_files,
        concurrent_prs=concurrent,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["disposition"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
