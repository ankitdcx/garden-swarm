#!/usr/bin/env python3
"""Exhaustive finite model; stdlib only; does not prove the Rust implementation.

Run: python3 garden-tests/formal_model.py

Bound: 4 principal IDs (predecessor, peer, successor, unknown), 2 atomic scopes,
3 grant slots, 3 time points, 2 policy versions, 2 authority epochs, 2 request
IDs, and at most 1 pending permit. Root authority is externally provisioned;
only its two descendants may be issued. Administrative changes are trusted.

``validated`` abstracts the conjunction of exact request binding, independent
attestation admission, certainty, and discharged effect obligations. False
values always deny. Cryptographic signatures, evidence truth, OS separation,
resource exhaustion, crash recovery, and unbounded liveness are not modeled.

Requests with validated=False are an exact state-transition equivalence class
per request ID: their other fields cannot affect admission or the resulting
state. The explorer visits one representative of each such class. All 128 raw
request values are checked against this quotient in check_quotient().
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass, replace
from itertools import product
import json
import time


@dataclass(frozen=True, slots=True)
class Grant:
    recipient: int
    issuer: int
    parent: int
    scope: int
    expires: int
    policy: int
    epoch: int


@dataclass(frozen=True, slots=True)
class Request:
    request_id: int
    principal: int
    scope: int
    policy: int
    epoch: int
    validated: bool


@dataclass(frozen=True, slots=True)
class State:
    now: int = 0
    policy: int = 0
    epoch: int = 0
    upgraded: bool = False
    grants: tuple[Grant, ...] = (Grant(0, -1, -1, 3, 2, 0, 0),)
    revoked: int = 0
    spent: int = 0
    effects: int = 0
    pending: Request | None = None


@dataclass(frozen=True, slots=True)
class Event:
    kind: str
    allowed: bool = False
    request: Request | None = None
    grant: Grant | None = None
    receipt: bool = True
    effect: bool = False
    detail: str = ""


class Counterexample(AssertionError):
    def __init__(self, invariant: str):
        super().__init__(invariant)
        self.invariant = invariant


VALID_REQUESTS = tuple(Request(*values, True) for values in product(
    range(2), range(4), (1, 2), range(2), range(2)))
INVALID_REPRESENTATIVES = tuple(Request(i, 0, 1, 0, 0, False) for i in range(2))
QUOTIENT_REQUESTS = VALID_REQUESTS + INVALID_REPRESENTATIVES
RAW_REQUESTS = tuple(Request(*values) for values in product(
    range(2), range(4), (1, 2), range(2), range(2), (False, True)))


def reference_scope(state: State, index: int) -> int:
    """Independent recursive specification of a live ancestry chain."""
    def walk(node: int, visiting: frozenset[int]) -> int:
        if node in visiting or not 0 <= node < len(state.grants):
            return 0
        grant = state.grants[node]
        if (state.revoked & (1 << node) or state.now >= grant.expires
                or grant.policy != state.policy or grant.epoch != state.epoch):
            return 0
        if node == 0:
            return grant.scope if grant.parent == -1 and grant.issuer == -1 else 0
        parent_scope = walk(grant.parent, visiting | {node})
        if not parent_scope:
            return 0
        parent = state.grants[grant.parent]
        if (grant.issuer != parent.recipient or grant.expires > parent.expires
                or grant.scope & ~parent_scope):
            return 0
        return grant.scope
    return walk(index, frozenset())


def reference_authorized(state: State, request: Request) -> bool:
    if (not request.validated or request.policy != state.policy
            or request.epoch != state.epoch or request.principal == 3
            or request.principal == 0 and state.upgraded
            or request.principal == 2 and not state.upgraded):
        return False
    effective = 0
    for index, grant in enumerate(state.grants):
        if grant.recipient == request.principal:
            effective |= reference_scope(state, index)
    return bool(effective & request.scope)


def implementation_authorized(state: State, request: Request, mutation: str) -> bool:
    """A deliberately separate iterative transition rule with fault switches."""
    if not request.validated and mutation != "uncertainty_passes":
        return False
    if mutation != "ignore_version" and request.policy != state.policy:
        return False
    if mutation != "ignore_epoch" and request.epoch != state.epoch:
        return False
    principal = request.principal
    if principal == 2 and state.upgraded and mutation == "inherit_successor":
        principal = 0
    elif principal == 0 and state.upgraded or principal == 2 and not state.upgraded:
        return False
    for leaf, grant in enumerate(state.grants):
        if grant.recipient != principal or not grant.scope & request.scope:
            continue
        seen: set[int] = set()
        index = leaf
        valid = True
        while index != -1:
            if index in seen or not 0 <= index < len(state.grants):
                valid = False
                break
            seen.add(index)
            current = state.grants[index]
            if (state.revoked & (1 << index)
                    and (mutation != "ignore_ancestor_revocation" or index == leaf)):
                valid = False
                break
            if mutation != "ignore_expiry" and state.now >= current.expires:
                valid = False
                break
            if mutation != "ignore_version" and current.policy != state.policy:
                valid = False
                break
            if mutation != "ignore_epoch" and current.epoch != state.epoch:
                valid = False
                break
            if index:
                if not 0 <= current.parent < len(state.grants):
                    valid = False
                    break
                parent = state.grants[current.parent]
                if (current.issuer != parent.recipient
                        or current.expires > parent.expires
                        or current.scope & ~parent.scope):
                    valid = False
                    break
            elif current.parent != -1 or current.issuer != -1:
                valid = False
                break
            index = current.parent
        if valid:
            return True
    return False


def grant_is_attenuated(state: State, grant: Grant) -> bool:
    if not 0 <= grant.parent < len(state.grants):
        return False
    parent = state.grants[grant.parent]
    return (bool(reference_scope(state, grant.parent))
            and grant.issuer == parent.recipient
            and not grant.scope & ~parent.scope
            and state.now < grant.expires <= parent.expires
            and grant.policy == state.policy and grant.epoch == state.epoch)


def transitions(state: State, mutation: str):
    if state.now < 2:
        yield replace(state, now=state.now + 1), Event("advance_time")
    if state.policy == 0:
        yield replace(state, policy=1), Event("trusted_policy_update")
    if state.epoch == 0:
        yield replace(state, epoch=1), Event("trusted_authority_epoch_update")
    if not state.upgraded:
        yield replace(state, upgraded=True), Event("upgrade_without_grant")
    for index in range(len(state.grants)):
        if not state.revoked & (1 << index):
            yield replace(state, revoked=state.revoked | (1 << index)), Event(
                "revoke", detail=f"grant={index}")
    if len(state.grants) < 3:
        # New records can only reference existing records. Own/future/unknown
        # parent pointers are nevertheless submitted as denial test inputs.
        slot = len(state.grants)
        recipient, issuer = (1, 0) if slot == 1 else (0, 1)
        for parent, scope, expires in product(range(slot + 2), (1, 2, 3), (1, 2)):
            grant = Grant(recipient, issuer, parent, scope, expires,
                          state.policy, state.epoch)
            allowed = grant_is_attenuated(state, grant)
            if mutation == "widen_delegation" and 0 <= parent < slot:
                p = state.grants[parent]
                allowed = (bool(reference_scope(state, parent))
                           and issuer == p.recipient
                           and state.now < expires <= p.expires)
            nxt = replace(state, grants=state.grants + (grant,)) if allowed else state
            yield nxt, Event("delegate", allowed=allowed, grant=grant)
    if state.pending is None:
        for request in QUOTIENT_REQUESTS:
            bit = 1 << request.request_id
            replay = bool(state.spent & bit)
            allowed = (not replay or mutation == "allow_replay") and \
                implementation_authorized(state, request, mutation)
            nxt = replace(state, spent=state.spent | bit,
                          pending=request if allowed else None)
            yield nxt, Event("admit", allowed, request,
                             receipt=mutation != "omit_receipt" or not allowed)
    else:
        request = state.pending
        allowed = mutation == "skip_final_recheck" or \
            implementation_authorized(state, request, mutation)
        effects = state.effects | (1 << request.request_id) if allowed else state.effects
        yield replace(state, pending=None, effects=effects), Event(
            "execute", allowed, request, effect=allowed)


def check_transition(before: State, after: State, event: Event):
    if not event.receipt:
        raise Counterexample("every_decision_has_receipt")
    if after.effects & ~after.spent:
        raise Counterexample("effect_requires_consumed_request")
    if event.kind == "delegate" and event.allowed:
        if not grant_is_attenuated(before, event.grant):
            raise Counterexample("scope_expiry_issuer_and_ancestry_attenuation")
    if event.kind == "admit":
        request = event.request
        bit = 1 << request.request_id
        if not after.spent & bit:
            raise Counterexample("denied_identifiers_are_consumed")
        if event.allowed and before.spent & bit:
            raise Counterexample("no_replayed_admission")
        if event.allowed and not reference_authorized(before, request):
            raise Counterexample("admission_requires_current_bounded_authority")
        expected = not before.spent & bit and reference_authorized(before, request)
        if event.allowed != bool(expected):
            raise Counterexample("admission_matches_default_deny_specification")
    if event.effect:
        request = event.request
        if before.pending != request:
            raise Counterexample("effect_requires_exact_admitted_request")
        if not reference_authorized(before, request):
            raise Counterexample("effect_requires_final_current_authority")
        if before.effects & (1 << request.request_id):
            raise Counterexample("at_most_one_effect_per_request_id")
    if after.pending is not None and not after.spent & (1 << after.pending.request_id):
        raise Counterexample("pending_permit_requires_consumed_request")


def describe(event: Event) -> dict:
    result = {"action": event.kind, "allowed": event.allowed}
    if event.request is not None:
        result["request"] = {name: getattr(event.request, name) for name in (
            "request_id", "principal", "scope", "policy", "epoch", "validated")}
    if event.grant is not None:
        result["grant"] = {name: getattr(event.grant, name) for name in (
            "recipient", "issuer", "parent", "scope", "expires", "policy", "epoch")}
    if event.detail:
        result["detail"] = event.detail
    return result


def explore(mutation: str = "none", stop_at: int | None = None) -> dict:
    initial = State()
    queue = deque([initial])
    # Parent pointers retain shortest witnesses; full traces are constructed only
    # when a safety violation occurs.
    seen: dict[State, tuple[State, Event] | None] = {initial: None}
    transition_count = 0
    while queue:
        before = queue.popleft()
        for after, event in transitions(before, mutation):
            transition_count += 1
            try:
                check_transition(before, after, event)
            except Counterexample as error:
                path = [describe(event)]
                cursor = before
                while seen[cursor] is not None:
                    predecessor, earlier = seen[cursor]
                    path.append(describe(earlier))
                    cursor = predecessor
                path.reverse()
                return {"status": "counterexample", "mutation": mutation,
                        "invariant": error.invariant, "states": len(seen),
                        "transitions": transition_count, "witness": path}
            if after not in seen:
                seen[after] = (before, event)
                queue.append(after)
                if stop_at is not None and len(seen) >= stop_at:
                    return {"status": "bounded_prefix_only", "states": len(seen),
                            "transitions": transition_count}
    return {"status": "all_reachable_states_checked", "states": len(seen),
            "transitions": transition_count}


def check_quotient() -> dict:
    # For all raw requests with failed validation, the guard denies before any
    # identity/scope/version field is inspected and transition effects depend only
    # on the ID. Test all other environment coordinates and replay possibilities.
    checked = 0
    for now, policy, epoch, upgraded, spent in product(
            range(3), range(2), range(2), (False, True), range(4)):
        state = replace(State(), now=now, policy=policy, epoch=epoch,
                        upgraded=upgraded, spent=spent)
        for request in RAW_REQUESTS:
            if request.validated:
                continue
            representative = INVALID_REPRESENTATIVES[request.request_id]
            assert not implementation_authorized(state, request, "none")
            assert not reference_authorized(state, request)
            assert replace(state, spent=state.spent | (1 << request.request_id)) == \
                replace(state, spent=state.spent | (1 << representative.request_id))
            checked += 1
    return {"raw_request_values": len(RAW_REQUESTS),
            "transition_equivalence_classes": len(QUOTIENT_REQUESTS),
            "equivalence_checks": checked}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-negative-controls", action="store_true")
    parser.add_argument("--prefix-states", type=int, help="debug only; never a full proof")
    args = parser.parse_args()
    started = time.monotonic()
    quotient = check_quotient()
    positive = explore(stop_at=args.prefix_states)
    controls = []
    if not args.skip_negative_controls and args.prefix_states is None:
        for mutation in ("widen_delegation", "ignore_ancestor_revocation",
                         "ignore_version", "ignore_epoch", "ignore_expiry",
                         "inherit_successor", "allow_replay", "skip_final_recheck",
                         "uncertainty_passes", "omit_receipt"):
            controls.append(explore(mutation))
    ok = positive["status"] == "all_reachable_states_checked" and all(
        item["status"] == "counterexample" for item in controls)
    report = {
        "model": "bounded delegation, admission, and effect transition model",
        "implementation_proof": False,
        "bounds": {"principals": 4, "atomic_scopes": 2, "grant_slots": 3,
                   "time_points": 3, "policy_versions": 2, "authority_epochs": 2,
                   "request_ids": 2, "pending_permits": 1},
        "request_quotient": quotient,
        "positive": positive,
        "negative_controls": controls,
        "passed": ok,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "limitations": ["finite abstraction, not a Rust refinement proof",
                        "trusted validation represented by a Boolean",
                        "receipt presence only, not cryptographic integrity",
                        "no OS isolation, crash recovery, availability, or liveness proof"]}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
