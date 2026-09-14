#!/usr/bin/env python3
"""Deterministically select one bounded Garden Design Review Matrix target per UTC hour.

This is scheduling/evidence plumbing only. It never admits a semantic delta, grants
reviewers authority, or changes canonical Garden source. The workflow checkout is
ephemeral: the matrix rewrite below selects the target for this run only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

MATRIX = Path("agents/design-review-matrix.json")
RECEIPT = Path("agents/runtime/design-target-selection.json")


def select_target(matrix: dict[str, Any], slot: int) -> dict[str, Any]:
    targets = list(matrix.get("targets") or [])
    if len(targets) < 2:
        raise ValueError("Design Review Matrix needs at least two targets for hourly rotation")
    if slot < 0:
        raise ValueError("hour_slot must be non-negative")
    index = slot % len(targets)
    target = targets[index]
    target_id = str(target.get("target_id", "")).strip()
    if not target_id:
        raise ValueError("selected target has no target_id")
    matrix["active_target_id"] = target_id
    matrix["active_target_selection_reason"] = (
        f"Deterministic hourly round-robin slot={slot}; index={index} of {len(targets)}. "
        "Scheduling evidence only; no semantic authority."
    )
    matrix["active_target_hour_slot"] = slot
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", default=str(MATRIX))
    parser.add_argument("--slot", type=int)
    parser.add_argument("--receipt", default=str(RECEIPT))
    args = parser.parse_args()

    matrix_path = Path(args.matrix)
    raw = matrix_path.read_bytes()
    input_matrix_sha256 = hashlib.sha256(raw).hexdigest()
    matrix = json.loads(raw.decode("utf-8"))
    if matrix.get("schema") != "GardenDesignReviewMatrix/v1":
        raise SystemExit("unsupported GardenDesignReviewMatrix schema")
    if matrix.get("semantic_compliance_proved") is not False:
        raise SystemExit("review matrix may not self-claim semantic compliance")

    slot = args.slot if args.slot is not None else int(time.time() // 3600)
    target = select_target(matrix, slot)
    target_index = next(
        i for i, row in enumerate(matrix["targets"]) if row.get("target_id") == target["target_id"]
    )

    # This mutation exists only inside the workflow checkout so the existing bounded
    # review tool can consume exactly the selected target. It is not committed.
    matrix_path.write_text(json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    receipt = {
        "schema": "GardenDesignTargetSelectionReceipt/v1",
        "hour_slot": slot,
        "selection_mode": "DETERMINISTIC_HOURLY_ROUND_ROBIN",
        "target_id": target["target_id"],
        "target_index": target_index,
        "target_count": len(matrix["targets"]),
        "design_epoch": matrix["design_epoch"],
        "canonical_source_root_sha256": matrix["canonical_source_root_sha256"],
        "input_matrix_sha256": input_matrix_sha256,
        "semantic_delta_admitted": False,
        "authority_effect": "NONE_PROPOSAL_ONLY",
    }
    out = Path(args.receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
