#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_version() -> dict[str, str]:
    lines = [line.strip() for line in (ROOT / "VERSION").read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) < 3:
        raise SystemExit("VERSION must contain Garden release, GSL version, and release date")
    garden = lines[0]
    gsl = lines[1]
    date_match = re.fullmatch(r"Release date:\s*(\d{4}-\d{2}-\d{2})", lines[2])
    if not date_match:
        raise SystemExit("VERSION release date line is malformed")
    return {"garden": garden, "gsl": gsl, "release_date": date_match.group(1)}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="/tmp/version-epoch-receipt.json")
    args = p.parse_args()
    version = parse_version()
    epoch = json.loads((ROOT / "gsl" / "epoch" / "DESIGN_EPOCH.json").read_text(encoding="utf-8"))
    branch_policy = json.loads((ROOT / "gsl" / "epoch" / "BRANCH_EPOCH_POLICY.json").read_text(encoding="utf-8"))
    failures: list[str] = []

    canonical = str(epoch.get("canonical_release", ""))
    expected_release = version["garden"].replace(" ", "-") + "-" + version["release_date"]
    if canonical != expected_release:
        failures.append(f"VERSION_DESIGN_EPOCH_RELEASE_MISMATCH:{canonical}!={expected_release}")
    if str(epoch.get("gsl")) != version["gsl"].removeprefix("GSL "):
        failures.append(f"VERSION_GSL_MISMATCH:{epoch.get('gsl')}!={version['gsl']}")
    if branch_policy.get("current_design_epoch_ref") != epoch.get("design_epoch_ref"):
        failures.append("BRANCH_EPOCH_POLICY_STALE")
    if epoch.get("accepted") is not False:
        failures.append("REPOSITORY_MUST_NOT_SELF_ACCEPT_DESIGN_EPOCH")

    receipt = {
        "schema": "GardenVersionEpochCouplingReceipt/v1",
        "version": version,
        "design_epoch_ref": epoch.get("design_epoch_ref"),
        "canonical_release": canonical,
        "branch_epoch_policy": "gsl/epoch/BRANCH_EPOCH_POLICY.json",
        "result": "PASS" if not failures else "FAIL",
        "failures": failures,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"result": receipt["result"], "failures": failures}, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
