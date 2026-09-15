#!/usr/bin/env python3
"""Select the bounded DeepSeek + Qwen paid reviewer pair for public IP-origin review."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

POLICY = Path("agents/openrouter-paid-review-policy.json")
OUTPUT = Path("agents/runtime/paid-selection.json")
REQUIRED_FAMILIES = ("deepseek", "qwen")


def build_selection(policy: dict[str, Any]) -> dict[str, Any]:
    if policy.get("schema") != "GardenOpenRouterPaidReviewPolicy/v1":
        raise ValueError("unsupported paid-review policy schema")
    if policy.get("public_only") is not True:
        raise ValueError("IP-origin review policy must remain public-only")
    if policy.get("semantic_delta_admitted") is not False:
        raise ValueError("IP-origin review may not self-admit semantic deltas")

    by_family = {
        str(row.get("family")): row
        for row in (policy.get("routine_reviewers") or [])
        if isinstance(row, dict)
    }
    missing = [family for family in REQUIRED_FAMILIES if family not in by_family]
    if missing:
        raise ValueError(f"missing required IP-origin reviewer families: {missing}")

    selected = [by_family[family] for family in REQUIRED_FAMILIES]
    if any(str(row.get("model", "")).endswith(":free") for row in selected):
        raise ValueError("IP-origin paid selector may not silently substitute free routes")

    daily_ceiling = float(policy.get("daily_openrouter_cost_ceiling_usd", 0))
    if not (0 < daily_ceiling <= 1.0):
        raise ValueError("daily OpenRouter cost ceiling must be >0 and <= $1.00")
    provider_policy = policy.get("provider_policy") or {}
    if provider_policy.get("data_collection") != "deny":
        raise ValueError("provider data_collection must remain deny")

    return {
        "schema": "GardenPaidModelSelection/v2",
        "purpose": "PUBLIC_IP_ORIGIN_REVIEW",
        "design_epoch": policy["design_epoch"],
        "selected": selected,
        "approved_families": list(REQUIRED_FAMILIES),
        "daily_openrouter_cost_ceiling_usd": daily_ceiling,
        "routine_hourly_cost_ceiling_usd": policy["routine_hourly_cost_ceiling_usd"],
        "routine_model_call_cost_ceiling_usd": policy["routine_model_call_cost_ceiling_usd"],
        "max_prompt_characters": policy["max_prompt_characters"],
        "max_output_tokens": policy["max_output_tokens"],
        "provider_policy": provider_policy,
        "semantic_delta_admitted": False,
    }


def main() -> int:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    payload = build_selection(policy)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
