#!/usr/bin/env python3
"""Select exactly one different Design Review Matrix target for the current hour."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

MATRIX = Path("agents/design-review-matrix.json")


def select_target(matrix: dict, slot: int) -> dict:
    targets = list(matrix.get("targets") or [])
    if len(targets) < 2:
        raise ValueError("Design Review Matrix needs at least two targets for hourly rotation")
    target = targets[slot % len(targets)]
    target_id = str(target.get("target_id", "")).strip()
    if not target_id:
        raise ValueError("selected target has no target_id")
    matrix["active_target_id"] = target_id
    matrix["active_target_selection_reason"] = (
        f"Deterministic hourly rotation slot={slot}; index={slot % len(targets)} of {len(targets)}. "
        "Rotation is scheduling evidence only and grants no semantic authority."
    )
    matrix["active_target_hour_slot"] = slot
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", default=str(MATRIX))
    parser.add_argument("--slot", type=int)
    parser.add_argument("--receipt", default="agents/runtime/design-target-selection.json")
    args = parser.parse_args()
    matrix_path = Path(args.matrix)
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    slot = args.slot if args.slot is not None else int(time.time() // 3600)
    target = select_target(matrix, slot)
    matrix_path.write_text(json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    receipt = {
        "schema": "GardenDesignTargetSelectionReceipt/v1",
        "hour_slot": slot,
        "target_id": target["target_id"],
        "target_count": len(matrix["targets"]),
        "selection_mode": "DETERMINISTIC_HOURLY_ROUND_ROBIN",
        "semantic_delta_admitted": False,
    }
    out = Path(args.receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
