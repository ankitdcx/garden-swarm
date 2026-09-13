#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from tools.free_model_rotation import catalog

ROLE_CYCLE = ("formal", "implementation", "adversary", "grounding", "open_weight_baseline", "compliance")


def family_of(model_id: str) -> str:
    provider = model_id.split("/", 1)[0].strip().lower()
    return provider or model_id.split(":", 1)[0].lower()


def choose_flexible(models: list[dict], slot: int, preferred: int, minimum: int) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for model in models:
        model_id = str(model.get("id", ""))
        if not model_id.endswith(":free"):
            continue
        groups.setdefault(family_of(model_id), []).append(model)
    families = sorted(groups)
    if len(families) < minimum:
        raise SystemExit(f"Only {len(families)} distinct free provider families available; minimum is {minimum}")
    ordered = families[slot % len(families):] + families[:slot % len(families)]
    out = []
    for idx, family in enumerate(ordered[:preferred]):
        hits = groups[family]
        hits.sort(key=lambda row: int(row.get("context_length") or 0), reverse=True)
        model = hits[0]
        out.append({
            "family": family,
            "role": ROLE_CYCLE[idx % len(ROLE_CYCLE)],
            "model": model["id"],
            "context_length": model.get("context_length"),
        })
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="agents/runtime/free-selection.json")
    parser.add_argument("--slot", type=int)
    parser.add_argument("--preferred", type=int, default=6)
    parser.add_argument("--minimum", type=int, default=3)
    args = parser.parse_args()
    if args.minimum < 3 or args.preferred < args.minimum:
        raise SystemExit("invalid reviewer pool bounds")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is required")
    slot = args.slot if args.slot is not None else int(datetime.now(timezone.utc).timestamp() // 3600)
    models = catalog(key)
    selected = choose_flexible(models, slot, args.preferred, args.minimum)
    payload = {
        "schema":"GardenFreeModelSelection/v3",
        "purpose":"REVIEW_QUORUM",
        "hour_slot":slot,
        "free_catalog_count":len(models),
        "minimum_family_count":args.minimum,
        "preferred_family_count":args.preferred,
        "selected":selected,
        "cost_policy":"OpenRouter :free routes only; only valid structured findings count toward quorum.",
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
