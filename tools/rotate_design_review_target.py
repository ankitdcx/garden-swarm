#!/usr/bin/env python3
"""Deterministically select one bounded Garden review target from a durable event key.

This is routing/evidence plumbing only. It never admits a semantic delta, grants
reviewers authority or changes canonical Garden source. No wall-clock fallback is
permitted: unchanged time passage must not rotate work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

MATRIX = Path("agents/design-review-matrix.json")
RECEIPT = Path("agents/runtime/design-target-selection.json")


def event_slot(event_key: str) -> int:
    key = str(event_key).strip()
    if not key:
        raise ValueError("event_key must be non-empty")
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:16], 16)


def select_target(matrix: dict[str, Any], slot: int) -> dict[str, Any]:
    targets = list(matrix.get("targets") or [])
    if len(targets) < 2:
        raise ValueError("Design Review Matrix needs at least two targets for deterministic rotation")
    if slot < 0:
        raise ValueError("event_slot must be non-negative")
    index = slot % len(targets)
    target = targets[index]
    target_id = str(target.get("target_id", "")).strip()
    if not target_id:
        raise ValueError("selected target has no target_id")
    matrix["active_target_id"] = target_id
    matrix["active_target_selection_reason"] = (
        f"Deterministic event-key rotation slot={slot}; index={index} of {len(targets)}. "
        "Routing evidence only; no semantic authority."
    )
    matrix["active_target_event_slot"] = slot
    matrix.pop("active_target_hour_slot", None)
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", default=str(MATRIX))
    parser.add_argument("--event-key")
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

    event_key = args.event_key or os.environ.get("GARDEN_EVENT_KEY") or os.environ.get("GITHUB_SHA")
    if args.slot is not None:
        slot = args.slot
        event_key_hash = None
        selection_mode = "EXPLICIT_EVENT_SLOT"
    else:
        if not event_key:
            raise SystemExit("event key is required unless --slot is supplied; no clock fallback is allowed")
        slot = event_slot(event_key)
        event_key_hash = hashlib.sha256(event_key.encode("utf-8")).hexdigest()
        selection_mode = "DETERMINISTIC_EVENT_HASH_ROUND_ROBIN"

    target = select_target(matrix, slot)
    target_index = next(i for i, row in enumerate(matrix["targets"]) if row.get("target_id") == target["target_id"])

    # Ephemeral workflow mutation only; the selected target is not committed here.
    matrix_path.write_text(json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    receipt = {
        "schema": "GardenDesignTargetSelectionReceipt/v2",
        "event_slot": slot,
        "event_key_sha256": event_key_hash,
        "selection_mode": selection_mode,
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
