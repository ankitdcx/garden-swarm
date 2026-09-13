#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = Path("/tmp")


def run_stage(name: str, argv: list[str], receipt: str | None = None) -> dict:
    proc = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True)
    row = {
        "stage": name,
        "argv": argv,
        "result": "PASS" if proc.returncode == 0 else "FAIL",
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
    }
    if receipt:
        path = Path(receipt)
        row["receipt_path"] = receipt
        if path.is_file():
            row["receipt"] = json.loads(path.read_text(encoding="utf-8"))
        else:
            row["result"] = "FAIL"
            row["receipt_missing"] = True
    return row


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="/tmp/ci-conformance-pipeline-receipt.json")
    p.add_argument("--base-sha", default=os.getenv("BASE_SHA"))
    p.add_argument("--head-sha", default=os.getenv("HEAD_SHA"))
    args = p.parse_args()

    stages = [
        run_stage("PUBLIC_RELEASE_INTEGRITY", [sys.executable, "scripts/verify_public_release.py"]),
        run_stage("GSL_NAMESPACE", [sys.executable, "scripts/verify_gsl_namespace.py", "--output", "/tmp/gsl-namespace-receipt.json"], "/tmp/gsl-namespace-receipt.json"),
        run_stage("VERSION_DESIGN_EPOCH", [sys.executable, "scripts/verify_version_epoch.py", "--output", "/tmp/version-epoch-receipt.json"], "/tmp/version-epoch-receipt.json"),
        run_stage("REPO_SURFACE_MANIFEST", [sys.executable, "scripts/build_repo_manifest.py", "--check"]),
        run_stage("REPO_PROFILE_AUDIT", [sys.executable, "scripts/audit_repo_gsl.py", "--strict-frontier", "--output", "/tmp/garden-repo-gsl-audit.json"], "/tmp/garden-repo-gsl-audit.json"),
        run_stage("GSL_APPLICATION", [sys.executable, "scripts/verify_gsl_application.py", "--output", "/tmp/garden-gsl-application-receipt.json"], "/tmp/garden-gsl-application-receipt.json"),
        run_stage("GENERATED_FUNCTION_CONTRACT_ALLOWLIST", [sys.executable, "scripts/verify_generated_contract_allowlist.py"]),
        run_stage("REFERENCE_CLOSURE", [sys.executable, "scripts/build_reference_closure.py", "--output", "/tmp/reference-closure-receipt.json"], "/tmp/reference-closure-receipt.json"),
        run_stage("TEST_MATRIX", [sys.executable, "scripts/run_test_matrix.py", "--output", "/tmp/test-matrix-receipt.json"], "/tmp/test-matrix-receipt.json"),
        run_stage("DURABLE_RECEIPTS", [sys.executable, "scripts/build_durable_gsl_receipts.py", "--check"]),
    ]
    if args.base_sha and args.head_sha:
        stages.append(run_stage(
            "REPO_CHANGE_GATE",
            [sys.executable, "scripts/gate_repo_change.py", "--base-sha", args.base_sha, "--head-sha", args.head_sha, "--output", "/tmp/repo-change-gate-receipt.json"],
            "/tmp/repo-change-gate-receipt.json",
        ))

    overall = "PASS" if all(row["result"] == "PASS" for row in stages) else "FAIL"
    receipt = {
        "schema": "CIConformancePipelineReceipt/v2",
        "repository": "ankitdcx/garden-swarm",
        "design_epoch_ref": "Garden-v15.5@63561ce9fcd4a72f44af333662b342fd18c4e99930209c30c5f801bcc5c74598",
        "stages": stages,
        "overall": overall,
        "merge_semantics": "PASS only when every applicable stage PASSes. No override may relabel FAIL/UNKNOWN/STALE/INCONCLUSIVE/TIMEOUT/RESOURCE_UNKNOWN/MALFORMED as PASS.",
        "boundary": "Pipeline PASS is repository-scope conformance evidence, not canonical Garden promotion, empirical validation or deployment certification."
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"overall": overall, "stages": {r['stage']: r['result'] for r in stages}}, sort_keys=True))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
