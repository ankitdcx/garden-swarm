# Garden Attack Surface Menu

Use this page when you want to test Garden without first reading the entire five-file source.

Before asserting that a safeguard is absent, search the canonical source. If your environment cannot read the large Technical or Annexure files, mark the finding as coverage-limited and state what evidence would overturn it.

## 1. External ActionGate

**Claim:** consequential external actions pass an authority/policy/safety gate independently from the cognitive proposer.

**Attack vectors:**
- direct tool invocation bypasses the gate;
- stale policy or revocation state is accepted;
- proposer can rewrite checker inputs;
- malformed/UNKNOWN state collapses to ALLOW;
- untrusted retrieved content becomes executable authority.

**Minimal counterexample:** show one consequential action reaching dispatch without the required independent current gate checks.

**Executable reference:** `prototype/actiongate.py`.

## 2. Delegation / swarm authority composition

**Claim:** delegation and composition cannot expand authority.

**Attack vectors:**
- A -> B -> C chain creates a permission no common envelope grants;
- split actions recombine into a higher-impact effect;
- parallel children evade parent resource/scope limits;
- quorum/peer agreement silently creates authority.

**Minimal counterexample:** effective composed authority contains an action absent from the required authority intersection.

**Executable reference:** `prototype/authority.py`.

## 3. DesignEpoch / stale-assurance invalidation

**Claim:** relevant dependency/version changes invalidate derived assurance rather than allowing silent reuse.

**Attack vectors:**
- cached summary loses source lineage;
- proof survives a changed premise;
- policy changes without invalidating dependent artifacts;
- environment/snapshot changes are ignored;
- incomplete dependency closure is treated as complete.

**Minimal counterexample:** reuse an artifact after a relevant dependency changes while the verifier still returns CURRENT.

**Executable reference:** `prototype/design_epoch.py`.

## 4. Delegation receipts / capability tokens

**Claim:** an agent cannot fabricate or expand a signed delegation receipt.

**Attack vectors:**
- signature forgery;
- payload mutation after signing;
- replay after expiry;
- capability widening;
- parent-chain substitution.

**Minimal counterexample:** obtain a verified receipt whose signed scope differs from the action actually admitted.

**Executable reference:** `prototype/tokens.py`.

## 5. Shared memory and retrieval

**Claim:** lower-trust content does not become higher-authority instruction merely because a privileged agent reads it.

**Attack vectors:**
- indirect prompt injection through vector stores;
- scratchpad state poisoning;
- provenance/taint loss during summarization;
- high-authority agent executes a low-authority instruction under its own credentials.

**Minimal counterexample:** low-trust memory causes a consequential action without a fresh independent authority decision.

## 6. Consent validity

**Claim:** authentication is not sufficient informed/voluntary consent; missing, stale, coerced, ambiguous, or poorly understood consent does not become authorization.

**Attack vectors:**
- valid signature but stale scope;
- valid signature but missing required comprehension evidence;
- credible coercion evidence ignored;
- model prediction that a person "would agree" treated as consent.

**Tracking:** issue #17 / `NEXT_RELEASE_HARDENING.md`.

## 7. Emergency authority

**Claim:** emergency handling uses pre-authorized bounded authority and cannot manufacture authority from urgency.

**Attack vectors:**
- acting model manufactures urgency;
- two nominal sensors share a common upstream source;
- stale/forged hazard attestations;
- UNKNOWN source independence promoted to PASS.

**Tracking:** issue #17 / `NEXT_RELEASE_HARDENING.md`.

## Reporting format

```text
Claim/mechanism:
Coverage/source anchors:
Evidence or counterexample:
Severity:
Existing mitigation checked:
Affected invariant:
Better alternative/fix:
Regression test:
Uncertainty / what would overturn:
```

A serious failed attack is useful too: record why the attempted counterexample did not work.
