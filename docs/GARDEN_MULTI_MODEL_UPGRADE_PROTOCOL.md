# Garden Multi-Model Upgrade Protocol

Status: APPROVED OPERATIONAL DESIGN — implementation and executable closure in progress
Date: 2026-09-14
Scope: `garden-swarm`, `garden-main`, and Garden successor-design evolution
Authority boundary: this document defines the approved operational process. It does not by itself modify canonical Garden semantics, constitutional authority, HSA, or DesignEpoch. Protected changes remain human-gated.

> **2026-09-19 routing/process update:** the model roster, OpenRouter routing, review-round count, and cost controls in this older protocol are superseded for new OpenRouter work by `docs/OPENROUTER_PROCESS_V2_2026-09-19.md` and the active machine-readable policies under `agents/`. The broader evidence/authority principles in this document remain historical design background unless separately superseded.

## 1. Purpose

Garden continuously performs three distinct jobs:

1. Review `garden-swarm` and `garden-main` for correctness against the current canonical Garden/DesignEpoch.
2. Build and repair executable Garden code in `garden-main` and the review machinery in `garden-swarm`.
3. Accumulate verified Garden design improvements and materialize at most one normal successor candidate per Asia/Kolkata day; zero successor is a valid successful outcome.

These jobs share one evidence ledger but do not bypass one another.

## 2. Core epistemic rule

A claim's status is determined by independently verifiable evidence, not by vote, dissent, or model identity.

Where verified evidence conflicts, the conflict itself becomes a finding; the disputed claim remains UNRESOLVED and every mutation dependent upon it is frozen until resolution.

Unverified evidence may enter the ledger but cannot by itself determine the outcome.

## 3. Model roles

Routine independent board:

- ChatGPT / GPT-5.6 Sol: OpenAI-family blind reviewer; builder; primary integrator.
- DeepSeek: independent adversarial reasoning/code reviewer.
- Qwen: independent architecture/code reviewer.
- Gemini: independent Google-family reviewer.
- Approved free shadow model: optional additional reviewer when privacy policy permits.

Escalation only:

- Claude: difficult disagreement, high-stakes semantic or architectural challenge, final attack.
- Stronger Gemini: escalation where routine Gemini is insufficient.
- Kimi: large-repository/long-context implementation investigation.

OpenRouter spending should purchase non-OpenAI diversity; the ChatGPT lane is supplied separately.

Model agreement is not treated as proof. Reviewer-family independence, unique evidence, and unique arguments are tracked separately from raw reviewer count.

## 4. Human authority and delegation

Automation operates only inside a revocable `HumanDelegationEnvelope/v1`.

The envelope defines:

- allowed actions;
- prohibited actions;
- protected paths;
- protected semantics;
- auto-merge scope;
- auto-canonicalization scope;
- required human approval scope;
- emergency authority;
- privacy limits;
- spending limits;
- revocation method;
- human-unavailable behavior;
- expiry/review date.

Protected changes include at least HSA, governance, human authority, root/constitutional principles, major architectural replacement, federation/launch policy, and delegation-envelope changes.

Delegation cannot expand itself. Changes to the delegation envelope are themselves protected.

Human unavailability is represented by `HumanAvailabilityWindow/v1`. If no explicit window exists, use the declared human timezone (Asia/Kolkata unless superseded), assume ordinary availability for one business day, then transition to `HUMAN_UNAVAILABLE`. After three business days, transition to `HUMAN_EXTENDED_UNAVAILABLE`, generate a receipt, and notify using the declared contact mode. Routine delegated work may continue; protected or unclear-authority work pauses.

## 5. Hourly target selection

Target selection is event-driven first and deterministic-coverage second.

Priority order:

1. Immediate blockers: HIGH/CRITICAL unresolved finding, failed CI/test, active freeze, security/authority/HSA concern, regression, production incident.
2. Fresh changes: new code, repo machinery, design delta, or unreviewed change since the last cycle.
3. Pending valuable work: accepted finding awaiting implementation, incomplete contract/module, known architecture gap, stale candidate requiring verification.
4. Coverage rotation: deterministic rotation through Garden design modules, `garden-main` modules, and `garden-swarm` modules when nothing higher-priority exists.

Normal coverage rotation should ensure all three workstreams receive attention. A suggested fallback is:

- cycle A: `garden-main`;
- cycle B: canonical Garden design;
- cycle C: `garden-swarm`;
- repeat.

Within a queue, candidate priority is based on severity, dependency reach, uncertainty, recency, implementation importance, and time since last review, with a penalty for unchanged heavily reviewed areas.

The selected scope must remain bounded: selected module + changed files + mechanically derived dependency/reference closure + relevant contracts/invariants/tests + linked unresolved findings.

Periodic full-repository/full-design closure audits are required to catch defects outside incremental scope.

## 6. Mechanical ReviewPacket construction

ChatGPT or another model must not silently decide what reviewers see.

`ReviewPacket/v1` is mechanically derived from:

- exact repository commit(s);
- canonical version;
- DesignEpoch;
- git diff;
- changed files/symbols;
- static dependency closure;
- Garden reference closure;
- affected schemas/contracts/invariants/tests;
- CI/test results;
- linked unresolved/reopened findings;
- exact source hashes.

Any manual/model inclusion or exclusion requires `PacketConstructionDecision/v1` with object, INCLUDE|EXCLUDE, reason, actor, and evidence. The Challenger can audit those decisions.

An incomplete packet cannot produce review closure.

## 7. Privacy router

No external-model request may bypass the fail-closed privacy router.

Every outbound packet is classified:

- PUBLIC
- PRIVATE
- RESTRICTED

The router checks provider retention, training policy, ZDR capability, data-collection policy, and material-class allowance.

Result: ALLOW or DENY.

Unknown provider privacy status is DENY.

Every decision produces `RoutingReceipt/v1`.

Public/non-approved providers must never receive private `garden-main`, secrets, credentials, or private user material.

## 8. Budget governor

Use separate pools with hard caps and receipts:

- ROUTINE reviewer budget;
- CHALLENGER budget;
- ESCALATION budget;
- EMERGENCY_RESERVE.

The exact dollar split may be tuned empirically. The emergency reserve is restricted to CRITICAL escalation, emergency-successor verification, or restoration of a frozen critical path.

If ROUTINE is exhausted: ChatGPT + approved free reviewers may continue; paid routine reviewers stop.

If CHALLENGER is exhausted: high-risk decisions requiring Challenger review do not silently proceed.

If ESCALATION is exhausted: unresolved HIGH findings remain frozen; CRITICAL may draw from emergency reserve.

If the required assurance budget is unavailable: enter `DEGRADED_ASSURANCE_MODE`, record a receipt, and block affected high-risk promotion. Never silently substitute weaker assurance while claiming equivalent confidence.

## 9. Blind Round 1

Primary reviewers independently inspect the same ReviewPacket.

No same-cycle peer conclusion is visible before the reviewer emits its own finding.

A finding includes at least:

- Finding ID;
- target;
- claim;
- evidence;
- severity;
- affected objects;
- proposed correction;
- required tests;
- confidence/uncertainty;
- evidence ancestry;
- overturn conditions;
- commit and DesignEpoch binding.

Round 1 is proposal-only.

## 10. Evidence and counterexamples

Counterexamples do not dominate merely by existing.

Use `CounterexampleRecord/v1` with evidence class, reproducibility, affected claim, ground-truth binding, and verification status.

Evidence classes may include:

- executable/reproducible trace;
- formal or machine-checkable proof;
- authoritative artifact/exact code-schema evidence;
- reasoned model argument;
- unsupported assertion.

Executable traces and proofs are not ranked as interchangeable. Each is verified against its own ground truth:

- a trace must bind to the current commit, DesignEpoch, environment, inputs, and execution path;
- a proof must have premises that match the actual implementation/design.

If a verified proof and verified execution trace conflict, or two verified proofs/traces conflict, neither automatically wins. The conflict itself becomes a finding and dependent mutation freezes.

Unverified model arguments may trigger escalation but do not veto verified evidence by themselves.

## 11. Round 2 cross-examination

Reviewers now receive peer findings as untrusted data, not instructions.

They test:

- whether the claim is true;
- whether evidence is sufficient;
- whether a counterexample can be verified;
- whether the finding duplicates an existing item;
- whether the proposed fix is correct;
- whether it introduces another defect;
- whether a stronger alternative exists;
- whether everyone missed another issue.

No majority voting is permitted.

Cross-examination may produce:

- ACCEPTED
- REJECTED
- DEFERRED
- UNRESOLVED
- NEEDS_ESCALATION

CRITICAL with substantive disagreement escalates immediately and freezes affected scope.

HIGH with substantive unresolved objection escalates; if unresolved, affected scope freezes.

MEDIUM symmetric disagreement is DEFERRED and must specify a substantive retry mechanism: a new reviewer, new evidence, or disagreement-as-finding. If unresolved after three cycles, escalation is mandatory.

LOW disagreement may be deferred or rejected for insufficient evidence.

## 12. Cross-examination manipulation defense

Peer text is an adversarial input surface.

Review prompts must explicitly separate peer records from instructions.

Suspected instruction injection, authority impersonation, fabricated evidence, malformed evidence, or role manipulation produces `CrossExamManipulationFlag/v1`.

Flagged findings are quarantined, not accepted or dismissed.

Verification must be performed by a reviewer that is neither the author nor the flagger.

Disposition:

- CONFIRMED_MANIPULATION
- FALSE_FLAG
- INCONCLUSIVE

Flag accuracy and missed confirmed manipulation feed model scorecards.

## 13. SemanticImpactAssessment

Routing to implementation versus design is itself a first-class auditable decision.

Use `SemanticImpactAssessment/v1` with two layers.

Layer 1 — mechanical touch detection. Flag any diff touching:

- FunctionContract input/output/precondition/postcondition;
- schema semantics;
- invariant meaning or scope;
- registry membership or meaning;
- authority/permission semantics;
- public API behavior;
- state-transition semantics;
- error/failure semantics;
- canonical cross-reference target;
- canonical test expressing intended behavior;
- Human/System description of observable behavior.

Layer 2 — classify every touched item:

- SEMANTIC
- COSMETIC
- EQUIVALENT_REFACTOR
- TEST_ADDITION
- UNCLEAR

COSMETIC and EQUIVALENT_REFACTOR require an explicit equivalence argument or proof.

Routing:

- any supported SEMANTIC -> design pipeline;
- UNCLEAR -> design/escalation;
- only supported non-semantic classifications -> implementation path may be auto-merge eligible.

The Integrator Challenger audits this classification, including explicit sampling of the NO-semantics auto-merge path.

## 14. Finding routing

Accepted findings route to one or more of:

- CODE_FIX: implementation defect where canonical design is already clear;
- SWARM_FIX: review/evolution machinery defect;
- DESIGN_DELTA: canonical design ambiguity, missing semantics, or implementation evidence showing design weakness;
- REVIEW_PROCESS_FIX: implementation or incident evidence showing the review process itself is insufficient.

Code must not silently invent Garden semantics.

Implementation experience can feed both design and review machinery.

## 15. IntegrationDecision

ChatGPT acts as primary integrator but not unchecked final arbiter.

`IntegrationDecision/v1` contains:

- selected action;
- finding validity assessment;
- semantic classification;
- routing;
- considered_alternatives[];
- rejection_reasons[];
- risks;
- rollback path;
- required tests;
- authority/delegation basis.

Where independent alternatives exist, at least one considered alternative must originate independently of ChatGPT: reviewer finding, counterexample, design delta, prior disagreement, or equivalent external evidence.

## 16. Integrator Challenger

Important decisions are independently reviewed by a Challenger.

The Challenger reviews:

- finding validity;
- evidence quality;
- packet construction;
- SemanticImpactAssessment;
- routing;
- IntegrationDecision;
- considered alternatives;
- authority/delegation compliance;
- privacy/budget compliance;
- RuleID->CheckID->Receipt closure.

Output: `ChallengerDecision/v1` with PASS, CHALLENGE, ESCALATE, or AUDIT_PENDING.

Challenger family rotates on a slower cadence, approximately weekly, and reads a rolling 7–30 day history to detect patterns such as systematic semantic down-classification or thin approvals.

The Challenger must audit samples of the auto-merge path specifically.

Monthly, sample Challenger PASS/reject decisions using `ChallengerAuditReceipt/v1`. The meta-auditor must be a model family different from both ChatGPT and the Challenger being audited. If an independent third family is unavailable, mark AUDIT_PENDING.

## 17. Implementation pipeline

Use one builder + multiple critics, not multiple competing builders.

For implementation findings:

accepted finding -> exact canonical requirement -> governed branch -> implementation -> tests -> DeepSeek/Qwen/Gemini review -> adversarial tests -> repair -> Garden/GSL checks -> required Challenger -> merge -> post-merge verification.

Auto-merge is allowed only when:

- semantic impact is supported NO;
- tests pass;
- objections are resolved;
- security/authority constraints are preserved;
- reference closure passes;
- required receipts pass;
- no active freeze blocks the scope.

## 18. Freeze propagation and lifting

Unresolved HIGH/CRITICAL findings freeze the affected path.

Freeze may block:

- affected merges;
- dependent work admission;
- related design delta;
- daily successor if it depends on the disputed claim.

Foundational issues may create GLOBAL_FREEZE.

In-flight work may finish on its branch but cannot merge or promote while the freeze remains active.

The branch remains bound to its DesignEpoch. If any frozen path changes while the freeze is active, the branch must rebase against current state and rerun relevant tests/reviews before merge. Continuing without rebase is allowed only when the branch touches no frozen path.

Freeze states include ACTIVE, LIFT_PENDING, LIFTED, SUPERSEDED.

SUPERSEDED is valid only when the frozen scope no longer exists or a verified superset finding replaces the original; evidence is required.

`FreezeLiftReceipt/v1` must link the original freeze, resolved finding, repair evidence, tests, released scope, independent verification, and Challenger approval.

## 19. Reopen and revert

CLOSED is not permanently terminal.

A closed finding may become REOPENED when later evidence establishes causal linkage to a regression or incident.

An implementation may become REVERTED when rolled back.

Reopen/revert events are explicit graph edges and receipts, not hidden history edits.

## 20. Production-incident feedback

Real escaped defects are first-class quality evidence.

`ProductionIncidentRecord/v1` records:

- incident;
- attribution mode: SINGLE_COMMIT | INTERACTION | CUMULATIVE | UNKNOWN;
- attributed_commits[] with roles/weights where possible;
- affected modules;
- packet(s) that reviewed the relevant change;
- reviewers involved;
- findings produced or absent;
- IntegrationDecision/Challenger lineage;
- root cause;
- detected review miss, packet miss, test miss, semantic-routing miss, integration miss, or Challenger miss.

Real escaped defects are more important than internal activity metrics.

## 21. Seeded-defect evaluation

Prefer a separate `garden-evaluation` repository for seeded defects.

It must have its own DesignEpoch binding and a mirror-sync procedure.

`MirrorSyncReceipt/v1` records source commit, mirror commit, sync method, DesignEpoch, and integrity check.

Each `SeededDefectRun/v1` records `seeded_defect: true`, injected defect, expected detection condition, injection authority, cleanup verification, and board outcome.

Seeded-defect artifacts must never be mergeable into production or canonical input. Metrics are separate from real findings.

If the same repository is ever used instead, isolation must exist at Git/CI/release-policy level, not by naming convention alone.

## 22. Reviewer performance and independence

Track at least:

- reviewer count;
- family count;
- unique argument count;
- evidence strength;
- independence estimate;
- verified counterexample status;
- unique valid findings;
- duplicates;
- false positives;
- missed seeded defects;
- real escaped-defect misses;
- findings later reopened;
- Challenger reversals;
- cost per useful finding;
- latency.

Do not hard-code stereotypes about model families. Infer failure patterns from Garden's own history.

Use empirical results to change model frequency, role, or eligibility.

## 23. Design-delta accumulation

Canonical Garden remains immutable during ordinary hourly work.

Each accepted semantic improvement becomes `DeltaRecord/v1` containing problem, old semantics, proposed semantics, affected modules, schemas/contracts/invariants/tests/references, evidence, reviews, Challenger result, DesignEpoch, and status.

Typical states:

- PROPOSED
- REVIEWED
- DISPUTED
- ACCEPTED
- ADMITTED_FOR_SUCCESSOR
- REJECTED

Admitted deltas accumulate during the day without editing the canonical predecessor.

## 24. Daily successor

Normal cadence is at most one successor per Asia/Kolkata day; zero is valid and should be recorded as `NO_SEMANTIC_RELEASE`.

Daily materialization:

immutable predecessor + all admitted deltas -> complete successor candidate.

The entire integrated candidate is then attacked and verified, including:

- cross-delta consistency;
- predecessor retention;
- five-file completeness;
- reference closure;
- schemas/registries/FunctionContracts/invariants/tests;
- GSL-COMPARE;
- Reason/Proof/Audit/Compliance/HSA;
- expected-delta drift;
- manifests;
- hashes;
- provenance;
- required Challenger evidence.

If individually valid deltas conflict in composition, repair/remove the conflicting delta and re-run verification.

Canonical promotion remains governed by the HumanDelegationEnvelope and protected-change rules.

## 25. Emergency successor

An out-of-band successor is allowed only for confirmed safety, authority, HSA, security, critical-correctness, or foundational semantic contradiction.

The first emergency successor inside a rolling 24-hour window follows the emergency protocol.

A second emergency successor inside the same rolling 24 hours requires explicit human acknowledgement or remains frozen.

Use `EmergencySuccessorReceipt/v1`.

## 26. Required lifecycle records

The implementation should provide at least:

- FindingRecord/v1
- ReviewPacket/v1
- PacketConstructionDecision/v1
- CounterexampleRecord/v1
- SemanticImpactAssessment/v1
- DeltaRecord/v1
- IntegrationDecision/v1
- ChallengerDecision/v1
- ChallengerAuditReceipt/v1
- ReviewReceipt/v1
- EscalationRecord/v1
- RoutingReceipt/v1
- BudgetReceipt/v1
- HumanDelegationEnvelope/v1
- HumanAvailabilityWindow/v1
- CrossExamManipulationFlag/v1
- SeededDefectRun/v1
- MirrorSyncReceipt/v1
- ProductionIncidentRecord/v1
- FreezeRecord/v1
- FreezeLiftReceipt/v1
- ReopenRecord/v1
- EmergencySuccessorReceipt/v1
- CanonicalizationReceipt/v1
- RuleDefinition/v1
- CheckDefinition/v1
- RuleCheckBinding/v1

All records bind to exact applicable repository commit(s), canonical version, DesignEpoch, model/provider identity where applicable, timestamps, evidence/source hashes, and decision lineage.

## 27. Rule -> Check -> Receipt closure

This is the governing implementation invariant.

Every normative rule MUST map to an executable check. Every check MUST produce a typed receipt. Every receipt MUST bind to the exact commit/DesignEpoch/evidence it verified.

A rule without a check is non-enforced.

A check without a receipt is non-auditable.

A receipt without provenance is invalid.

Required traceability:

RuleID -> CheckID -> check implementation/version -> evidence consumed -> typed receipt -> PASS|FAIL|UNCLEAR -> permitted/frozen mutation.

CI must fail or freeze affected promotion for:

- rule without check;
- check without rule;
- check without receipt;
- receipt without provenance;
- unknown DesignEpoch;
- missing required evidence;
- failed required check.

## 28. Hourly logical cycle

1. Detect repo/design changes, incidents, failures, pending findings, and freezes.
2. Select highest-priority target; use deterministic coverage rotation only when no higher-priority work exists.
3. Mechanically build ReviewPacket.
4. Apply privacy gate.
5. Apply budget gate.
6. Run blind ChatGPT/DeepSeek/Qwen/Gemini review as available and permitted.
7. Cross-examine.
8. Verify counterexamples/evidence.
9. Resolve, defer, freeze, or escalate findings.
10. Build SemanticImpactAssessment.
11. Route finding.
12. Build IntegrationDecision.
13. Obtain required Challenger decision.
14. Implement accepted code/swarm fixes.
15. Run independent patch review and adversarial tests.
16. Merge eligible work.
17. Admit eligible design deltas.
18. Apply or lift freezes using receipts.
19. Persist privacy/budget/evidence/decision receipts.
20. Close the cycle.

## 29. Operational state and migration

The process is being migrated from older Garden review workflows into this protocol. Existing hourly blind-review, cross-examination, integration/build, daily repo review, and daily-candidate machinery remain useful but must progressively be brought under the typed schemas and Rule->Check->Receipt closure above.

The protocol itself is not considered executable merely because this document exists. Closure is reached only when each normative rule is backed by an implemented check and typed receipt.

## 30. Governing rule

Review continuously. Build continuously. Improve the review system continuously. Accumulate semantic deltas continuously. Promote canonical Garden only when evidence, assurance, and delegated authority permit it.
