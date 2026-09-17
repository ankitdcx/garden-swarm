# Garden v15.9 Wave 1 — ChatGPT independent baseline

Status: FROZEN BEFORE EXTERNAL MODEL REVIEW. Proposal evidence only.
Scope: P012–P016.
Rule: initial external reviewers MUST NOT receive this file.

## P012 — Algebras
Candidate findings/hypotheses:
1. Decision Algebra is under-specified relative to its claim of independent algebra status; either define typed operands/operators/laws/non-laws or merge its semantics into the generic Result/Policy result owner.
2. Policy Algebra needs an explicit conservative composition table for INDETERMINATE/CONFLICT/NOT_APPLICABLE/approval sets; NOT_APPLICABLE should act as contextual absence only when applicability is established, never as implicit permit.
3. Exception/precedence semantics need proof that lower-authority exceptions cannot weaken higher hard constraints.
4. Conformance PASS must require complete mandatory applicability/coverage closure; partial mapping or stale evidence cannot compose to PASS.
5. Evidence Algebra should distinguish support aggregation from evidence-independence assessment; circular/shared-root evidence needs well-founded grounding or explicit dependence model.
6. Cross-algebra results need a typed interface so PolicyDecision, ConformanceResult and EvidenceComposition cannot be substituted for each other merely because they use similar status labels.

## P013 — Compare
Candidate findings/hypotheses:
1. Comparison should be fundamentally partial-order / constraint-aware; universal scalar score would be unsafe and semantically lossy.
2. ComparePolicy should version materiality/tolerance/scalarization choices and expose which dimensions are policy/value judgments versus measured/formal dimensions.
3. Comparison outputs need separate result types for epistemic support, design quality, feasibility/constraints and adoption recommendation.
4. Mandatory closure retrieval needs a receipt showing required symbolic/dependency/policy/invariant sets were considered; ranked retrieval cannot establish closure.
5. Counterfactual replay requires explicit model/identification/transportability status and cannot be counted as fresh empirical evidence.
6. Comparator evolution must invalidate prior calibration where applicable and cannot self-certify changes to its own protected evaluation rules.

## P014 — Reason
Candidate findings/hypotheses:
1. R1–R4 should specify obligation classes, not implementation-specific compute amounts; deeper tiers add breadth/independence/adversariality/validation planning rather than simply 'more tokens'.
2. Reason result algebra needs explicit PARTIAL/INCONCLUSIVE/UNKNOWN/CONTRADICTED/RESOURCE_LIMIT/MODEL_OUT_OF_SCOPE/VALIDATION_REQUIRED.
3. Strategy selection must be separated from strategy self-evaluation; benchmark/performance evidence should bind evaluator, dataset/context, leakage risk and external outcome where possible.
4. Mixed strategies need a composition trace and termination/resource contract; disagreement among solver/LLM/simulation outputs remains explicit.
5. Abstraction and backward/preimage reasoning need soundness/over-approximation annotations so necessary-condition analysis is not presented as exact causality.
6. Reasoning portfolio evolution should use independent evaluation and DesignEpoch invalidation for protected selection rules.

## P015 — Proof + Explanation
Candidate findings/hypotheses:
1. V1 'ordinary validation' risks blurring formal Proof with tests/empirical validation; rename/refine tiers so Proof remains formal/structural while AssurancePlan may combine non-proof bases.
2. ProofAttemptResult should distinguish PROVED, COUNTEREXAMPLE/DISPROVED, UNKNOWN, INCONCLUSIVE, TIMEOUT, RESOURCE_UNKNOWN, STALE, NOT_APPLICABLE, MALFORMED and CHECKER_UNTRUSTED where relevant.
3. Proof certificates must bind exact assumptions, logic/checker/version, dependency root and environment; proof reuse needs compatibility evidence.
4. Explanation faithfulness should bind each material statement to trace/evidence/proof/policy source or mark it as synthesis/uncertainty.
5. Explanation must support privacy-preserving contestability: a redaction status itself can leak protected membership.
6. WHY/causal explanations need typed distinction among causal trace, decision rationale, heuristic attribution and unknown cause.
7. No separate Explanation Algebra appears necessary unless repeated composition laws cannot be represented as Process + typed projection.

## P016 — Orchestrate / Search / Compile / Transition
Candidate findings/hypotheses:
1. Orchestration replanning needs versioned ActivationPlan state and bounded recursion; mid-process change should invalidate only affected plan closure.
2. Search should have separate MandatoryClosureResult and RankedRetrievalResult; incomplete mandatory retrieval is not equivalent to low relevance.
3. Search result provenance/staleness/coverage should be explicit; diversity/negative evidence should not depend solely on similarity ranking.
4. Compile needs a SemanticPreservationReceipt or translation-validation contract between accepted source semantics, CIR and target artifact; successful build is insufficient.
5. Compiler/generator trust-boundary changes require independent baseline verification; a new compiler cannot be sole verifier of its own semantic equivalence.
6. Transition should expose PREPARED / ADMITTED / COMMITTED / EFFECT_APPLIED / OUTCOME_UNKNOWN / RECONCILED phases or equivalent typed semantics to close partial-effect and retry ambiguity.
7. Transition commit authority and effect authorization must remain point-of-use fresh; post-hoc receipts cannot retroactively authorize effects.
8. Cross-engine Search↔Reason↔Orchestrate recursion needs explicit call/dependency/resource termination contracts to avoid hidden cyclic work amplification.
