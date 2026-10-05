# Model Capability Comparison Process v0.1 — Frozen Review Target

Status: FROZEN_FOR_ADVERSARIAL_REVIEW. No implementation or capability run is authorized by this document.

## Objective
Measure comparative reasoning capability across model families while isolating reasoning from web/filesystem/compiler/tools, memory, agent infrastructure, static benchmark memorization, popularity and reputation. Execution after protocol freeze will use OpenRouter where exact models are available.

## Review-before-run
Freeze this process; send the identical protocol to independent model families; preserve raw reviews without cross-talk; accept changes only for concrete failure/bias scenarios; reconcile and freeze v1.0 before generating real test items.

## Roles
Separate author, admissibility reviewer, solver and verifier/adjudicator. Any overlap is recorded; prior exposure to an item/key disqualifies that observation from fully blind primary scoring.

## Test structure
A common independent set plus reciprocal challenges. Each participant authors an equal number (initially 10) of novel questions. Before seeing solver answers, freeze question, answer, scoring rule, assumptions, ambiguity analysis, category, difficulty rationale, verification method and SHA-256.

## Admissibility
Items must be novel, self-contained, text-only, reasoning-focused and independent of current web/private knowledge/tools. Reject trivia, subjective taste, obscure recall, wording traps, tokenizer/subword or character-counting exploits, string reversal, ASCII/spatial tricks, model identity, inaccessible information and unverifiable answers. Normalize notation where practical. Defective items reduce authoring quality.

## Author quality
Do not reward survival alone. Measure validity plus empirical discriminative power/difficulty. Trivial indisputable items cannot maximize author quality.

## Blind solving
Equivalent instructions, information, restrictions, answer format and comparable resource budgets. Record exact model/version/provider/time/temperature/top_p/seed/token or reasoning limits. Randomize item order. No competitor answers, hidden keys, scores or adjudication. Authoring/solving/adjudication use isolated sessions. Self-authored solving is separate and excluded from primary reciprocal accuracy.

## Cross-model comparability
Identical API parameters are not assumed equivalent. Report resource conditions and accuracy-versus-cost/compute Pareto frontiers rather than a fabricated cost-adjusted scalar.

## Verification
Prefer deterministic/formal verification. Authors cannot unilaterally control representation-biased checkers. Equivalent correct answers must be accepted where appropriate.

## Open-answer adjudication
Use frozen rubric, structural/style normalization, anonymization, multiple independent adjudicators and inter-rater agreement. Permit explicit counterexamples.

## No majority-vote truth
Consensus does not establish correctness. A counterexample must itself be verified. Unresolved items become DISPUTED/UNKNOWN; do not force consensus.

## Dispute transparency
Report dispute count, difficulty, author family, disagreement and reason; show sensitivity with/without disputed items where meaningful.

## Home-field effects
Report peer-authored accuracy by author family/category, self-authored results separately, and representation/style effects.

## Statistics
Pre-register scoring, exclusions, stopping rule, statistical model, equivalence margin, multiple-comparison correction, minimum power/sample and any composites. Use paired/mixed-effects or IRT-style analysis. Strong claims require hundreds of observations across fresh epochs. Within the practical-equivalence region report INDISTINGUISHABLE, not an artificial rank.

## Longitudinal measurement
Use fresh epochs. Published/leaked primary items are retired. Link epochs using secret never-published anchors and/or procedural generators with controlled difficulty distributions; pre-register calibration.

## Contamination
No actual test items during protocol review. Generate the first item bank only after v1.0 freeze. Treat transmission to an external provider as potential exposure. Preserve hashes/timestamps/provenance.

## Calibration/consistency
Confidence calibration requires confidence reports and sufficient observations. Consistency requires repeated samples under a pre-registered policy; one deterministic response cannot establish consistency.

## Prompt robustness
Use multiple pre-registered semantically equivalent prompt variants where feasible and report sensitivity. Never select a prompt post-hoc to favor a model.

## Human-grounded validation
Include an independently validated slice for benchmark validity, ambiguity, disputed keys and category validity so the system is not solely models grading models.

## Adjudication scaling
If full cross-adjudication is too costly, use pre-registered stratified random adjudication: multiple independent judges per open/disputed item, randomized assignment, minimum coverage, and extra verification for difficult/high-impact disputes.

## Reporting
Per model: common accuracy; reciprocal peer-authored accuracy; author-family/category breakdown; author validity/discrimination; refusal/invalid rate; calibration/consistency where supported; latency/tokens/cost; accuracy-cost Pareto position; uncertainty intervals.

Primary pairwise conclusions: A>B WITH EVIDENCE; B>A WITH EVIDENCE; INDISTINGUISHABLE AT CURRENT POWER; INCONCLUSIVE; DISPUTED. Non-significance is not proof of equality.

After deterministic analysis, models may independently challenge anonymized results. Label cross-model consensus only where conclusions survive counterexample checking. Preserve disagreements.

Never publish a universal intelligence scalar. Report profiles, pairwise distinctions, uncertainty, cheap-vs-frontier gap, category differences, Pareto frontier, longitudinal change and evidence strength.

## Execution/audit
After v1.0 freeze, run through OpenRouter where exact models exist. Preserve protocol version -> epoch -> item provenance/hashes -> exact models/settings -> raw answers -> verification -> disputes -> statistics -> conclusions.

## Boundary
Benchmark performance is empirical evidence only. It grants no truth, Proof, authority, canonical status, permission or automatic model-selection power.
