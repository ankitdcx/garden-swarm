#!/usr/bin/env python3
"""Select the bounded paid OpenRouter reviewer set for routine Garden review."""
from __future__ import annotations

import json
from pathlib import Path
from tools.provider_exclusion import load_policy, require_allowed_model, openrouter_provider_policy

POLICY = Path("agents/openrouter-paid-review-policy.json")
OUTPUT = Path("agents/runtime/paid-selection.json")


def main() -> int:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    if policy.get("schema") != "GardenOpenRouterPaidReviewPolicy/v1":
        raise SystemExit("unsupported paid-review policy schema")
    if policy.get("public_only") is not True:
        raise SystemExit("routine public reviewer policy must remain public-only")
    if policy.get("semantic_delta_admitted") is not False:
        raise SystemExit("routine reviewer policy may not self-admit semantic deltas")

    exclusion_policy = load_policy()
    selected = list(policy.get("routine_reviewers") or [])
    if len(selected) < 2:
        raise SystemExit("routine paid reviewer set must contain at least two independent families")
    families = [str(row.get("family")) for row in selected]
    if len(set(families)) != len(families):
        raise SystemExit("routine paid reviewer families must be distinct")
    if any(not str(row.get("model", "")).strip() for row in selected):
        raise SystemExit("routine paid reviewer is missing a model")
    if any(str(row.get("model", "")).endswith(":free") for row in selected):
        raise SystemExit("paid routine selector may not silently substitute free routes")
    for row in selected:
        require_allowed_model(model_id=str(row.get("model", "")), family=str(row.get("family", "")), policy=exclusion_policy)

    daily_ceiling = float(policy.get("daily_openrouter_cost_ceiling_usd", 0))
    if not (0 < daily_ceiling <= 2.0):
        raise SystemExit("daily OpenRouter cost ceiling must be >0 and <= $2.00")

    payload = {
        "schema": "GardenPaidModelSelection/v2",
        "purpose": policy["purpose"],
        "design_epoch": policy["design_epoch"],
        "provider_exclusion_policy": policy.get("provider_exclusion_policy"),
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
