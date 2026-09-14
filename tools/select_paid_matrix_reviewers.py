#!/usr/bin/env python3
"""Select the fixed bounded paid OpenRouter reviewer set for routine Garden review."""
from __future__ import annotations

import json
from pathlib import Path

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

    selected = list(policy.get("routine_reviewers") or [])
    families = [str(row.get("family")) for row in selected]
    if families != ["deepseek", "qwen"]:
        raise SystemExit("routine paid reviewer set must be exactly DeepSeek + Qwen")
    if len(set(families)) != len(families):
        raise SystemExit("routine paid reviewer families must be distinct")
    if any(str(row.get("model", "")).endswith(":free") for row in selected):
        raise SystemExit("paid routine selector may not silently substitute free routes")

    payload = {
        "schema": "GardenPaidModelSelection/v1",
        "purpose": policy["purpose"],
        "design_epoch": policy["design_epoch"],
        "selected": selected,
        "routine_hourly_cost_ceiling_usd": policy["routine_hourly_cost_ceiling_usd"],
        "routine_model_call_cost_ceiling_usd": policy["routine_model_call_cost_ceiling_usd"],
        "max_prompt_characters": policy["max_prompt_characters"],
        "max_output_tokens": policy["max_output_tokens"],
        "provider_policy": policy["provider_policy"],
        "semantic_delta_admitted": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
