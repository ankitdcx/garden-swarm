# Garden post-v15.5 pending design candidates

Status: **tracking only — candidate / not ratified / not part of published Garden v15.5**.

This file is the public reconciliation map for worthy Garden source-design candidates. It does not itself admit, ratify, implement, or promote any semantic change. Published v15.5 remains immutable.

## Active source-design candidate groups

1. **Nine v15.6 GSL gap closures** — tracked structurally in the private `ankitdcx/garden-main` v15.6 candidate registry: bootstrap trust-root ceremony; shared-state authority provenance; deterministic let/query semantics; causal-level typing; R0 SanityGate separation; rights-view ordering; provenance redaction-vs-absence typing; and catalogue closure for `AuthorityDecl` / `EffectDecl`.

2. **External hardening queue** — `NEXT_RELEASE_HARDENING.md`: emergency-source independence normalization, typed consent-validity assessment, external regression probes, and ConstitutionalEvent typed-boundary/observability hardening.

3. **GSL-KR Continuous Epistemic Assimilation & Consolidation (KR-CEA) v1.0** — worthy candidate, now explicitly tracked for successor review. Core delta: runtime cognition may continuously improve governed epistemic state without waiting for weight retraining, while persistent knowledge, model/scaffold consolidation, execution authority and constitutional change remain separate typed transitions with separate gates. Candidate additions include `EpistemicDeltaCandidate`, `KnowledgeAssimilationReceipt`, loss-aware `KnowledgeCompressionReceipt`, cross-context pattern receipt/profile, separately governed `ModelConsolidationCandidate`, lineage-aware corroboration, current-applicability checks for retrieval, and knowledge-dividend measurement. Existing v15.5 owners such as `BeliefTimeline`, `EpistemicTransition`, `HistoricalSemanticSummary`, Continuous Failure Learning, Provenance, Search/Compare/Reason/Proof and dependency-aware revalidation should be reused rather than duplicated.

4. **Rationalization & Verification Hardening / ReasoningStrategyPortfolio historical proposal** — must not be silently lost. Status: **reconciliation required**. Compare the earlier ratified design proposal against v15.5 Reason, GSL-COMPARE, AAP, FunctionContracts and verification owners. Mark it fully subsumed with evidence if nothing survives; otherwise requeue only the genuinely missing semantic requirements. NO_CHANGE is preferred over duplicate architecture.

## Worthy work that is *not* automatically a Garden source-design delta

- **WP-009H shared DesignEpoch convergence vectors** — important implementation/conformance hardening; already merged in the private build repository. It becomes a source-design delta only if convergence testing exposes a missing semantic requirement.
- **WP-009D..G** Compare/Reason/Proof/Evidence separation, algebra/AAP selection and tamper-evident evolution audit — implementation/conformance hardening toward existing Garden intent.
- **Multi-agent integration provenance and semantic-collision checks** — repository/build hardening, not automatically a five-file semantic change.
- **Hourly 3–4+ same-target reviews, daily repo review, one daily successor candidate, archive/version history** — operational evolution-governance implementation. Any semantic gap it exposes must enter this candidate map separately.

## Admission rule

A tracked candidate is not admitted merely because it appears here. Before entering a daily successor materialization it must pass:

- at least 3 independent qualified reviewer families/checkpoints on the **same bounded target**, preferably 4+;
- blind review before peer cross-examination;
- evidence-ancestry/correlation analysis;
- whole-source collision/equivalence review;
- applicable GSL-COMPARE / DO_NOTHING, Reason, Proof, Evidence, AAP, authority and ActionGate checks;
- tests/invariants/contracts and dependency revalidation;
- cross-delta consistency, predecessor retention and reference closure.

The final daily successor remains a **candidate** until the separate human canonical-promotion boundary is satisfied.
