#!/usr/bin/env python3
"""Derive a deterministic bounded repo-review target from the exact PR git diff."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "agents/repo-review-matrix.json"
RUNTIME = ROOT / "agents/runtime/pr-review"
CHUNK_SIZE = 10000
MAX_CHUNKS = 5


def run(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    args = parser.parse_args()

    changed = run("diff", "--name-only", f"{args.base_sha}...{args.head_sha}").decode("utf-8").splitlines()
    changed = [x.strip() for x in changed if x.strip()]
    diff = run("diff", "--no-ext-diff", "--unified=20", f"{args.base_sha}...{args.head_sha}")
    diff_sha = hashlib.sha256(diff).hexdigest()
    file_list_sha = hashlib.sha256("\n".join(changed).encode("utf-8")).hexdigest()

    RUNTIME.mkdir(parents=True, exist_ok=True)
    for old in RUNTIME.glob("pr-change-set-*.diff"):
        old.unlink()

    # Preserve both ends when a very large diff exceeds the bounded model evidence budget.
    max_bytes = CHUNK_SIZE * MAX_CHUNKS
    if len(diff) > max_bytes:
        front = max_bytes * 2 // 3
        back = max_bytes - front
        bounded = diff[:front] + b"\n... [BOUNDED MIDDLE OF PR DIFF OMITTED; FULL HASH/FILE LIST RETAINED] ...\n" + diff[-back:]
        coverage = "BOUNDED_HEAD_TAIL_OF_FULL_DIFF"
    else:
        bounded = diff
        coverage = "FULL_DIFF"

    files: list[str] = []
    for idx in range(0, len(bounded), CHUNK_SIZE):
        chunk = bounded[idx:idx + CHUNK_SIZE]
        path = RUNTIME / f"pr-change-set-{idx // CHUNK_SIZE:03d}.diff"
        path.write_bytes(chunk)
        files.append(path.relative_to(ROOT).as_posix())

    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    target = {
        "target_id": "RRM-PR-CHANGE-SET",
        "risk": "DERIVED_FROM_ACTUAL_DIFF",
        "review_question": (
            "Review this exact PR change set as a Garden/GSL repository transition. Attempt to falsify its correctness, "
            "authority containment, status/result algebra, DesignEpoch/source obligations, tests, provenance and fail-closed behavior. "
            "Do not infer unshown middle diff content; use NEEDS_CROSS_REFERENCE when bounded evidence is insufficient."
        ),
        "files": files,
        "public_only": True,
        "base_sha": args.base_sha,
        "head_sha": args.head_sha,
        "full_diff_sha256": diff_sha,
        "changed_file_list_sha256": file_list_sha,
        "changed_file_count": len(changed),
        "changed_files": changed,
        "evidence_coverage": coverage,
    }
    matrix["targets"] = [target] + [row for row in matrix.get("targets", []) if row.get("target_id") != target["target_id"]]
    MATRIX.write_text(json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    receipt = {
        "schema": "GardenPRReviewTargetReceipt/v1",
        "base_sha": args.base_sha,
        "head_sha": args.head_sha,
        "full_diff_sha256": diff_sha,
        "changed_file_list_sha256": file_list_sha,
        "changed_file_count": len(changed),
        "evidence_coverage": coverage,
        "evidence_chunks": files,
        "target_id": target["target_id"],
        "semantic_delta_admitted": False,
    }
    out = RUNTIME / "target-receipt.json"
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
