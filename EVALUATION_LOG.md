# Garden Public Evaluation Log

Garden treats external criticism, failed attacks, negative results and implementation failures as useful evidence. This log is a public index; the linked issues contain the detailed arguments and full-source triage.

No entry in this file is itself proof, certification, or a claim that an evaluator is independent merely because it is external.

## 2026-09-12 — launch-day external AI evaluations

### Audit synthesis #1 — issue #15

External AI systems attacked:

- shared-memory / prompt-injection privilege escalation;
- emergency-path manipulation and manufactured urgency;
- stale semantic dependencies and cached/flattened artifacts;
- multi-agent authority amplification across a delegation chain.

Full-source triage found that most of these failure classes already have explicit v15.5 safeguards, but the tests remain valuable as implementation regression fixtures.

**Residual canonical issue found:** `EMG-003` in the Annexure used a universal `>=2 independent sensors` formulation while the Technical emergency detector specifies hazard/profile-specific source-diversity requirements and explicitly rejects a universal sensor count. This is tracked for successor normalization.

Detailed record: issue #15.

The authority-amplification attack is also preserved as a public postmortem in `docs/evaluations/001-authority-amplification.md` and as an executable regression test under `tests/adversarial/`.

### Audit synthesis #2 — issue #16

An external AI reviewer argued that Garden's hard-gate conjunction lacked a non-physical enforcement substrate and that consent authentication could be mistaken for proof of informed/voluntary consent.

Full-source triage found that v15.5 already specifies:

- an External Deterministic Action Gate outside the cognitive proposer;
- protected execution privilege rings;
- explicit point-of-use authority/revocation checks;
- protected root/checker boundaries.

**Residual hardening opportunity:** make the epistemic limits of consent validity more explicit so that authentication/signature can never be treated as sufficient proof of voluntariness or comprehension when those properties are required.

Detailed record: issue #16.

### Next-successor candidate — issue #17

Issue #17 records two candidate hardening items without modifying the published v15.5 release:

1. emergency-source independence normalization and common-mode/manufactured-urgency tests;
2. a typed consent-validity assessment that preserves UNKNOWN/INCONCLUSIVE states and separates authentication from voluntariness/comprehension.

It also preserves the strongest external challenge scenarios as future executable regression tests.

## Executable regression status

A non-certified reference harness now exists under `prototype/` and `tests/adversarial/` for:

- stale policy/DesignEpoch handling;
- delegation-chain authority amplification;
- shared-memory/untrusted-context escalation for high-impact action;
- signed delegation receipt mutation/expiry checks.

These tests increase falsifiability; they do not constitute production security proof or deployment certification.

## How to add an evaluation

Start with `ATTACK_SURFACE.md`, `EVALUATE_IN_60_MINUTES.md`, or issue #10.

A useful report states:

- claim/mechanism;
- coverage and exact source anchors;
- executable test/prototype coverage where applicable;
- failure/counterexample or negative result;
- severity;
- existing mitigation checked;
- proposed fix or stronger alternative;
- reproducible test;
- uncertainty and what would overturn the conclusion.

If you cannot inspect a large canonical file because of tool/fetch limits, say so explicitly. Do not turn a coverage limit into an absence claim.

## Evaluation status vocabulary

- **UNTRIAGED** — received but not yet compared against the full source.
- **ALREADY_COVERED** — the claimed missing mechanism is explicitly present; keep the scenario if it improves testing.
- **IMPLEMENTATION_TEST** — architecture exists, but an executable implementation must prove it works.
- **DOCUMENTATION_GAP** — mechanism exists but is too difficult to discover or is described ambiguously.
- **CANONICAL_HARDENING** — a real specification clarification/normalization is warranted.
- **ARCHITECTURAL_DEFECT** — a required mechanism is missing or structurally insufficient.
- **EMPIRICAL_OPEN** — cannot be resolved from source semantics; measurement/experiment is required.

Garden should publish both successful falsifications and serious failed attacks.
