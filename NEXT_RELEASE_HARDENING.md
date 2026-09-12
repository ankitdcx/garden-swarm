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

## 4. Non-goals

These candidates do not propose:

- a new top-level engine;
- a new authority source;
- a new GSL Core Object or Core Relation;
- automatic deployment authority;
- changing v15.5 history in place.

Any canonical successor must run ordinary Garden comparison, dependency, rights/authority, proof/test and release-integrity processes before ratification.