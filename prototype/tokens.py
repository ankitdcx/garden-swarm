from __future__ import annotations

import base64
import json
import time
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Iterable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


@dataclass(frozen=True)
class DelegationReceipt:
    issuer: str
    subject: str
    capabilities: tuple[str, ...]
    expires_at: int
    nonce: str
    parent_digest: str | None = None


def _canonical_payload(receipt: DelegationReceipt) -> bytes:
    payload = asdict(receipt)
    payload["capabilities"] = sorted(set(payload["capabilities"]))
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def receipt_digest(receipt: DelegationReceipt) -> str:
    return sha256(_canonical_payload(receipt)).hexdigest()


def sign_receipt(private_key: Ed25519PrivateKey, receipt: DelegationReceipt) -> dict[str, str]:
    payload = _canonical_payload(receipt)
    signature = private_key.sign(payload)
    return {
        "payload": base64.urlsafe_b64encode(payload).decode("ascii"),
        "signature": base64.urlsafe_b64encode(signature).decode("ascii"),
    }


def verify_receipt(
    public_key: Ed25519PublicKey,
    signed: dict[str, str],
    *,
    now: int | None = None,
    required_capability: str | None = None,
    expected_subject: str | None = None,
) -> tuple[bool, str, DelegationReceipt | None]:
    try:
        payload = base64.urlsafe_b64decode(signed["payload"].encode("ascii"))
        signature = base64.urlsafe_b64decode(signed["signature"].encode("ascii"))
        public_key.verify(signature, payload)
        decoded = json.loads(payload.decode("utf-8"))
        receipt = DelegationReceipt(
            issuer=decoded["issuer"],
            subject=decoded["subject"],
            capabilities=tuple(decoded["capabilities"]),
            expires_at=int(decoded["expires_at"]),
            nonce=decoded["nonce"],
            parent_digest=decoded.get("parent_digest"),
        )
    except (KeyError, ValueError, json.JSONDecodeError, InvalidSignature):
        return False, "INVALID_SIGNATURE_OR_PAYLOAD", None

    current_time = int(time.time()) if now is None else now
    if receipt.expires_at <= current_time:
        return False, "EXPIRED", receipt

    if expected_subject is not None and receipt.subject != expected_subject:
        return False, "SUBJECT_MISMATCH", receipt

    if required_capability is not None and required_capability not in receipt.capabilities:
        return False, "CAPABILITY_NOT_DELEGATED", receipt

    return True, "VALID_FOR_DECLARED_SCOPE", receipt
