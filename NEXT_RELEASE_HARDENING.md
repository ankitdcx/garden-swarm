# Garden Next-Release Hardening Candidates

Status: **CANDIDATE / NOT RATIFIED / NOT PART OF PUBLISHED v15.5**

The published Garden v15.5 canonical source remains unchanged. This file records concrete successor candidates discovered through external adversarial review and full-source triage.

Canonical tracking issue: #17.

## 1. Normalize emergency source-independence semantics

### Problem

v15.5 contains a wording conflict:

- Annexure `EMG-003` uses `>=2 independent sensors`;
- the Technical emergency detector states that required source diversity/independence is hazard/profile-specific and that a universal sensor count is not assumed.

### Candidate normalized rule

`EMG-003` successor wording:

> Emergency triggers SHALL satisfy the source-diversity/independence requirement defined by the applicable hazard/profile. No universal sensor-count constant is assumed. Nominally distinct observations that share a material common source, control path, calibration dependency or failure mode SHALL NOT be counted as independent merely by multiplicity.

Additional hardening:

> Self-generated urgency, internal preference/confidence/valence/model state, or evidence causally controlled solely by the acting cognition whose authority would expand cannot by itself satisfy the independent external-hazard evidence requirement.

### Regression tests

1. Two sensors derived from one upstream feed do not count as two independent sources.
2. Agent-generated urgency text cannot establish external hazard.
3. Stale/forged attestation yields STALE/BLOCKED/UNKNOWN as applicable.
4. Unresolved common-mode dependence remains INCONCLUSIVE/UNKNOWN.
5. A profile may require one, two, or more sources only when justified by its hazard/evidence contract; the count is not a universal Garden constant.

## 2. Typed consent-validity assessment

### Problem

Garden already requires coerced, stale, ambiguous or poorly understood consent to default to preserve/DO_NOTHING where applicable and already separates `ConsentContract` from `UnderstandingRecord`. The residual risk is implementation-level conflation of authentication/signature with proof of informed and voluntary consent.

### Candidate artifact

Name provisional pending collision/equivalence review:

`ConsentValidityAssessment`

Suggested semantic fields:

- `subject_ref` / competent principal binding;
- requested action/effect/scope;
- identity/authentication evidence;
- freshness/expiry/revocation state;
- disclosure/explanation reference;
- `UnderstandingRecord` / comprehension evidence;
- voluntariness/coercion evidence and limitations;
- applicable domain/jurisdiction/profile requirements;
- independent-review requirement where applicable;
- material invalidators;
- DesignEpoch / KnowledgeSnapshot / environment bindings;
- provenance;
- status:
  `VALID_FOR_SCOPE | INVALID | UNKNOWN | INCONCLUSIVE | STALE | BLOCKED`.

### Candidate hard rules

1. Signature/authentication establishes only the properties supported by its declared identity/act assumptions; it does not by itself prove voluntariness, freedom from coercion, or comprehension.
2. When voluntariness/comprehension is a required condition and is not adequately evidenced, status cannot be `VALID_FOR_SCOPE`.
3. `UNKNOWN`/`INCONCLUSIVE` follows the applicable preserve/deny/escalate semantics rather than optimistic admission.
4. Model confidence, reputation, prediction of likely agreement, or majority preference cannot manufacture consent.
5. Material change in action, effect, risk, explanation, environment, scope, subject state, or governing requirement invalidates prior consent as applicable.
6. Consent validity does not replace legality, rights, safety, policy, evidence or capability gates.

### Regression tests

1. Valid signature + stale/revoked scope -> STALE/INVALID.
2. Valid signature + missing required comprehension evidence -> UNKNOWN/INCONCLUSIVE.
3. Valid signature + credible coercion evidence -> INVALID/BLOCKED/review under the profile.
4. No consent + high model confidence the person would agree -> no authorization.
5. Material effect/risk delta after valid consent -> re-consent/review required.
6. R2/R3 replay or mutation of consent artifacts -> external gate rejects unless authoritative current state is independently established.

## 3. External-review regression bundle

Preserve these scenarios even when the current design already contains the intended safeguard:

- shared-memory / retrieved-context poisoning of a higher-authority agent;
- stale flattened summaries / learned policies after DesignEpoch change;
- A -> B -> C delegation-chain authority amplification;
- subverted proposer targeting ActionGate inputs/checkers;
- attested R0/R1 isolation from R2/R3 writable authority;
- common-mode emergency sensors posing as independent;
- authentic-but-insufficient consent evidence.

A successor should add these as executable tests where the runtime/security harness exists rather than treating prose coverage as execution evidence.

## 4. ConstitutionalEvent typed-boundary hardening

Status: **ACCEPTED FOR SUCCESSOR CANDIDATE TRIAGE / NOT RATIFIED**

Source lineage: repeated bounded reviews on issue #49 were independently cross-referenced against the complete v15.5 owner contracts before admission to this candidate queue. Failed/stale/model-unavailable attempts are not evidence for this section.

### Whole-source triage

v15.5 already establishes the main semantics and they should not be duplicated under new owners:

- a constitutional/right violation or VETO blocks the affected transition;
- a consequential PASS emits `ConstitutionalEvent(kind=CHECK)` and ordinary flow may continue;
- unresolved constitutional applicability routes to a low-authority safe state/escalation rather than optimistic admission;
- containment/restriction has its own authority, evidence, severity/risk and applicability requirements;
- event history is immutable and later resolution is linked rather than rewriting history;
- authorization, commitment and execution are distinct stages, and irreversible effects already use governed prepare/commit/compensation paths.

The successor work below therefore closes machine-traceability and type-coherence gaps rather than creating a new constitutional owner, containment authority, or execution engine.

### 4.1 Non-authorizing event and typed containment-action linkage

#### Problem

`ConstitutionalEvent` carries `containment_criteria_result?`, evidence/routing fields and `resolution_ref?`, while the owner contract separately says containment/restriction follows its own authority and applicability rules. The schema does not currently make the separate authorization linkage explicit enough for a machine checker to prove that a restriction was independently authorized.

#### Candidate rule

A `ConstitutionalEvent`, including `kind=VIOLATION`, `check_result=VETO`, `containment_criteria_result`, evidence references, routing fields or event existence, **MUST NOT by itself authorize containment/restriction**.

If containment/restriction is actually executed in response to the event, the execution path MUST carry a machine-verifiable typed reference to the separately authorized containment/action/admission decision under the applicable authority, evidence, severity/risk, safety, privacy, scope and freshness rules. Reuse an existing canonical action/authorization/`ContainmentAction`/admission receipt where it is the correct owner; do not invent a duplicate authority source. `resolution_ref` may satisfy this linkage only if its type and contract explicitly bind and verify that separate authorization.

#### Regression tests

1. `VETO + containment_criteria_result=SATISFIED + no valid separate authorization/action receipt` -> offending transition remains blocked; no containment/restriction executes.
2. A valid separately authorized containment action may execute only within its own scope/expiry/evidence and safety constraints.
3. Event evidence, routing or severity alone cannot mint containment authority.
4. Revoked/stale/mismatched containment authorization -> no containment execution; the constitutional block remains independently effective.

### 4.2 ConstitutionalEvent cross-field coherence

#### Problem

The current schema independently enumerates `kind: CHECK | VIOLATION` and `check_result: PASS | VETO | INCONCLUSIVE | UNKNOWN`. Existing tests establish the intended PASS path, but the type itself can represent contradictory tuples such as `kind=VIOLATION, check_result=PASS` unless a checker adds an unstated convention.

#### Candidate minimum rules

1. `check_result=PASS` MUST imply `kind=CHECK`.
2. `kind=VIOLATION` MUST NOT coexist with `check_result=PASS`.
3. `recorded/observable event` is not a blocking predicate by itself; a PASS/CHECK event remains eligible for ordinary flow absent an independent blocking gate.
4. Stronger mappings for `VETO`, `INCONCLUSIVE` or `UNKNOWN` MUST come from their existing owner contracts or an explicit machine-resolvable binding; they must not be guessed from enum position or local implementation convention.

#### Regression tests

1. Construct `kind=VIOLATION, check_result=PASS` -> schema/conformance rejection.
2. PASS/CHECK event recorded and observable -> ordinary flow may continue if all other gates pass.
3. `INCONCLUSIVE` or `UNKNOWN` cannot be silently promoted to PASS by a local event consumer.

### 4.3 Non-amplifying event observability

#### Problem

The Human source requires consequential constitutional checks to be observable, and the event carries evidence/context references. Privacy already taints protected data and forbids unauthorized PII processing, while Security/Authority remain separate gates. The Event-Service query/route surface should make that inheritance machine-resolvable so `observable` cannot be implemented as unrestricted payload disclosure.

#### Candidate rule

ConstitutionalEvent observability is an **authority-preserving projection**, not disclosure or dereference authority.

- observing, routing, subscribing to or querying an event MUST NOT grant authority to read/dereference protected `evidence_refs`, rights context, identity data or other protected payloads;
- referenced data retains its source access-control, consent, taint, minimization, confidentiality, redaction, retention and jurisdictional constraints;
- an event projection may expose only fields authorized for that observer and purpose;
- an authorized audit path may retain access required by its separate authority without broadening ordinary subscriber access;
- event visibility never creates containment authority or guilt/intent semantics.

Prefer an explicit Event-Service/Security/Privacy binding over a ConstitutionalEvent-specific duplicate access-control subsystem.

#### Regression tests

1. Unauthorized subscriber can receive the permitted event projection but cannot dereference protected evidence/context.
2. Authorized auditor can access only the evidence allowed by its valid scope and purpose.
3. Redaction/minimization of event projection does not mutate the immutable underlying event/evidence lineage.
4. Subscription/query capability alone cannot be exchanged for evidence-read or containment capability.

### 4.4 Existing-semantics regression probes — no new owner rule yet

The following hourly ideas are worth preserving as tests/cross-reference probes, but current whole-source review does **not** justify a new independent invariant family for them:

1. **INCONCLUSIVE/UNKNOWN fail-closed behavior.** HumanCore.Constitution already routes unresolved applicability to low-authority safe state/escalation; Policy also forbids converting UNKNOWN/CONFLICT into PERMIT. A successor should make the ConstitutionalEvent binding machine-resolvable rather than duplicate the rule.
2. **VETO before consequential effect commit.** Constitution already blocks execution and Compute.Execution already uses authorization plus prepare/commit/compensation barriers. Add a conformance vector if needed; do not create a second execution-order owner unless an executable counterexample demonstrates a gap.
3. **Containment outcome must not release the original constitutional block.** Treat as a regression property of the existing independent VETO and containment contracts.
4. **Persistence/logging failure must not fail open.** Once the independent constitutional gate returns VETO, later event/evidence persistence failure must not turn that VETO into permission. Test this as fault injection against the existing gate/recording separation.
5. **Fresh-identifier replay/effect equivalence.** Preserve as an adversarial probe. Reuse existing idempotency, ActionHash, re-evaluation and transition/effect semantics where sufficient; add a new semantic rule only if a materially equivalent retry can actually bypass current gates.

### 4.5 Rejected/duplicate interpretations from the hourly stream

These should not be promoted merely because they appeared repeatedly in comments:

- **"Any recorded ConstitutionalEvent blocks."** Rejected: v15.5 explicitly permits PASS/CHECK ordinary continuation; only a violation/VETO or another independent blocking gate blocks.
- **"Every violation automatically freezes the agent."** Rejected: directly contradicts CON-EVT-003 and the Human source.
- **"A ConstitutionalEvent proves guilt or intent."** Rejected: directly contradicts the owner contract.
- **"Create a new containment authority source."** Rejected: containment must reuse the existing authority/action/admission architecture.
- **Duplicate INCONCLUSIVE/UNKNOWN owner semantics.** Rejected unless cross-reference analysis proves the existing Constitution/Policy/AAP owners are not machine-resolvable at the gate.

## 5. Mechanically derived ReviewPacket and reviewer-ordering hardening

Status: **CANDIDATE / NOT RATIFIED / NEEDS REQUIRED REVIEW**

Source evidence: bounded ChatGPT blind/cross-examination evidence on issue #49 identified a process gap after directly checking the committed public review workflow and accessible repository state. The earlier one-family execution-budget versus three-family admission-quorum failure is **not** part of this candidate because PR #71 already repaired that defect on `main`.

### Problem

The current hourly review machinery produces target-selection, provider-selection/reviewer outputs and combined receipts, but it does not yet create a single mechanically derived `GardenReviewPacket/v1` that binds the complete scope a reviewer is expected to inspect. Without that packet, a model can neither prove that the reviewed diff/symbol/dependency surface was complete nor distinguish an intentional exclusion from silent curation.

This is review-assurance infrastructure only. Recording it here does not ratify a new Garden source rule, does not alter v15.5, and does not authorize semantic admission.

### Candidate owner/bindings

Prefer a review-orchestration/evidence owner in `garden-swarm`; do not create a new authority source.

A packet should bind, at minimum:

- exact public/private repository commit(s) in scope, without exposing private source material to public providers;
- immutable canonical Garden version, source root and DesignEpoch;
- reproducible base..head diff and mechanically derived changed paths;
- changed symbols and dependency/reference closure;
- mechanically affected schemas, FunctionContracts, registries, invariants and tests;
- exact CI/test/environment receipts relevant to the change;
- linked unresolved/reopened findings and applicable freeze state;
- target/source hashes for the bounded review target;
- every non-mechanical inclusion or exclusion as an explicit `PacketConstructionDecision` with provenance and reason;
- immutable packet hash/artifact identity carried into blind-review and cross-examination receipts.

The packet is evidence scope, not authority. It MUST NOT self-classify a semantic change as admitted, mint trusted authority, satisfy independent-review quorum, or override ActionGate/DesignEpoch/human boundaries.

### Reviewer-ordering requirement to test

The packet must exist before Round-1 blind review begins. Peer conclusions must remain unavailable to that reviewer until its blind finding is persisted. Cross-examination then consumes the same exact packet identity plus eligible peer evidence.

### DO_NOTHING comparison

DO_NOTHING preserves the present failure mode: reviews may be exact-target-bound yet still lack a machine-verifiable proof that the surrounding changed code/design/evidence scope was complete. This makes omissions difficult to distinguish from deliberate exclusions and weakens later semantic-impact, Challenger and integration decisions. A deterministic packet improves auditability without granting any new authority.

### Required regression tests

1. Reject packet construction when repo commit/base/head, canonical source root/DesignEpoch, target or source-hash binding is absent/stale/mismatched.
2. Recompute diff, changed-path set, changed-symbol extraction and dependency/reference closure deterministically.
3. Reject unexplained manual exclusions and incomplete mechanically affected-object closure.
4. Bind CI/test receipts to the exact commit, DesignEpoch and execution environment; stale traces do not count.
5. Require mechanically relevant unresolved/reopened findings and freeze state to be linked.
6. Verify public packet projections never disclose private `garden-main` source beyond explicitly permitted hashes/identifiers; unknown provider policy remains DENY.
7. Verify Round 1 cannot start until the exact packet artifact exists and peer conclusions remain inaccessible until the blind receipt is persisted.
8. Verify cross-examination rejects a peer finding bound to any different packet hash/commit/DesignEpoch/target.

### Conflicts / duplicates

- The execution-budget/admission-quorum mismatch is already resolved by merged PR #71 and is intentionally not requeued here.
- Existing Design Review Matrix target binding, source manifests, integration-provenance receipts and GSL reference closure are inputs to this candidate, not substitutes for the complete ReviewPacket.
- If later evidence shows an existing artifact already provides every required field and ordering guarantee, prefer equivalence/subsumption and close this candidate rather than create duplicate machinery.

## 6. Non-goals

These candidates do not propose:

- a new top-level engine;
- a new authority source;
- a new GSL Core Object or Core Relation;
- automatic deployment authority;
- changing v15.5 history in place.

Any canonical successor must run ordinary Garden comparison, dependency, rights/authority, proof/test and release-integrity processes before ratification.