#!/usr/bin/env python3
"""High-confidence changed-file secret scanner for Garden CI."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

RULES = {
    "PRIVATE_KEY_PEM": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "GITHUB_TOKEN": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "OPENAI_OR_OPENROUTER_KEY": re.compile(r"\bsk-(?:proj-|or-v1-)?[A-Za-z0-9_-]{20,}\b"),
    "AWS_ACCESS_KEY_ID": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GOOGLE_API_KEY": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "HIGH_CONFIDENCE_ASSIGNMENT": re.compile(r"(?ix)\b(?:api[_-]?key|secret|password|access[_-]?token)\b\s*[:=]\s*[\"']([A-Za-z0-9_./+=-]{32,})[\"']"),
}
PLACEHOLDER_WORDS = ("example", "placeholder", "redacted", "changeme", "dummy", "fake", "test-only", "<", "${")


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def changed_files(base: str, head: str) -> list[str]:
    out = _git("diff", "--name-only", "--diff-filter=ACMR", base, head)
    return [x for x in out.splitlines() if x]


def load_allowlist(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "GardenSecretScanAllowlist/v1":
        raise ValueError("unsupported secret-scan allowlist")
    rows = data.get("entries") or []
    if not isinstance(rows, list):
        raise ValueError("allowlist entries must be a list")
    return rows


def _allowed(path: str, rule: str, line: str, rows: list[dict[str, Any]]) -> bool:
    line_hash = hashlib.sha256(line.encode("utf-8")).hexdigest()
    return any(row.get("path") == path and row.get("rule") == rule and row.get("line_sha256") == line_hash and str(row.get("reason") or "").strip() for row in rows)


def scan_paths(paths: list[str], *, root: Path = Path("."), allowlist: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    allowlist = allowlist or []; findings = []; scanned = 0
    for rel in paths:
        p = root / rel
        if not p.is_file():
            continue
        try:
            raw = p.read_bytes()
        except OSError:
            continue
        if b"\x00" in raw:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        scanned += 1
        for lineno, line in enumerate(text.splitlines(), 1):
            for rule, pattern in RULES.items():
                match = pattern.search(line)
                if not match:
                    continue
                candidate = match.group(1) if rule == "HIGH_CONFIDENCE_ASSIGNMENT" and match.groups() else match.group(0)
                if rule == "HIGH_CONFIDENCE_ASSIGNMENT" and any(word in candidate.lower() for word in PLACEHOLDER_WORDS):
                    continue
                if _allowed(rel, rule, line, allowlist):
                    continue
                findings.append({"path": rel, "line": lineno, "rule": rule, "match_sha256": hashlib.sha256(candidate.encode("utf-8")).hexdigest()})
    return {"schema": "GardenSecretScanReceipt/v1", "scanned_text_files": scanned, "finding_count": len(findings), "findings": findings, "status": "BLOCKED" if findings else "PASS", "boundary": "Hashes identify suspected matches without printing credential material."}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--base", required=True); parser.add_argument("--head", default="HEAD"); parser.add_argument("--allowlist", default="security/secret-scan-allowlist.json"); parser.add_argument("--output"); args = parser.parse_args()
    receipt = scan_paths(changed_files(args.base, args.head), allowlist=load_allowlist(Path(args.allowlist))); rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output: Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end=""); return 0 if receipt["status"] == "PASS" else 2

if __name__ == "__main__": raise SystemExit(main())
