from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/mobile-relay", tags=["mobile-relay"])

_ENABLED = os.getenv("GARDEN_RELAY_ENABLED", "").strip() == "1"
_PUBLIC_ONLY = os.getenv("GARDEN_RELAY_PUBLIC_ONLY", "1").strip() == "1"
_DEVICE_TOKEN = os.getenv("GARDEN_RELAY_DEVICE_TOKEN", "").strip()
_RESULT_DIR = Path(os.getenv("GARDEN_RELAY_RESULT_DIR", "/tmp/garden-relay")).resolve()
_SAFE = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")


class RelayResultInput(BaseModel):
    schema: str = Field(default="GardenRelayUpload/v1")
    job_id: str = Field(min_length=1, max_length=160)
    slot: str = Field(min_length=1, max_length=64)
    payload_b64: str = Field(min_length=1, max_length=8_000_000)
    payload_sha256: str = Field(min_length=64, max_length=64)
    kind: str = Field(default="SHARED_RESULT", max_length=80)
    data_classification: str = Field(default="PUBLIC", max_length=32)
    receipt_capability: str = Field(min_length=32, max_length=256)
    client_received_utc: str = Field(default="", max_length=80)


def _require_enabled() -> None:
    if not _ENABLED:
        raise HTTPException(status_code=404, detail="Mobile relay disabled")


def _safe(value: str, field: str) -> str:
    if not _SAFE.fullmatch(value):
        raise HTTPException(status_code=400, detail=f"Invalid {field}")
    return value


def _auth(authorization: str | None) -> None:
    _require_enabled()
    if not _DEVICE_TOKEN:
        raise HTTPException(status_code=503, detail="Relay device authentication unavailable")
    expected = f"Bearer {_DEVICE_TOKEN}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid relay device credential")


def _job_dir(job_id: str) -> Path:
    path = (_RESULT_DIR / _safe(job_id, "job_id")).resolve()
    try:
        path.relative_to(_RESULT_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid job path") from exc
    return path


def _slot_path(job_id: str, slot: str) -> Path:
    directory = _job_dir(job_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{_safe(slot, 'slot')}.json"


@router.get("/health")
def mobile_relay_health() -> dict[str, Any]:
    _require_enabled()
    return {
        "status": "ok",
        "public_only": _PUBLIC_ONLY,
        "storage": "EPHEMERAL_LOCAL_PROTOTYPE",
        "authority_effect": "NONE_TRANSPORT_ONLY",
    }


@router.post("/result")
def upload_result(
    result: RelayResultInput,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _auth(authorization)
    if result.schema != "GardenRelayUpload/v1":
        raise HTTPException(status_code=400, detail="Unsupported relay result schema")
    if _PUBLIC_ONLY and result.data_classification != "PUBLIC":
        raise HTTPException(status_code=403, detail="Relay accepts PUBLIC review material only")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", result.payload_sha256):
        raise HTTPException(status_code=400, detail="Invalid payload SHA-256")

    try:
        raw = base64.b64decode(result.payload_b64, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Base64 payload") from exc

    got = hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(got.lower(), result.payload_sha256.lower()):
        raise HTTPException(status_code=400, detail="Payload SHA-256 mismatch")

    if len(raw) > 5_000_000:
        raise HTTPException(status_code=413, detail="Payload too large")

    record = {
        "schema": "GardenRelayStoredResult/v1",
        "job_id": result.job_id,
        "slot": result.slot,
        "kind": result.kind,
        "data_classification": result.data_classification,
        "payload_sha256": got,
        "payload_bytes": len(raw),
        "payload_b64": base64.b64encode(raw).decode("ascii"),
        "receipt_capability_sha256": hashlib.sha256(result.receipt_capability.encode("utf-8")).hexdigest(),
        "client_received_utc": result.client_received_utc,
        "server_received_unix": int(time.time()),
        "authority_effect": "NONE_TRANSPORT_ONLY",
    }

    path = _slot_path(result.job_id, result.slot)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    temp.replace(path)

    return {
        "status": "stored",
        "job_id": result.job_id,
        "slot": result.slot,
        "payload_sha256": got,
        "payload_bytes": len(raw),
        "authority_effect": "NONE_TRANSPORT_ONLY",
    }


@router.get("/result/{job_id}/{slot}")
def fetch_result(job_id: str, slot: str, capability: str) -> dict[str, Any]:
    _require_enabled()
    path = _slot_path(job_id, slot)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Result not found")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Stored relay result unreadable") from exc
    got = hashlib.sha256(capability.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(got, str(record.get("receipt_capability_sha256", ""))):
        raise HTTPException(status_code=403, detail="Invalid result capability")
    return record
