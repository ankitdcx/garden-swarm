"""Fail-closed contract for challenger-only Garden review evidence.

This module does not call providers. It validates whether a proposed challenger
record is allowed to exist alongside an unavailable required reviewer slot.
"""
from __future__ import annotations

def validate_challenger_admission(*, explicit_human_authorization: bool,
                                  required_slot_transport_state: str,
                                  public_source_bound: bool,
                                  peer_answers_hidden: bool,
                                  cost_ceiling_usd: float) -> dict:
    if explicit_human_authorization is not True:
        raise ValueError("challenger requires explicit human authorization")
    if required_slot_transport_state != "QUALIFIED_BUT_UNAVAILABLE":
        raise ValueError("challenger lane requires unavailable qualified slot")
    if public_source_bound is not True:
        raise ValueError("challenger requires exact public source binding")
    if peer_answers_hidden is not True:
        raise ValueError("challenger must remain blind to peer answers")
    if cost_ceiling_usd > 0.01:
        raise ValueError("challenger exceeds active per-call ceiling")
    return {
        "evidence_class": "CHALLENGER_ONLY",
        "satisfies_required_slot": False,
        "satisfies_independent_convergence": False,
        "semantic_delta_admitted": False,
    }
