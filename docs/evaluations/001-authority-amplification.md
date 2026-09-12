---
title: Evaluation 001 — Authority Amplification
---

# Evaluation 001 — Multi-Agent Authority Amplification

## Attack

An external evaluator proposed a three-agent chain:

- Agent A may only suggest.
- Agent B may evaluate/use low-impact tools.
- Agent C may execute a high-impact action when receiving an evaluated request.

The proposed failure was that each local step could appear individually authorized while the composed A -> B -> C path produced authority no participant should have been able to create.

## Initial severity claim

**HIGH** if Garden only checked local/node authority and did not constrain composed paths.

## Full-source triage

The full v15.5 source already contains the relevant anti-amplification semantics:

- `SwarmCoord` constrains actions by the intersection of sub-agent, swarm and principal authority/token scope.
- `CapabilityCompositionProof` preserves the intersection of principal authority, token scope, agent envelope and policy.
- `MAC-001` states that collective authority cannot exceed the valid intersection or be amplified by delegation/quorum.
- `TEST-MAC-001/002` cover authority-amplification cases.

Therefore the original absence claim did **not** survive full-source review.

## Why the evaluation was still useful

The evaluator produced a concrete, implementation-ready adversarial fixture. Garden now preserves the scenario in executable form under:

- `prototype/authority.py`
- `tests/adversarial/test_known_attacks.py`

The reference test constructs an A -> B -> C chain and asserts that `execute_high` is rejected when it is not in the common authority intersection.

## Lesson

A failed attack is valuable when it becomes a regression test.

This evaluation also exposed a process requirement for future reviewers: **do not infer absence from summary files alone**. If large canonical files cannot be fetched, mark the finding as coverage-limited and state what evidence would overturn it.

## Current status

- architectural gap: **NOT CONFIRMED**;
- executable regression fixture: **ADDED**;
- production/runtime proof: **PENDING**;
- deployment certification: **PENDING**.

This document is an evaluation record, not a replacement for canonical Garden semantics.
