# OpenRouter model value review — 2026-09-19

Status: operational evidence only. This is not a general model-quality ranking and grants no Garden authority.

## Basis

Observed during the Garden v15.10 three-artifact redesign campaign: four adversarial rounds plus the low-cost final confirmation. Costs are OpenRouter-reported generation costs from the preserved review artifacts. "Visible answers" means a substantive final answer was actually returned and usable.

| Family / model | Calls | Visible answers | Observed total cost (USD) | Operational lesson |
|---|---:|---:|---:|---|
| Xiaomi MiMo-V2.5-Pro | 5 | 4 | 0.029339 | Very high value; concrete implementation and interaction failures. |
| Mistral Medium 3.5 | 5 | 3 | 0.044184 | Strong edge-case, serialization, ordering and final-cleanup reviewer. |
| NVIDIA Nemotron 3 Ultra | 5 | 4 | 0.067106 | Strong architecture/boundary challenger; sometimes over-expansive but useful. |
| Pareto | 5 | 4 | 0.091934 | Strong at false equivalence, assurance language and proof/claim discipline. |
| DeepSeek V4 Pro | 5 | 2 | 0.110843 | Output reliability was uneven, but the usable answers found major late blockers at very low marginal cost. |
| GLM 5.3 | 5 | 1 | 0.192461 | One sharp formal review, insufficient visible-output reliability for quorum. |
| Grok 4.6 | 4 | 4 | 0.218630 | Strong concrete adversarial counterexamples; not needed routinely at current cost. |
| Gemini 3.1 Pro | 4 | 4 | 0.218772 | Creative second-order failure detection; escalation only. |
| Qwen 3.8 | 4 | 2 | 0.312358 | Some strong formal reviews but inconsistent visible output. |
| Kimi K3 | 4 | 2 | 0.658184 | Useful but weak routine price/value. |
| GPT-6 Astra | 4 | 4 | 0.746758 | Strong sustained architecture reviewer; expensive relative to routine board. |
| Claude Opus 5 | 4 | 3 | 1.163520 | Strong on self-certification/epistemic claims; expensive and not routine. |
| Fugu Ultra v2 | 4 | 3 | 4.725527 | Deep qualifier/equation/state-order review; prohibit automatic use due cost. |

Total observed campaign cost across these calls was approximately USD 8.58.

## Decision

Routine board:
1. DeepSeek — determinism, hidden inputs, derivation.
2. MiMo — implementation interactions and failure cases.
3. Nemotron — architecture boundaries, ownership, scale.
4. Pareto — equivalence, proof and assurance claims.
5. Mistral — serialization, state/order/timing and edge cases.

GLM is shadow-only until visible-output reliability improves.

Expensive models are never automatic. A future human may explicitly opt in to one for a specific unresolved question.

## Important interpretation

A valid material counterexample from one reviewer overrides any number of approvals. Agreement is evidence, not Proof. Price or benchmark reputation does not create authority.
