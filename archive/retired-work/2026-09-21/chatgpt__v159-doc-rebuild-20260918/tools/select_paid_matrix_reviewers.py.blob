#!/usr/bin/env python3
"""Select the bounded paid OpenRouter reviewer set for routine Garden review."""
from __future__ import annotations

import json
from pathlib import Path
from tools.provider_exclusion import load_policy, require_allowed_model, openrouter_provider_policy

POLICY = Path("agents/openrouter-paid-review-policy.json")
REGISTRY = Path("agents/reviewer-slot-registry.json")
OUTPUT = Path("agents/runtime/paid-selection.json")


def active_reviewers(policy: dict, registry: dict, exclusion_policy: dict) -> list[dict]:
    if registry.get("schema") != "GardenReviewerSlotRegistry/v1":
        raise ValueError("unsupported reviewer slot registry")
    slots = list(registry.get("slots") or [])
    required = int(registry.get("required_active_slots", 0))
    if len(slots) != required or required != 4:
        raise ValueError("exactly four governed reviewer slots required")
    if any(slot.get("state") != "ACTIVE" for slot in slots):
        raise ValueError("reviewer slot not ACTIVE; repair or governed replacement required before new convergence task")
    selected = [{"family": str(s["family"]), "role": str(s["role"]), "model": str(s["model"])} for s in slots]
    families = [row["family"] for row in selected]
    if len(set(families)) != required:
        raise ValueError("reviewer slot families must remain distinct")
    if any(not row["model"].strip() for row in selected):
        raise ValueError("reviewer slot is missing a model")
    if any(row["model"].endswith(":free") for row in selected):
        raise ValueError("paid routine selector may not silently substitute free routes")
    for row in selected:
        require_allowed_model(model_id=row["model"], family=row["family"], policy=exclusion_policy)
    mirror = list(policy.get("routine_reviewers") or [])
    if mirror != selected:
        raise ValueError("paid-review routine_reviewers drifted from reviewer-slot-registry; update both in one governed PR")
    return selected


def main() -> int:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    if policy.get("schema") != "GardenOpenRouterPaidReviewPolicy/v1":
        raise SystemExit("unsupported paid-review policy schema")
    if policy.get("public_only") is not True:
        raise SystemExit("routine public reviewer policy must remain public-only")
    if policy.get("semantic_delta_admitted") is not False:
        raise SystemExit("routine reviewer policy may not self-admit semantic deltas")

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    exclusion_policy = load_policy()
    try:
        selected = active_reviewers(policy, registry, exclusion_policy)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    families = [row["family"] for row in selected]

    daily_ceiling = float(policy.get("daily_openrouter_cost_ceiling_usd", 0))
    if not (0 < daily_ceiling <= 10.0):
        raise SystemExit("daily OpenRouter cost ceiling must be >0 and <= $10.00")

    payload = {
        "schema": "GardenPaidModelSelection/v2",
        "purpose": policy["purpose"],
        "design_epoch": policy["design_epoch"],
        "provider_exclusion_policy": policy.get("provider_exclusion_policy"),
        "reviewer_quality_policy": policy.get("reviewer_quality_policy"),
        "reviewer_slot_registry": str(REGISTRY),
        "selected": selected,
        "approved_families": families,
        "daily_openrouter_cost_ceiling_usd": daily_ceiling,
        "routine_hourly_cost_ceiling_usd": policy["routine_hourly_cost_ceiling_usd"],
        "routine_model_call_cost_ceiling_usd": policy["routine_model_call_cost_ceiling_usd"],
        "max_prompt_characters": policy["max_prompt_characters"],
        "max_output_tokens": policy["max_output_tokens"],
        "provider_policy": openrouter_provider_policy(policy["provider_policy"], exclusion_policy),
        "semantic_delta_admitted": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
