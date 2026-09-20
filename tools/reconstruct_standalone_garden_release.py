#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import lzma
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "agent" / "releases" / "content"
V1510 = ROOT / "agent" / "releases" / "v15.10"
V1511 = ROOT / "agent" / "releases" / "v15.11"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def reconstruct_object(name: str) -> bytes:
    manifest = load_json(CONTENT / "CONTENT_OBJECTS_v15x.json")
    obj = manifest["objects"][name]
    direct_path = obj.get("direct_path")
    if direct_path:
        path = CONTENT / direct_path
        if path.exists():
            raw = path.read_bytes()
            if len(raw) != obj["raw_bytes"] or sha256(raw) != obj["raw_sha256"]:
                raise ValueError(f"direct content-object mismatch: {name}")
            return raw
    encoded = bytearray()
    for part in obj["parts"]:
        path = CONTENT / part["name"]
        raw = path.read_bytes()
        if len(raw) != part["bytes"] or sha256(raw) != part["sha256"]:
            raise ValueError(f"content-object part mismatch: {path.name}")
        encoded.extend(raw.strip())
    compressed = base64.b64decode(bytes(encoded), validate=True)
    if len(compressed) != obj["compressed_bytes"] or sha256(compressed) != obj["compressed_sha256"]:
        raise ValueError(f"compressed content-object mismatch: {name}")
    raw = lzma.decompress(compressed, format=lzma.FORMAT_XZ)
    if len(raw) != obj["raw_bytes"] or sha256(raw) != obj["raw_sha256"]:
        raise ValueError(f"raw content-object mismatch: {name}")
    return raw


def reconstruct_text_parts(version: str) -> bytes:
    manifest = load_json(CONTENT / "TEXT_PARTS_MANIFEST.json")["technical"][version]
    out = bytearray()
    for part in manifest["parts"]:
        source_version = part.get("source_version", version)
        directory = V1510 if source_version == "15.10" else V1511
        path = directory / part["name"]
        raw = path.read_bytes()
        if len(raw) != part["bytes"] or sha256(raw) != part["sha256"]:
            raise ValueError(f"technical part mismatch: {part['name']}")
        out.extend(raw)
    data = bytes(out)
    if len(data) != manifest["output_bytes"] or sha256(data) != manifest["output_sha256"]:
        raise ValueError(f"technical reconstruction mismatch: {version}")
    return data


def verify_direct_sources(directory: Path, manifest: dict, version: str) -> None:
    for name, meta in manifest["primary_sources"].items():
        if name.startswith("GARDEN_CATALOGUE_"):
            continue
        if name.startswith("GARDEN_TECHNICAL_"):
            data = reconstruct_text_parts(version)
        else:
            data = (directory / name).read_bytes()
        if len(data) != meta["bytes"] or sha256(data) != meta["sha256"]:
            raise ValueError(f"direct source mismatch: {name}")


def reconstruct_catalogue_v1510() -> bytes:
    data = reconstruct_object("catalogue")
    manifest = load_json(V1510 / "RELEASE_MANIFEST_v15.10.json")
    meta = manifest["primary_sources"]["GARDEN_CATALOGUE_v15.10.txt"]
    if len(data) != meta["bytes"] or sha256(data) != meta["sha256"]:
        raise ValueError("v15.10 Catalogue manifest mismatch")
    return data


def reconstruct_catalogue_v1511() -> bytes:
    base = reconstruct_catalogue_v1510().decode("utf-8")
    base = base.replace("GARDEN v15.10\n", "GARDEN v15.11\n", 1)
    base = base.replace("Release: Garden v15.10\n", "Release: Garden v15.11 candidate\n", 1)
    end = "END OF GARDEN v15.10 — CATALOGUE\n"
    if not base.endswith(end):
        raise ValueError("unexpected v15.10 Catalogue end marker")
    delta = (V1511 / "GARDEN_CATALOGUE_v15.11_DELTA.txt").read_text(encoding="utf-8")
    data = (base[:-len(end)] + delta).encode("utf-8")
    manifest = load_json(V1511 / "RELEASE_MANIFEST_v15.11.json")
    meta = manifest["primary_sources"]["GARDEN_CATALOGUE_v15.11.txt"]
    if len(data) != meta["bytes"] or sha256(data) != meta["sha256"]:
        raise ValueError("v15.11 Catalogue manifest mismatch")
    return data


def materialize(version: str, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    if version == "15.10":
        manifest = load_json(V1510 / "RELEASE_MANIFEST_v15.10.json")
        verify_direct_sources(V1510, manifest, "15.10")
        for name in ("GARDEN_BOOK_v15.10.txt", "GARDEN_VERSION_HISTORY_v15.10.txt",
                     "CURRENT_READING_MAP_v15.10.json", "RELEASE_MANIFEST_v15.10.json",
                     "RETENTION_CLOSURE_RECEIPT_v15.10.json", "verify_v15.10_retention.py"):
            shutil.copyfile(V1510 / name, out / name)
        (out / "GARDEN_TECHNICAL_v15.10.txt").write_bytes(reconstruct_text_parts("15.10"))
        (out / "GARDEN_CATALOGUE_v15.10.txt").write_bytes(reconstruct_catalogue_v1510())
        (out / "SEMANTIC_RETENTION_DISPOSITION_v15.10.jsonl").write_bytes(
            reconstruct_object("retention_disposition")
        )
        return
    if version == "15.11":
        manifest = load_json(V1511 / "RELEASE_MANIFEST_v15.11.json")
        verify_direct_sources(V1511, manifest, "15.11")
        for name in ("GARDEN_BOOK_v15.11.txt", "GARDEN_VERSION_HISTORY_v15.11.txt",
                     "CLOSURE_RECEIPT_v15.11.json", "RELEASE_MANIFEST_v15.11.json", "verify_v15.11.py"):
            shutil.copyfile(V1511 / name, out / name)
        (out / "GARDEN_TECHNICAL_v15.11.txt").write_bytes(reconstruct_text_parts("15.11"))
        (out / "GARDEN_CATALOGUE_v15.11.txt").write_bytes(reconstruct_catalogue_v1511())
        return
    raise ValueError("version must be 15.10 or 15.11")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("version", choices=["15.10", "15.11"])
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    materialize(args.version, args.out)
    print(f"MATERIALIZED_GARDEN_{args.version}:{args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
