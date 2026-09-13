from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from prototype.tokens import (
    DelegationReceipt,
    ReceiptValidationStatus,
    sign_receipt,
    validate_receipt,
)


def test_validate_receipt_preserves_typed_terminal_states():
    private = Ed25519PrivateKey.generate()
    receipt = DelegationReceipt(
        issuer="human:alice",
        subject="agent:A",
        capabilities=("notify",),
        expires_at=2_000_000_000,
        nonce="typed-1",
    )
    signed = sign_receipt(private, receipt)

    valid = validate_receipt(
        private.public_key(),
        signed,
        now=1_900_000_000,
        expected_issuer="human:alice",
        expected_subject="agent:A",
        required_capability="notify",
    )
    assert valid.status is ReceiptValidationStatus.VALID
    assert valid.valid is True

    expired = validate_receipt(private.public_key(), signed, now=2_100_000_000)
    assert expired.status is ReceiptValidationStatus.EXPIRED
    assert expired.valid is False

    mismatch = validate_receipt(
        private.public_key(), signed, now=1_900_000_000, expected_issuer="human:bob"
    )
    assert mismatch.status is ReceiptValidationStatus.ISSUER_MISMATCH
    assert mismatch.valid is False


def test_bool_is_only_a_derived_convenience_predicate():
    private = Ed25519PrivateKey.generate()
    receipt = DelegationReceipt(
        issuer="human:alice",
        subject="agent:A",
        capabilities=("notify",),
        expires_at=2_000_000_000,
        nonce="typed-2",
    )
    result = validate_receipt(private.public_key(), sign_receipt(private, receipt), now=1_900_000_000)
    assert result.status is ReceiptValidationStatus.VALID
    assert isinstance(result.valid, bool)
