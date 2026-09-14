#!/usr/bin/env python3
"""Garden public-release integrity checks using only Python stdlib."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "AGENTS.md",
    "GARDEN_FOR_AGI.md",
    "PUBLIC_RELEASE.md",
    "LICENSE",
    "PATENT_AND_USE_NOTICE.md",
    "RELAY_PROTOCOL.md",
    "TASKS.md",
    "SOURCE_MANIFEST.json",
    "DISCOVERY.json",
    "relay/manifest.json",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CITATION.cff",
]

JSON_FILES = [
    "SOURCE_MANIFEST.json",
    "DISCOVERY.json",
    "relay/manifest.json",
]

PUBLIC_TEXT_SUFFIXES = {".md", ".txt", ".json", ".yml", ".yaml", ".cff", ".py"}
PERSONAL_EMAIL_RE = re.compile(
    r"[A-Z0-9._%+-]+@(gmail\.com|yahoo\.com|hotmail\.com|outlook\.com)",
    re.IGNORECASE,
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)
    print(f"FAIL: {msg}")


def main() -> int:
    errors: list[str] = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).is_file():
            fail(f"missing required file: {rel}", errors)

    for rel in JSON_FILES:
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"invalid JSON {rel}: {exc}", errors)

    manifest_path = ROOT / "SOURCE_MANIFEST.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            canonical = manifest.get("canonical_files", [])
            if len(canonical) != 5:
                fail(f"expected 5 canonical files, found {len(canonical)}", errors)
            for item in canonical:
                rel = item.get("path")
                expected = item.get("sha256")
                if not rel or not expected:
                    fail(f"malformed canonical file entry: {item!r}", errors)
                    continue
                path = ROOT / rel
                if not path.is_file():
                    fail(f"canonical file missing: {rel}", errors)
                    continue
                actual = sha256(path)
                if actual.lower() != str(expected).lower():
                    fail(
                        f"canonical SHA-256 mismatch for {rel}: expected {expected}, got {actual}",
                        errors,
                    )
        except Exception as exc:
            fail(f"cannot validate SOURCE_MANIFEST.json: {exc}", errors)

    # Guard against accidentally committing ordinary personal mailbox addresses.
    # GitHub noreply addresses are intentionally allowed.
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in PUBLIC_TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in PERSONAL_EMAIL_RE.finditer(text):
            value = match.group(0)
            if value.endswith("@users.noreply.github.com"):
                continue
            fail(f"possible personal email in tracked file {path.relative_to(ROOT)}: {value}", errors)

    if errors:
        print(f"\nGarden public-release integrity: FAIL ({len(errors)} finding(s))")
        return 1

    print("Garden public-release integrity: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
