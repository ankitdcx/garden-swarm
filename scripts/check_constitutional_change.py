#!/usr/bin/env python3
"""Fail-closed detector for repository constitutional-path changes.

Until an external/trusted-base approval verifier exists, any observed change to a
path declared constitutional by gsl/CHANGE_POLICY.json returns ESCALATE and a
non-zero process exit. This script does not approve constitutional changes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]


def evaluate(changed_paths: Iterable[str]) -> dict:
    policy = json.loads((ROOT / "gsl" / "CHANGE_POLICY.json").read_text(encoding="utf-8"))
    constitutional = set(map(str, policy.get("constitutional_paths") or []))
    observed = sorted({str(p).strip() for p in changed_paths if str(p).strip()})
    touched = sorted(set(observed) & constitutional)
    if not touched:
        return {
            "schema": "GardenConstitutionalChangeGuardReceipt/v1",
            "result": "PASS",
            "constitutional_paths_touched": [],
            "changed_paths": observed,
            "authority_effect": "NONE",
        }
    return {
        "schema": "GardenConstitutionalChangeGuardReceipt/v1",
        "result": "ESCALATE",
        "constitutional_paths_touched": touched,
        "changed_paths": observed,
        "reason": "Constitutional path changed while no external/trusted-base approval verifier is implemented. Current change policy requires candidate/ESCALATE.",
        "approval_verifier_status": "NOT_IMPLEMENTED",
        "authority_effect": "NONE_NO_APPROVAL_GRANTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--paths-file")
    parser.add_argument("--output", default="/tmp/constitutional-change-guard.json")
    args = parser.parse_args()
    paths = list(args.paths)
    if args.paths_file:
        paths.extend(Path(args.paths_file).read_text(encoding="utf-8").splitlines())
    receipt = evaluate(paths)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
