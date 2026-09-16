#!/usr/bin/env python3
"""Plan isolated ChatGPT Garden workstreams and merge-train integration.

This planner reuses AgentWorkIntent semantic collision logic. It does not create
branches, merge PRs, issue approvals, or treat Git isolation as semantic proof.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from swarm.integration_provenance import AgentWorkIntent, compare_intents

POLICY_PATH = Path("CHATGPT_WORKSTREAM_POLICY.json")
SCHEMA = "GardenChatGPTWorkstreamIntent/v1"
PLAN_SCHEMA = "GardenChatGPTWorkstreamPlan/v1"


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "GardenChatGPTWorkstreamPolicy/v1":
        raise ValueError("unsupported ChatGPT workstream policy")
    return data


def validate_workstream(data: dict[str, Any], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy or load_policy()
    if data.get("schema") != SCHEMA:
        raise ValueError(f"schema must be {SCHEMA}")
    required = policy["workstream_intent_required_fields"]
    for field in required:
        if field not in data:
            raise ValueError(f"missing workstream field: {field}")
    for field in ("workstream_id", "work_package_id", "branch", "base_sha", "integration_strategy", "status"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError(f"{field} must be non-empty")
    base = data["base_sha"].lower()
    if len(base) != 40 or any(c not in "0123456789abcdef" for c in base):
        raise ValueError("base_sha must be a full Git SHA")
    if data["status"] not in policy["allowed_status"]:
        raise ValueError("invalid workstream status")
    if data["integration_strategy"] not in policy["allowed_integration_strategy"]:
        raise ValueError("invalid integration strategy")
    deps = data["dependency_intent_ids"]
    if not isinstance(deps, list) or any(not isinstance(x, str) or not x.strip() for x in deps):
        raise ValueError("dependency_intent_ids must be a list of non-empty strings")
    if data["workstream_id"] in deps:
        raise ValueError("workstream cannot depend on itself")
    if data.get("draft_pr_created_before_substantial_edit") is not True:
        raise ValueError("new ChatGPT workstream must expose an early draft PR before substantial edits")
    branch = data["branch"]
    prefix = policy["rules"]["future_chatgpt_branch_prefix"]
    integration_prefix = policy["collision_rule"]["integration_branch_prefix"]
    if data["status"] == "INTEGRATING":
        if not branch.startswith(integration_prefix):
            raise ValueError("integration workstream must use integration/ branch")
    elif not branch.startswith(prefix):
        raise ValueError("new ChatGPT workstream must use chatgpt/ branch")
    return dict(data)


def _components(nodes: list[str], edges: set[tuple[str, str]]) -> list[list[str]]:
    graph = {n: set() for n in nodes}
    for a, b in edges:
        graph[a].add(b); graph[b].add(a)
    seen: set[str] = set()
    out: list[list[str]] = []
    for node in nodes:
        if node in seen or not graph[node]:
            continue
        stack = [node]; comp = []
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur); comp.append(cur); stack.extend(sorted(graph[cur] - seen))
        out.append(sorted(comp))
    return out


def _toposort(ids: list[str], deps: dict[str, set[str]]) -> tuple[list[str], list[str]]:
    remaining = {k: set(v) for k, v in deps.items()}
    order: list[str] = []
    unknown: list[str] = []
    known = set(ids)
    for k, values in remaining.items():
        missing = values - known
        if missing:
            unknown.extend(f"{k}->{d}" for d in sorted(missing))
    if unknown:
        return [], sorted(unknown)
    while remaining:
        ready = sorted(k for k, v in remaining.items() if not v)
        if not ready:
            return order, ["DEPENDENCY_CYCLE:" + ",".join(sorted(remaining))]
        for k in ready:
            order.append(k); remaining.pop(k)
            for v in remaining.values():
                v.discard(k)
    return order, []


def plan(records: list[dict[str, Any]], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy or load_policy()
    rows = []
    by_id: dict[str, dict[str, Any]] = {}
    by_intent: dict[str, str] = {}
    branches: set[str] = set()
    for raw in records:
        ws = validate_workstream(raw["workstream"], policy)
        intent = AgentWorkIntent.from_mapping(raw["agent_intent"])
        if ws["workstream_id"] in by_id:
            raise ValueError("duplicate workstream_id")
        if ws["branch"] in branches:
            raise ValueError("two active workstreams cannot share a branch")
        if intent.base_sha != ws["base_sha"]:
            raise ValueError("workstream base must match AgentWorkIntent base")
        by_id[ws["workstream_id"]] = {"workstream": ws, "intent": intent}
        by_intent[intent.intent_id] = ws["workstream_id"]
        branches.add(ws["branch"])
        rows.append(ws["workstream_id"])

    collision_edges: set[tuple[str, str]] = set()
    comparisons = []
    ids = sorted(rows)
    for i, left in enumerate(ids):
        for right in ids[i + 1:]:
            cmp = compare_intents(by_id[left]["intent"], by_id[right]["intent"])
            comparisons.append({"left": left, "right": right, **cmp})
            if cmp["requires_integration_receipt"]:
                collision_edges.add((left, right))

    groups = _components(ids, collision_edges)
    collided = {x for g in groups for x in g}
    integration_groups = []
    for group in groups:
        bad = [w for w in group if by_id[w]["workstream"]["integration_strategy"] != "INTEGRATION_BRANCH_IF_COLLISION"]
        integration_groups.append({
            "source_workstreams": group,
            "status": "BLOCKED_POLICY" if bad else "INTEGRATION_BRANCH_REQUIRED",
            "policy_mismatches": bad,
            "recommended_branch": "integration/" + "-".join(x.split(":")[-1].replace("_", "-")[:24] for x in group)[:80],
            "source_branches_must_remain_intact": True,
            "integration_receipt_required": True,
        })

    direct = [w for w in ids if w not in collided and by_id[w]["workstream"]["status"] == "ACTIVE"]
    deps: dict[str, set[str]] = {}
    intent_to_workstream = dict(by_intent)
    for w in direct:
        requested = set(by_id[w]["workstream"]["dependency_intent_ids"])
        deps[w] = {intent_to_workstream[d] for d in requested if d in intent_to_workstream}
        missing = requested - set(intent_to_workstream)
        deps[w].update("__MISSING__" + d for d in missing)
    merge_train, dep_errors = _toposort(direct, deps)

    return {
        "schema": PLAN_SCHEMA,
        "workstream_count": len(ids),
        "comparisons": comparisons,
        "integration_groups": integration_groups,
        "merge_train": merge_train,
        "dependency_errors": dep_errors,
        "ready_for_direct_merge_train": not integration_groups and not dep_errors,
        "boundary": "Plan is collision/integration evidence only; repository checks, current-base freshness and protected admission still govern merge."
    }


def dependency_invalidations(merged_intent_data: dict[str, Any], remaining: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = AgentWorkIntent.from_mapping(merged_intent_data)
    out = []
    for raw in remaining:
        intent = AgentWorkIntent.from_mapping(raw["agent_intent"])
        cmp = compare_intents(intent, merged)
        if cmp["requires_integration_receipt"]:
            out.append({"workstream_id": raw["workstream"]["workstream_id"],
                        "event": "DEPENDENCY_INVALIDATION", "reasons": cmp["reasons"],
                        "required_action": "REVALIDATE_AGAINST_NEW_MAIN_BEFORE_CONTINUING"})
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("records", help="JSON list of {workstream, agent_intent} records")
    args = parser.parse_args()
    records = json.loads(Path(args.records).read_text(encoding="utf-8"))
    print(json.dumps(plan(records), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
