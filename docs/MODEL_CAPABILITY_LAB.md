# Model Capability Comparison Process v1.0 — First Executable Epoch

Status: FROZEN_FOR_EPOCH_1. Incorporates the independent 2026-10-05 protocol attacks. No rule changes after item generation begins.

## Measurement
Primary: at least 200 fresh procedurally generated common reasoning items with locally computed deterministic keys. Secondary: each participating model authors 10 reciprocal adversarial questions. Reciprocal questions never replace the common comparison.

## Roles and exposure
Authoring, admission, solving and adjudication use isolated sessions. Prior item/key exposure is recorded and disqualifies that solver-item observation from fully blind scoring.

## Reciprocal items
Before solving, freeze question, intended answer, assumptions, category, difficulty claim, scoring rule and ambiguity note. Reject trivia, subjective/current/private knowledge, tokenizer/character/string/spatial exploits, model-identity questions, unverifiable keys and wording traps. Independent key validation is required. Defective items remain author-quality evidence.

## Common items
Use parametric families spanning arithmetic dependency, modular recurrence, constraint/order, graph/path, probability, sets, causal intervention, scheduling, base conversion and consistency/logic. Freeze generator version, seed and hashes before solving. Retire items after first transmission.

## Solving and comparability
Same substantive instructions; no tools/web/files/memory. Record exact model/provider/version, visible budgets, latency, cost and transport state. Hidden reasoning budgets are not assumed equivalent; also report accuracy/cost and latency frontiers. Two pre-registered semantically equivalent solver wrappers are randomly assigned to disjoint common-item halves.

## Failure semantics
Valid answer scores normally. Refusal/invalid/malformed answer to a valid item is incorrect. Provider/transport/no-visible-text failure is TRANSPORT_FAILURE, not reasoning failure; report capability conditional on availability and end-to-end reliability separately. Unavailable/price-blocked is UNAVAILABLE, never zero capability.

## Verification/disputes
Deterministic verification first. Author keys/checkers are independently validated. Open answers are normalized/anonymized and unresolved items get at least three independent judges where affordable. Majority is not truth: a verified counterexample overrides votes. Remaining disputes stay DISPUTED and appear in sensitivity analysis.

## Home-field
Exclude self-authored questions from primary reciprocal score. Report peer accuracy by author family/category. Author quality combines validity, rejection/ambiguity rate, empirical difficulty and discrimination; trivial survival alone is not rewarded.

## Statistics
Common accuracy uses Wilson 95% intervals. Pairwise common-item differences use paired bootstrap with Holm correction. Practical-equivalence margin is 3 percentage points. A>B requires corrected significance and a difference outside that region; otherwise report INDISTINGUISHABLE_AT_CURRENT_POWER or INCONCLUSIVE. Reciprocal results remain secondary because author clustering/home-field dependence persists.

## Cost enforcement
Provider daily usage remains authoritative. Pre-call estimates reserve at least a 35% safety margin under the per-call ceiling. An observed ceiling overrun is a protocol incident and blocks further calls to that model in the epoch.

## Reporting/rating
Publish common accuracy/CI, reciprocal peer accuracy, author quality, category/author breakdown, transport reliability, invalid/refusal rate, latency, cost, Pareto position, pairwise status and disputes. A user-facing Epoch Rating 0-100 may be shown only as a descriptive index: 70% common accuracy + 20% reciprocal peer accuracy + 10% reliability. Missing reciprocal data makes it PROVISIONAL. Pairwise statistical conclusions remain primary; this is not a universal intelligence number.

## Boundary
Scores are empirical evidence only. No score creates truth, Proof, authority, permission, canonical status or automatic model selection.
