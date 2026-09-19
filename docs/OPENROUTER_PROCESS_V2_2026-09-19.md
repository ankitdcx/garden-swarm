# Garden OpenRouter Review Process v2 — 2026-09-19

Status: active noncanonical operational process. It changes review workflow only; it does not change Garden semantics or grant authority.

## Default principle

Use deterministic checks first. Call OpenRouter only for a material question that still needs independent model review.

The default board is five cheap specialist families:

- DeepSeek — determinism, hidden inputs, derivation.
- Xiaomi MiMo — implementation interactions and practical failure cases.
- NVIDIA Nemotron — architecture boundaries, ownership and scalability.
- Pareto — equivalence, proof language and assurance claims.
- Mistral — serialization, ordering, state transitions, timing and edge cases.

Each receives the same source packet independently. No reviewer sees another reviewer's answer.

## Normal process

1. Run local deterministic checks first.
2. ChatGPT writes and hashes a private baseline before any OpenRouter inference.
3. **Blind round:** send the same neutral packet to all five specialist reviewers.
4. Record every returned finding; `NO_SUBSTANTIVE_OUTPUT` is a transport/result state, not approval.
5. ChatGPT verifies each finding against the source and local tests. A finding ledger records retain/reject/integrate/unresolved with evidence.
6. If all five say NO_CHANGE and local gates remain clean, close after five calls.
7. If a valid finding changes the candidate, integrate it, rerun deterministic tests, then send the bit-identical repaired candidate to all five for final review.
8. If final review finds one valid material patch, repair once and use at most one five-reviewer confirmation round.
9. If a material dispute remains after confirmation, stop with an explicit unresolved receipt. Do not loop and do not automatically buy a more expensive model.

Normal changed-candidate path: 10 calls.
Easy no-change path: 5 calls.
Absolute task maximum: 15 calls.

## Budget

- Default daily OpenRouter ceiling: USD 1.00.
- Routine task ceiling: USD 0.25.
- Per-call reservation ceiling: USD 0.05.
- Dated audit mode: at most USD 2/day and USD 0.50/task.
- Automatic expensive escalation budget: USD 0.

Budget exhaustion means stop/defer. It never authorizes weaker review, missing context, peer-answer sharing or silent model substitution.

## Finding ledger

Each material finding must be normalized to:

- finding ID;
- reviewer family;
- candidate hash;
- affected owner/location;
- challenged claim;
- concrete counterexample or gap;
- severity;
- proposed patch;
- ChatGPT reproduction status;
- disposition;
- patch reference;
- regression test;
- candidate hash that closed it.

Repeated findings attach to the same issue rather than creating duplicate prose.

## No voting

Five approvals do not prove correctness. One reproducible material counterexample is sufficient to block or patch. ChatGPT integrates based on source/evidence/tests, not majority vote.

## Empty output

If a provider call succeeds but produces no usable visible answer, record `NO_SUBSTANTIVE_OUTPUT`. Do not automatically retry the same unchanged packet. A later materially changed candidate may call that family again.

## Expensive models

Astra, Claude, Gemini Pro, Grok, Qwen large, Kimi and Fugu are not part of the automatic process. They require an explicit future human opt-in for a specific unresolved question.

## Provider routing

The 2026-09-19 human directive re-authorizes NVIDIA/Nemotron and Mistral for low-cost Garden review. Anthropic/Claude remains excluded by the current operator-routing policy.

## Evidence boundary

OpenRouter outputs remain proposal evidence. They cannot create truth, Proof, authority, canonical status, merge permission or human admission.
