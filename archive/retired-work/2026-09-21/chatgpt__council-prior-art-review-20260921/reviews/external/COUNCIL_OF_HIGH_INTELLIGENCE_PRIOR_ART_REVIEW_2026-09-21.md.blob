# External prior-art comparison — Council of High Intelligence

Status: NONCANONICAL REVIEW EVIDENCE  
Date: 2026-09-21  
External source: https://github.com/0xNyk/council-of-high-intelligence  
License observed: MIT  
Use rule: requirements/ideas comparison only. No external source code, prompt/persona text, configuration, or expressive protocol text is copied into Garden by this review.

## Scope boundary

This review compares the public Council project with Garden's existing GROUP_REVIEW/OpenRouter mechanisms. It does not modify Garden canonical semantics and does not touch active v15.10/v15.11 design work.

MIT licensing permits broad copyright use subject to its notice, but this review does **not** treat an MIT license as a patent grant or as a freedom-to-operate opinion. If Garden later proposes implementing a mechanism whose patent status matters, that mechanism needs a separate targeted prior-art/patent review.

## Existing Garden mechanisms that already cover the same problem class

Garden already has:
- immutable/hash-bound review packets;
- blind workers whose first results are frozen before peer exposure;
- real multi-provider/model review rather than simulated personas;
- explicit process-failure semantics;
- independent verifier stage;
- evidence/authority separation;
- bounded paid OpenRouter execution, identity checks and privacy/provider gates;
- no assumption that reviewer consensus creates semantic/canonical authority;
- UNKNOWN/blocked states rather than forced success;
- repository-mediated durable review evidence.

These should remain Garden-owned. The external project is not a replacement architecture.

## External mechanisms examined

The public Council README describes:
1. independent first positions followed by cross-examination, final stance and synthesis;
2. explicit FACT / INFERENCE / ASSUMPTION / UNKNOWN field labels;
3. checks for premature agreement, repeated claims, missing dissent and unsupported confidence;
4. preservation of split outcomes instead of prose-manufactured consensus;
5. recommendation output paired with acceptable compromises, kill criteria and a concrete next action;
6. outcome checkpoints recording prediction, owner, review date and evidence that would change the recommendation;
7. provider-family separation for opposing/polarity seats where possible;
8. dry-route preview of provider/model seat allocation;
9. smaller review modes for cheaper/reversible decisions;
10. simulation/validation checks for protocol parity and verdict fields.

## Gap comparison

### A. Already present / do not import

**Blind first pass and later reconciliation** — already materially stronger in GROUP_REVIEW because Garden binds workers to exact frozen packets and treats contamination/process failure explicitly.

**Multi-provider routing** — already present through Garden reviewer slots/OpenRouter. Keep Garden identity/privacy/budget gates.

**No forced consensus / UNKNOWN** — already part of Garden's broader typed epistemic approach. No need to import Council wording.

**Outcome revalidation concept** — Garden already has prediction/calibration/revalidation semantics at the design level. Do not duplicate semantic ownership.

### B. Useful operational candidates that appear incompletely explicit in GROUP_REVIEW

These are stated as independently formulated Garden requirements, not copied protocol text.

**GR-CAND-EXT-001 — Claim-status annotation in reviewer output**
Require material reviewer claims to identify whether they are directly evidenced, derived from evidence, dependent on an unverified premise, or unresolved for lack of information. Map these to existing Garden evidence/epistemic types rather than introducing Council's labels as new canonical types.

**GR-CAND-EXT-002 — Dissent-retention check**
Before synthesis can close, verify that material unresolved disagreements are represented in the synthesis or explicitly disposed with evidence. A synthesizer must not convert a split review into apparent agreement merely by omission.

**GR-CAND-EXT-003 — Premature-convergence detector**
Add an operational check for suspicious convergence before independent evidence is frozen, including shared phrasing/claim structure where it can indicate accidental peer leakage. This supplements, not replaces, Garden's existing blind-worker provenance controls.

**GR-CAND-EXT-004 — Decision stop/reversal conditions**
For a review that recommends an operational action, optionally record measurable conditions that would stop, reverse or reopen that action. Bind them to Garden's existing rollback/revalidation concepts instead of creating a new authority mechanism.

**GR-CAND-EXT-005 — Review follow-up checkpoint**
For predictions or uncertain empirical claims that materially affect a decision, optionally record an owner, review condition/date, and evidence needed for revalidation. Reuse Garden prediction/calibration semantics.

**GR-CAND-EXT-006 — Reviewer-family conflict separation**
When two assigned reviewer roles are intended to provide opposing or independent pressure, prefer different underlying model families/providers where available. Failure to diversify must be visible; it must not silently masquerade as independent-model evidence.

**GR-CAND-EXT-007 — Routing preview**
Provide a no-inference preview showing the exact planned reviewer slots/models/providers, expected budget reservation and fallback behavior before paid execution. This is an operational transparency/debugging feature and creates no authority.

**GR-CAND-EXT-008 — Proportional review modes**
Preserve Garden's risk-based triage but make the execution mapping explicit: cheap/reversible work should not automatically consume the same review topology as high-impact work. Existing Garden triage remains the owner; this candidate concerns implementation clarity/testing only.

### C. Not recommended for Garden adoption

- named historical/celebrity personas as core reviewer identities;
- importing Council's prompt/persona contracts;
- copying its coordinator protocol or installer architecture;
- weighted tallies as an authority source;
- replacing Garden's typed evidence/authority/admission system with a deliberation verdict;
- copying source/configuration merely because it is MIT licensed.

## IP/provenance controls for any implementation

1. Implement candidates from this Garden requirement statement, not by copying external code/text.
2. Keep this review as provenance showing the external project was known before implementation.
3. If any external code is later reused, isolate it, record exact source commit/path, preserve the required license notice, and review compatibility separately.
4. Do not claim patent clearance from this comparison.
5. For a mechanism selected for product/commercial deployment where patent exposure is material, perform a targeted patent/prior-art search before admission.
6. Preserve Garden's independent pre-existing mechanisms and commit history as evidence of independent development.

## Recommended implementation order

1. GR-CAND-EXT-007 routing preview.
2. GR-CAND-EXT-006 reviewer-family conflict separation.
3. GR-CAND-EXT-002 dissent-retention check.
4. GR-CAND-EXT-001 claim-status annotation using existing Garden types.
5. GR-CAND-EXT-003 premature-convergence detector.
6. GR-CAND-EXT-004/005 stop/reversal and follow-up checkpoint binding.
7. GR-CAND-EXT-008 proportional-mode implementation tests.

All are operational candidates only until independently reviewed and merged through the current Garden Git/process gates.
