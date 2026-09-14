#!/usr/bin/env python3
"""Select distinct OpenRouter :free families for one matrix review execution."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from tools.free_model_rotation import catalog, choose


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="agents/runtime/free-selection.json")
    parser.add_argument("--slot", type=int)
    parser.add_argument("--count", type=int, default=3)
    args = parser.parse_args()
    # This count is the provider-call selection budget for this execution, not
    # the Garden semantic-admission quorum. The latter remains >=3 independent
    # completed families and is enforced by the review/integration gates.
    if args.count < 1:
        raise SystemExit("reviewer selection count must be at least one")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is required")
    slot = args.slot if args.slot is not None else int(datetime.now(timezone.utc).timestamp() // 3600)
    models = catalog(key)
    selected = choose(models, slot, count=args.count)
    families = [row["family"] for row in selected]
    if len(set(families)) != len(families):
        raise SystemExit("reviewer selection is not family-independent")
    if not all(str(row["model"]).endswith(":free") for row in selected):
        raise SystemExit("non-free reviewer route refused")
    payload = {
        "schema": "GardenFreeModelSelection/v2",
        "purpose": "DESIGN_REVIEW_MATRIX",
        "hour_slot": slot,
        "free_catalog_count": len(models),
        "required_family_count": args.count,
        "selection_scope": "EXECUTION_BUDGET_ONLY_NOT_ADMISSION_QUORUM",
        "selected": selected,
        "cost_policy": "OpenRouter :free routes only; reviewer calls must independently report usage.cost == 0 before review completion is eligible.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
