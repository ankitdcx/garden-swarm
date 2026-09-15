# Garden Continuous Upgrade Process v2 (candidate)

Status: protected process candidate. Review under the predecessor process. Canonical Garden v15.5 is unchanged.

## Eight stages

1. **Observe / Discover** — inspect repo state, incidents, failed CI, open repair obligations, design coverage and new public research. Research may emit `CANDIDATE_ALTERNATIVE`; it may not declare an alternative better.
2. **Packetize** — build one coherent-complete `GardenReviewPacket/v1` for one immutable `CycleID`. Canonical packet bytes have one SHA-256 `packet_hash` used by every blind reviewer.
3. **Blind Review** — all model/specialist reviewers see the same packet and no same-cycle peer findings. Same-base specialists add coverage, not independent-family count.
4. **Cross-Examine** — starts only after required blind findings complete for the same CycleID/packet_hash. Evidence is checked, not voted on.
5. **Build / Repair** — implement the smallest verified-value change. Non-semantic work may use LIGHT; semantic work uses DesignEpoch-bound deltas.
6. **Verify** — independently prove the original failure is gone and no regression or semantic drift was introduced.
7. **Successor / Promotion** — compose admitted deltas into a complete successor. Immutable predecessor remains untouched. Protected canonical promotion remains human-only.
8. **Pipeline Health / Hygiene** — audit lane health, repair backlog, branch/PR state, stale evidence, budgets, model yield and process complexity.

## Coherent-complete ReviewPacket

`PacketCompletenessReceipt/v1` passes only when:
- exact public/private repo commits in scope are bound, or inaccessibility is explicit;
- canonical version, DesignEpoch/source root and ProcessVersion are bound;
- the bounded target text, source hashes and anchors are included;
- each repo has a defined base/head diff or mechanically proven `NO_CHANGE`;
- changed files and mechanically derived changed symbols are included;
- dependency/reference closure and owner definitions are mechanically derived;
- affected schemas, FunctionContracts, invariants, tests, registries and implementation bindings are included;
- exact-head CI/test/environment evidence is included;
- active freezes and unresolved/reopened findings touching closure objects are linked;
- every exclusion has a machine-checkable reason; and
- the closure frontier shows that adding another object would leave the declared closure boundary.

Missing required material, ambiguous closure, stale binding or unexplained exclusion => `PACKET_INCOMPLETE`.

## State coherence

Clock schedules are watchdogs, not authority to advance. A cycle moves only through:

`PACKET_BUILDING -> PACKET_READY -> BLIND_REVIEW -> BLIND_REVIEW_COMPLETE -> CROSS_EXAM -> BUILDER_READY -> INTEGRATED -> POST_FIX_VERIFIED`

Slow cycles remain isolated. Adjacent CycleIDs may not mix evidence. If cycles accumulate, intake is throttled instead of dropping findings.

## Evidence classes

The producer assigns `claimed_evidence_class` and attaches the evidence object. A deterministic validator checks whether the evidence can support that class. Once validated, the class is immutable. Reclassification requires `EvidenceClassChallenge` with same-or-higher-class evidence.

- **E4** reproducible executable trace, bound to exact commit/DesignEpoch/environment/command/result.
- **E3** formal proof or machine-checkable contradiction with current premise bindings.
- **E2** authoritative exact source/code/schema evidence.
- **E1** reasoned argument.
- **E0** unsupported assertion.

Integrators may not silently relabel evidence through selective citation.

## Exact-head merge protocol

Use merge-queue / rebase-and-reverify semantics. If main moves after verification, the old exact-head evidence expires. Rebase/update onto current main, rebuild affected evidence, rerun required tests/checks, then merge. Never silently merge X-verified work onto Y. No force-push or gate bypass.

## Repair obligations and aging

Every verified defect becomes a typed `RepairObligation` with severity, first-seen cycle, age, attempts, blocker, exact affected objects, reproduction evidence, expected repair and tests.

- CRITICAL preempts ordinary upgrades.
- HIGH gains priority with age.
- MEDIUM also ages upward.
- `REPAIR_BACKLOG_PRESSURE` throttles new discovery/feature intake when repair debt exceeds policy thresholds.

Opening an issue, freezing work or getting model agreement is not a fix.

## Reviewer allocation

Primary yield signals are external outcomes: seeded-defect detection, independently `VERIFIED_FIXED` results, reproducible counterexamples, incident/regression attribution and false-positive rate. Challenger/cross-exam acceptance is secondary and capped. Preserve a fixed exploration/diversity share.

## Human availability

- `HUMAN_AVAILABLE`: normal operation.
- `HUMAN_TEMPORARILY_UNAVAILABLE`: protected promotion pauses; routine governed work continues; admitted-unpromoted semantic work is capped at one major-candidate batch (normally <=10 deltas unless already MAJOR). Beyond cap => `DEFERRED_PENDING_PROMOTION_CAPACITY`.
- `HUMAN_PERMANENTLY_UNAVAILABLE`: canonical promotion remains frozen until a separately admitted succession/continuity mechanism exists. Keep the same cap; already-authorized safety/correctness implementation against the last valid DesignEpoch may continue; issue a 90-day continuity-status review.

Protected authority is never silently transferred.

## Budgets

Routine public OpenRouter review keeps the existing ~USD 1/day ceiling. Expensive escalation uses a separate `EscalationBudget` and defaults to zero automatic spend unless explicitly pre-authorized.

## Process change control

Semantic changes to review independence, packet completeness, evidence rules, state transitions, merge/freeze rules, budgets, human authority, admission/promotion, pipeline-health semantics, or Process Algebra binding require a ProcessVersion bump. ProcessVersion N+1 is reviewed under N and cannot self-authorize. Pure implementation fixes preserving admitted process semantics may use the non-semantic track.

## Pipeline health

`PipelineHealthReceipt/v1` records, per lane: last successful cycle, attempts/completions, latency, missed/stale cycles, backlog, failure reasons, unresolved repairs, independently verified closures, false closures, stale evidence, packet-incomplete rate and health state `HEALTHY|DEGRADED|REDUCED_OPERATION|FAILED`.

No lane certifies its own closure counts. Unhealthy lanes reduce operation or fail closed until repaired.

## Simplification

Quarterly `PipelineSimplificationReview/v1` looks for zero-yield lanes, duplicate gates, rules that never fire, record types with no consumers, obsolete paths and high-cost/low-value checks. Removal is a first-class improvement. Rare but load-bearing safety/privacy/authority controls are not removed merely because they rarely fire.

## Garden Process Algebra binding

The upgrade pipeline is not a separate orchestration framework. It is a governed Garden Process Algebra instance bound to canonical `REG-ALGEBRA-001`, `[S-PROCESS]#5.1`, and `[S-PROCESS]#5.1B`.

Every update action must emit or reference a validated `GardenEvolutionAlgebraUsageReceipt/v1` and an `AlgebraBoundUpdateReceipt/v1`. These receipts describe operator use; they grant no authority and do not prove Garden certification.

The Process operators are used as follows:

- `SEQUENCE(A,B)` — ordered state transitions and gates.
- `PARALLEL({P_i})` — blind peer reviewers operating on one identical `packet_hash`.
- `COMPOSE(A,B)` — composition of validated stages without assuming extra algebra laws.
- `BRANCH(c,A,B)` — semantic-vs-LIGHT routing, pass-vs-repair routing, and target-kind routing.
- `RETRY(P,bound)` — bounded repair attempts.
- `ROLLBACK(P)` — reverse a failed governed integration or promoted successor when rollback policy permits.
- `COMPENSATE(P)` — remediate external side effects that cannot be erased by rollback.
- `RECONSTRUCT(x)` — rebuild process state only from bound evidence/receipts; reconstruction never recreates authority from untrusted history.
- `ITERATE(P,k)` — bounded continuous upgrade cycles.
- `RECURSE(P)` — nested dependency repair only under explicit termination/resource bounds.
- `TERMINATE(reason)` — stop on invalid authority, unresolved critical conflict, failed completeness, or exhausted safe retry bounds.
- `DO_NOTHING` — required valid result when no change has positive verified value.

No associativity, commutativity, idempotence, distributivity or reordering law is inferred unless canonically registered. In particular, parallel reviewer effects are **not** assumed commutative.

### One update process, three targets

All updates use the same algebraic control flow:

`Observe/Discover -> Packetize -> PARALLEL(blind review) -> Cross-Examine -> BRANCH(semantic, full semantic path, LIGHT path) -> Build/Repair -> Verify -> BRANCH(pass, target-specific integration, RETRY/ROLLBACK/TERMINATE) -> Post-Fix Verify -> ITERATE or DO_NOTHING`

The target-specific terminal rule is the only major difference:

1. `PUBLIC_REPO` — exact-head governed merge into the public repository.
2. `PRIVATE_IMPLEMENTATION` — exact-head governed merge into the private implementation repository.
3. `CANONICAL_DESIGN` — never edit the immutable predecessor; compose a complete successor candidate, then require separately protected human canonical promotion.

Policy Algebra applies only where a registered authority/approval operator is actually executed. Ordinary ActionGate checks must not be silently relabeled as Policy Algebra.

Conformance Algebra is required for requirement/reference/test/obligation closure and exact-head conformance. Decision and Evidence Algebra remain explicit `FRONTIER` where their executable operator signatures are not yet bound. Bridge Algebra is conditional and applies only when a registered semantic-to-representation transformation is actually invoked.

Therefore Process v2 is **algebra-bound by construction**, but it must continue to report `semantic_compliance_proved=false` until every required frontier for the action is closed and a valid algebra validation receipt exists. `FRONTIER` never counts as compliance.
