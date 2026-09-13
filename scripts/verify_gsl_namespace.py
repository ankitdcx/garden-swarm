#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="/tmp/gsl-namespace-receipt.json")
    args = p.parse_args()
    payload = json.loads((ROOT / "gsl" / "NAMESPACE.json").read_text(encoding="utf-8"))
    failures: list[str] = []
    mirrors = payload.get("temporary_compatibility_mirrors") or {}
    rows = []
    for alias, canonical in sorted(mirrors.items()):
        a = ROOT / alias
        c = ROOT / canonical
        if not c.is_file():
            failures.append(f"CANONICAL_GSL_PATH_MISSING:{canonical}")
            continue
        if not a.is_file():
            failures.append(f"DECLARED_GSL_MIRROR_MISSING:{alias}")
            continue
        ad, cd = digest(a), digest(c)
        if ad != cd:
            failures.append(f"GSL_MIRROR_DIVERGENCE:{alias}!={canonical}")
        rows.append({"alias": alias, "canonical": canonical, "alias_sha256": ad, "canonical_sha256": cd})

    receipt = {
        "schema": "GardenGSLNamespaceReceipt/v1",
        "design_epoch_ref": payload.get("design_epoch_ref"),
        "canonical_groups": payload.get("canonical_groups"),
        "temporary_mirror_count": len(mirrors),
        "mirror_bindings": rows,
        "result": "PASS" if not failures else "FAIL",
        "failures": failures,
        "boundary": "PASS establishes namespace/mirror integrity only; nested paths are authoritative."
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"result": receipt["result"], "mirror_count": len(mirrors), "failures": failures}, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
