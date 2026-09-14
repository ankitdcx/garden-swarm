#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_DIR = ROOT / "gsl" / "receipts"
EXCLUDED_PREFIX = "gsl/receipts/"


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=check)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(payload: dict) -> str:
    return sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def stable_reference_detail_digest(payload: dict) -> str:
    """Digest reference evidence without self-hashing generated durable receipts."""
    stable = dict(payload)
    scanned_sources = stable.get("scanned_sources")
    if isinstance(scanned_sources, list):
        stable["scanned_sources"] = [
            row
            for row in scanned_sources
            if not (
                isinstance(row, dict)
                and str(row.get("path", "")).startswith(EXCLUDED_PREFIX)
            )
        ]
    return canonical_digest(stable)


def repo_content_root() -> tuple[str, list[dict[str, str]]]:
    tracked = run("git", "ls-files").stdout.splitlines()
    rows: list[dict[str, str]] = []
    for rel in sorted(x.strip() for x in tracked if x.strip() and not x.startswith(EXCLUDED_PREFIX)):
        path = ROOT / rel
        if not path.is_file():
            continue
        rows.append({"path": rel, "sha256": sha256_bytes(path.read_bytes())})
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(canonical), rows


def generate_payloads() -> tuple[dict, dict]:
    root, rows = repo_content_root()
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        app_path = td_path / "app.json"
        ref_path = td_path / "ref.json"
        audit_path = td_path / "audit.json"
        app = run("python", "scripts/verify_gsl_application.py", "--output", str(app_path), check=False)
        ref = run("python", "scripts/build_reference_closure.py", "--output", str(ref_path), check=False)
        audit = run("python", "scripts/audit_repo_gsl.py", "--strict-frontier", "--output", str(audit_path), check=False)
        app_payload = json.loads(app_path.read_text(encoding="utf-8")) if app_path.exists() else {"overall":"MALFORMED"}
        ref_payload = json.loads(ref_path.read_text(encoding="utf-8")) if ref_path.exists() else {"status":"MALFORMED"}
        audit_payload = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {"frontier_artifact_count":-1}

    conformance = {
        "schema": "CIConformancePipelineReceipt/v1",
        "publication_mode": "COMMITTED_DURABLE_SNAPSHOT",
        "repository": "ankitdcx/garden-swarm",
        "repository_content_root_algorithm": "sha256(canonical-json(sorted tracked path/sha256 rows excluding gsl/receipts/*))",
        "repository_content_root": root,
        "tracked_artifact_count_excluding_receipts": len(rows),
        "design_epoch_ref": app_payload.get("design_epoch_ref"),
        "application_conformance_overall": app_payload.get("overall"),
        "repo_frontier_artifact_count": audit_payload.get("frontier_artifact_count"),
        "repo_profile_error_count": audit_payload.get("profile_error_count", 0),
        "detail_digest_sha256": canonical_digest(app_payload),
        "reproduction": [
            "python scripts/verify_gsl_application.py --output /tmp/garden-gsl-conformance-receipt.json",
            "python scripts/audit_repo_gsl.py --strict-frontier --output /tmp/garden-repo-gsl-audit.json",
            "python scripts/build_durable_gsl_receipts.py --check"
        ],
        "result": "PASS" if app.returncode == 0 and audit.returncode == 0 else "FAIL",
        "boundary": "Scoped repository conformance evidence only; not canonical Garden promotion, empirical validation or deployment certification."
    }
    reference = {
        "schema": "ReferenceClosureReceipt/v1",
        "publication_mode": "COMMITTED_DURABLE_SNAPSHOT",
        "repository": "ankitdcx/garden-swarm",
        "repository_content_root": root,
        "scanner_version": ref_payload.get("scanner_version"),
        "coverage": ref_payload.get("coverage"),
        "reference_count": ref_payload.get("reference_count"),
        "unresolved_count": ref_payload.get("unresolved_count"),
        "detail_digest_sha256": stable_reference_detail_digest(ref_payload),
        "reproduction": [
            "python scripts/build_reference_closure.py --output /tmp/reference-closure-receipt.json",
            "python scripts/build_durable_gsl_receipts.py --check"
        ],
        "status": "PASS" if ref.returncode == 0 else "FAIL",
        "semantic_reference_closure_proved": False
    }
    return conformance, reference


def serialized(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    conformance, reference = generate_payloads()
    outputs = {
        RECEIPT_DIR / "CONFORMANCE_RECEIPT.json": serialized(conformance),
        RECEIPT_DIR / "REFERENCE_CLOSURE_RECEIPT.json": serialized(reference),
    }
    if args.check:
        failures = []
        for path, expected in outputs.items():
            actual = path.read_text(encoding="utf-8") if path.is_file() else None
            if actual != expected:
                failures.append(str(path.relative_to(ROOT)))
        print(json.dumps({"status":"PASS" if not failures else "FAIL","stale_or_missing":failures,"repository_content_root":conformance["repository_content_root"]}, sort_keys=True))
        return 0 if not failures else 1
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
    print(json.dumps({"status":"WRITTEN","repository_content_root":conformance["repository_content_root"],"files":[str(x.relative_to(ROOT)) for x in outputs]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
