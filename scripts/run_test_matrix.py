#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITES = [
    ("PROTOTYPE_CONFORMANCE", ["prototype/tests"]),
    ("SERVER_CONTRACT", ["server/tests"]),
    ("SWARM_CONTRACT", ["swarm/tests"]),
    ("ADVERSARIAL", ["tests/adversarial"]),
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="/tmp/garden-test-matrix-receipt.json")
    args = p.parse_args()
    rows = []
    for suite, paths in SUITES:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", *paths],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        rows.append({
            "suite": suite,
            "paths": paths,
            "result": "PASS" if proc.returncode == 0 else "FAIL",
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        })
    overall = "PASS" if all(row["result"] == "PASS" for row in rows) else "FAIL"
    receipt = {
        "schema": "GardenRepositoryTestMatrixReceipt/v1",
        "repository": "ankitdcx/garden-swarm",
        "suites": rows,
        "overall": overall,
        "rule": "Every applicable test class must PASS; no suite PASS overrides another suite FAIL/UNKNOWN/STALE/INCONCLUSIVE.",
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"overall": overall, "suites": {r['suite']: r['result'] for r in rows}}, sort_keys=True))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
