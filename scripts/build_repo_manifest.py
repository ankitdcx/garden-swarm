#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "gsl" / "profile" / "REPO_MANIFEST.json"
EXCLUDED = {"gsl/profile/REPO_MANIFEST.json"}
EXCLUDED_PREFIXES = ("gsl/receipts/",)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked() -> list[str]:
    proc = subprocess.run(["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=True)
    return sorted(line.strip() for line in proc.stdout.splitlines() if line.strip())


def build() -> dict:
    rows = []
    counts: Counter[str] = Counter()
    for rel in tracked():
        if rel in EXCLUDED or rel.startswith(EXCLUDED_PREFIXES):
            continue
        path = ROOT / rel
        if not path.is_file():
            continue
        rows.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256(path)})
        counts[rel.split("/", 1)[0]] += 1
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "schema": "GardenRepositorySurfaceManifest/v1",
        "repository": "ankitdcx/garden-swarm",
        "design_epoch_ref": "Garden-v15.5@63561ce9fcd4a72f44af333662b342fd18c4e99930209c30c5f801bcc5c74598",
        "root_algorithm": "sha256(canonical-json(sorted tracked path/bytes/sha256 rows excluding manifest and gsl/receipts/*))",
        "repository_content_root": hashlib.sha256(encoded).hexdigest(),
        "tracked_artifact_count": len(rows),
        "top_level_counts": dict(sorted(counts.items())),
        "artifacts": rows,
        "excluded_from_root": sorted(EXCLUDED) + ["gsl/receipts/*"],
        "boundary": "This manifest establishes the tracked repository surface and content identity, not semantic Garden certification."
    }


def text(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--write", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    payload = build()
    expected = text(payload)
    if args.write:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(expected, encoding="utf-8")
        print(json.dumps({"status":"WRITTEN","root":payload["repository_content_root"],"count":payload["tracked_artifact_count"]}, sort_keys=True))
        return 0
    if args.check:
        actual = MANIFEST.read_text(encoding="utf-8") if MANIFEST.is_file() else None
        ok = actual == expected
        print(json.dumps({"status":"PASS" if ok else "FAIL","root":payload["repository_content_root"],"count":payload["tracked_artifact_count"]}, sort_keys=True))
        if not ok:
            print("---EXPECTED-REPO-MANIFEST---")
            print(expected, end="")
            print("---END-EXPECTED-REPO-MANIFEST---")
        return 0 if ok else 1
    print(expected, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
