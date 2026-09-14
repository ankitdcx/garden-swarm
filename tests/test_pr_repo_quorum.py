from __future__ import annotations

from tools.pr_repo_quorum import validate_blind, validate_final


def model():
    return {"family": "test-family", "model": "example/test:free", "role": "adversary"}


def target():
    return {"full_diff_sha256": "a" * 64}


def test_blind_review_requires_compact_typed_fields():
    value = {
        "disposition": "NO_CHANGE",
        "claim": "bounded claim",
        "falsification": "counterexample attempt",
        "proposed_delta": "NO_CHANGE",
        "do_nothing": "prefer current design",
        "evidence_ancestry": "supplied diff only",
        "uncertainty": "bounded evidence",
    }
    row = validate_blind(value, model(), target())
    assert row["target_hash"] == "a" * 64
    assert row["reviewer_family"] == "test-family"


def test_final_review_requires_cross_exam_terminal():
    value = {
        "final_disposition": "REJECT_PROPOSAL",
        "surviving_claim": "none",
        "peer_challenges": ["counterexample"],
        "correlated_evidence": ["common diff"],
        "recommended_delta": "NO_CHANGE",
        "required_tests": [],
        "uncertainty": "low",
    }
    row = validate_final(value, model(), target())
    assert row["final_disposition"] == "REJECT_PROPOSAL"


def test_invalid_terminal_fails_closed():
    value = {
        "disposition": "ALLOW",
        "claim": "x",
        "falsification": "x",
        "proposed_delta": "x",
        "do_nothing": "x",
        "evidence_ancestry": "x",
        "uncertainty": "x",
    }
    try:
        validate_blind(value, model(), target())
    except ValueError:
        return
    raise AssertionError("invalid disposition must fail closed")
