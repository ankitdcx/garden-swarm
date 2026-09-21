#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile

from tools import reconstruct_standalone_garden_release as release

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "agent" / "releases" / "inbox"
CONTENT = ROOT / "agent" / "releases" / "content"
V1510 = ROOT / "agent" / "releases" / "v15.10"

ZIP_NAME = "Garden_v15.10_STANDALONE_NO_LOSS_CANDIDATE_2026-09-20.zip"
ZIP_SHA256 = "9af4f13415c05c94c693ef9720c1917801cffa0ead86ff1b06895291d089561b"
CATALOGUE_NAME = "GARDEN_CATALOGUE_v15.10.txt"
DISPOSITION_NAME = "SEMANTIC_RETENTION_DISPOSITION_v15.10.jsonl"
DISPOSITION_SHA256 = "0001889bddb182fbbd12db1da0fd8684f5be9bafcd595c7a0938adab3535ec04"
DISPOSITION_BYTES = 1554572


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(message: str) -> None:
    raise ValueError(message)


def main() -> int:
    path = INBOX / ZIP_NAME
    if not path.exists():
        print("STANDALONE_RELEASE_IMPORT_NO_INBOX_ZIP")
        return 0

    raw_zip = path.read_bytes()
    if sha256(raw_zip) != ZIP_SHA256:
        fail("standalone v15.10 ZIP SHA-256 mismatch")

    manifest = json.loads((V1510 / "RELEASE_MANIFEST_v15.10.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        required = set(manifest["primary_sources"]) | {
            "CURRENT_READING_MAP_v15.10.json",
            "RETENTION_CLOSURE_RECEIPT_v15.10.json",
            DISPOSITION_NAME,
            "verify_v15.10_retention.py",
        }
        missing = sorted(required - names)
        if missing:
            fail("standalone package missing entries: " + ", ".join(missing))

        for name, meta in manifest["primary_sources"].items():
            data = zf.read(name)
            if len(data) != meta["bytes"] or sha256(data) != meta["sha256"]:
                fail("primary source mismatch in uploaded ZIP: " + name)

        # Ensure the already-committed readable projections match the same package.
        if zf.read("GARDEN_BOOK_v15.10.txt") != (V1510 / "GARDEN_BOOK_v15.10.txt").read_bytes():
            fail("Book bytes differ from committed release source")
        if zf.read("GARDEN_TECHNICAL_v15.10.txt") != release.reconstruct_text_parts("15.10"):
            fail("Technical bytes differ from committed release source")
        if zf.read("GARDEN_VERSION_HISTORY_v15.10.txt") != (V1510 / "GARDEN_VERSION_HISTORY_v15.10.txt").read_bytes():
            fail("History bytes differ from committed release source")

        catalogue = zf.read(CATALOGUE_NAME)
        disposition = zf.read(DISPOSITION_NAME)
        if len(disposition) != DISPOSITION_BYTES or sha256(disposition) != DISPOSITION_SHA256:
            fail("retention disposition mismatch in uploaded ZIP")

    CONTENT.mkdir(parents=True, exist_ok=True)
    (CONTENT / CATALOGUE_NAME).write_bytes(catalogue)
    (CONTENT / DISPOSITION_NAME).write_bytes(disposition)

    # Prove the direct objects drive exact release reconstruction before commit.
    if release.reconstruct_catalogue_v1510() != catalogue:
        fail("direct Catalogue reconstruction mismatch after import")
    if release.reconstruct_object("retention_disposition") != disposition:
        fail("direct retention-disposition reconstruction mismatch after import")

    print(json.dumps({
        "schema": "GardenStandaloneReleaseImport/v1",
        "status": "PASS",
        "zip_sha256": ZIP_SHA256,
        "catalogue_sha256": sha256(catalogue),
        "retention_disposition_sha256": sha256(disposition),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("STANDALONE_RELEASE_IMPORT_FAIL:" + type(exc).__name__)
        raise
