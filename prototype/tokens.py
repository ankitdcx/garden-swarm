from __future__ import annotations

import base64
import json
import time
from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256

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


class ReceiptValidationStatus(str, Enum):
    VALID = "VALID"
    INVALID_SIGNATURE_OR_PAYLOAD = "INVALID_SIGNATURE_OR_PAYLOAD"
    EXPIRED = "EXPIRED"
    ISSUER_MISMATCH = "ISSUER_MISMATCH"
    SUBJECT_MISMATCH = "SUBJECT_MISMATCH"
    CAPABILITY_NOT_DELEGATED = "CAPABILITY_NOT_DELEGATED"
    PARENT_RECEIPT_REQUIRED = "PARENT_RECEIPT_REQUIRED"
    PARENT_DIGEST_MISMATCH = "PARENT_DIGEST_MISMATCH"
    ISSUER_NOT_PARENT_SUBJECT = "ISSUER_NOT_PARENT_SUBJECT"
    CAPABILITY_AMPLIFICATION = "CAPABILITY_AMPLIFICATION"
    EXPIRY_AMPLIFICATION = "EXPIRY_AMPLIFICATION"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ReceiptValidationResult:
    status: ReceiptValidationStatus
    receipt: DelegationReceipt | None
    reasons: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return self.status is ReceiptValidationStatus.VALID


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


def validate_receipt(
    public_key: Ed25519PublicKey,
    signed: dict[str, str],
    *,
    now: int | None = None,
    required_capability: str | None = None,
    expected_subject: str | None = None,
    expected_issuer: str | None = None,
    expected_parent: DelegationReceipt | None = None,
) -> ReceiptValidationResult:
    """Typed delegation receipt validation.

    Signature validity proves only that the supplied public key signed the payload.
    Expected issuer/subject/capability and parent binding remain explicit. Validation
    never grants authority beyond the validated receipt and its parent chain.
    """
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
        return ReceiptValidationResult(
            ReceiptValidationStatus.INVALID_SIGNATURE_OR_PAYLOAD,
            None,
            ("INVALID_SIGNATURE_OR_PAYLOAD",),
        )

    current_time = int(time.time()) if now is None else now
    if receipt.expires_at <= current_time:
        return ReceiptValidationResult(ReceiptValidationStatus.EXPIRED, receipt, ("EXPIRED",))
    if expected_issuer is not None and receipt.issuer != expected_issuer:
        return ReceiptValidationResult(ReceiptValidationStatus.ISSUER_MISMATCH, receipt, ("ISSUER_MISMATCH",))
    if expected_subject is not None and receipt.subject != expected_subject:
        return ReceiptValidationResult(ReceiptValidationStatus.SUBJECT_MISMATCH, receipt, ("SUBJECT_MISMATCH",))
    if required_capability is not None and required_capability not in receipt.capabilities:
        return ReceiptValidationResult(
            ReceiptValidationStatus.CAPABILITY_NOT_DELEGATED,
            receipt,
            ("CAPABILITY_NOT_DELEGATED",),
        )
    if receipt.parent_digest is not None and expected_parent is None:
        return ReceiptValidationResult(
            ReceiptValidationStatus.PARENT_RECEIPT_REQUIRED,
            receipt,
            ("PARENT_RECEIPT_REQUIRED",),
        )

    if expected_parent is not None:
        expected_digest = receipt_digest(expected_parent)
        if receipt.parent_digest != expected_digest:
            return ReceiptValidationResult(
                ReceiptValidationStatus.PARENT_DIGEST_MISMATCH,
                receipt,
                ("PARENT_DIGEST_MISMATCH",),
            )
        if receipt.issuer != expected_parent.subject:
            return ReceiptValidationResult(
                ReceiptValidationStatus.ISSUER_NOT_PARENT_SUBJECT,
                receipt,
                ("ISSUER_NOT_PARENT_SUBJECT",),
            )
        if not set(receipt.capabilities).issubset(set(expected_parent.capabilities)):
            return ReceiptValidationResult(
                ReceiptValidationStatus.CAPABILITY_AMPLIFICATION,
                receipt,
                ("CAPABILITY_AMPLIFICATION",),
            )
        if receipt.expires_at > expected_parent.expires_at:
            return ReceiptValidationResult(
                ReceiptValidationStatus.EXPIRY_AMPLIFICATION,
                receipt,
                ("EXPIRY_AMPLIFICATION",),
            )

    return ReceiptValidationResult(
        ReceiptValidationStatus.VALID,
        receipt,
        ("VALID_FOR_DECLARED_SCOPE",),
    )


def verify_receipt(
    public_key: Ed25519PublicKey,
    signed: dict[str, str],
    *,
    now: int | None = None,
    required_capability: str | None = None,
    expected_subject: str | None = None,
    expected_issuer: str | None = None,
    expected_parent: DelegationReceipt | None = None,
) -> tuple[bool, str, DelegationReceipt | None]:
    """Deprecated compatibility adapter around :func:`validate_receipt`.

    New Garden/GSL callers should consume ReceiptValidationResult directly so
    distinct terminal states are not laundered into one False value.
    """
    result = validate_receipt(
        public_key,
        signed,
        now=now,
        required_capability=required_capability,
        expected_subject=expected_subject,
        expected_issuer=expected_issuer,
        expected_parent=expected_parent,
    )
    return result.valid, result.reasons[0], result.receipt
