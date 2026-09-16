# Garden OpenRouter independent-branch convergence

Status: active noncanonical operating protocol for Garden OpenRouter model-inference work.

The public worker uses the existing `OPENROUTER_API_KEY` Actions secret. OpenRouter is not allowed to run a peer-sharing debate. The active protocol is `GardenIndependentBranchConvergencePolicy/v1` in `agents/independent-branch-convergence-policy.json`.

The broad Coordinator and legacy batch workers remain paused/not admitted. The bounded single-call worker can make at most one model inference per dispatch. No model output can merge code, establish truth/Proof, mint authority, or promote Garden semantics.

## Core process

For every Garden task that uses OpenRouter model inference:

1. **ChatGPT baseline first.** ChatGPT independently answers the task before any OpenRouter inference. The baseline content stays outside the public OpenRouter lane. The repository receives only a SHA-256 commitment binding the baseline, neutral query and source packet.
2. **Four blind branches.** DeepSeek, Qwen, GLM and Xiaomi/MiMo receive the same neutral query and source packet one after another. They do not receive ChatGPT's baseline or another model's answer.
3. **One-to-one reconciliation.** ChatGPT compares its baseline with each branch separately. A branch follow-up may contain only the same source packet, that model's own prior branch response, and ChatGPT's branch-specific merged candidate. Default is one follow-up; maximum is two. No response or summary from another branch is allowed.
4. **Four reconciled branch results.** ChatGPT then holds four separately reconciled versions. Models do not synthesize across branches.
5. **ChatGPT synthesis.** ChatGPT merges the four branch results and records common conclusions, material disagreements, evidence differences, surviving counterexamples, discarded alternatives, the DO_NOTHING alternative and uncertainty.
6. **Four isolated final reviews.** The bit-identical merged candidate is sent separately to all four reviewers. Each returns `APPROVE`, `BLOCK`, or `APPROVE_WITH_PATCH`. No final reviewer sees another final review.
7. **At most one confirmation round.** If a material block/patch is valid, ChatGPT reintegrates it and the bit-identical revised candidate may be sent once more to all four reviewers. If material disagreement survives, the task stops and escalates with an explicit disagreement receipt rather than looping.

Four-of-four agreement is never Proof. Closure still depends on applicable Garden Compare/Reason/Proof/Evidence/AAP/authority/ActionGate/human boundaries.

## Why peer sharing is forbidden

The predecessor worker used blind review followed by peer cross-examination: later prompts could include other models' findings. That can create correlated convergence and make apparently independent reviewers anchor on one another.

That behavior is superseded for new OpenRouter work. `free_swarm.cross_examination` and `specialist_free_sweep.cross_examination` are false. Legacy tools that contain peer-sharing logic remain historical/reference compatibility only; their outputs are not current `GardenIndependentBranchConvergence/v1` evidence.

## Durable ChatGPT handoff

The public worker cannot create ChatGPT's baseline or cross-branch synthesis. A durable external ChatGPT directive is staged on the `garden-review-state` branch at `review-state/convergence-directive.json` using `GardenIndependentBranchDirective/v1`.

The directive is public-only and contains a baseline commitment, not baseline text. It binds the exact target, source-packet hash, ordered reviewer families and protocol phase.

Supported phases:

- `BLIND`: same neutral packet for four sequential reviewers.
- `RECONCILE`: exactly one reviewer family, branch round 1 or 2, its own prior response hash, and ChatGPT's branch-specific candidate; no peer content.
- `FINAL`: one merged candidate hash; exact same candidate to all four.
- `CONFIRM`: one revised candidate hash; exact same candidate to all four; confirmation round equals 1.

Changing candidate bytes within a final/confirmation round fails closed.

## Execution and continuation

The active queue covers explicitly registered public targets in `agents/design-review-matrix.json`. Private candidate content is not sent by this lane. Canonical inputs are source-hash bound; public implementation inputs are bounded to registered paths.

`tools/independent_branch_worker.py` is the active inference transport. `tools/independent_branch_continuation.py` can automatically dispatch the next family only when the current phase itself uses the same packet and remains isolated (`BLIND`, `FINAL`, or `CONFIRM`). It cannot invent ChatGPT reconciliation directives.

A main-branch source/protocol change moves the queue to `AWAITING_CHATGPT_BASELINE_OR_DIRECTIVE`. Clock passage cannot create a baseline, directive, query or review task. The daily recovery wake can only recover already-admitted transport state.

## Calls and spending

Limits remain:

- one inference call per dispatch;
- one concurrent model call maximum;
- `$0.05` reservation ceiling per routine call;
- `$1.00` OpenRouter ceiling per UTC day;
- `$9` routine lifetime allocation from the original `$20` pool;
- **20 OpenRouter inference calls absolute maximum per convergence task**.

The ceiling is `4 blind + up to 8 branch follow-ups + 4 final + up to 4 confirmation = 20`. Easy work can finish at 8 calls; normal work is expected around 12. Budget exhaustion stops/defers work; it never authorizes dropping a required reviewer, weakening assurance, or sharing branches.

## Persistent state, identity and failures

The `garden-review-state` ledger preserves reservations, answers, generation identities, costs, queue status and protocol receipts. SHA-conditional writes reserve the effect before transport. Unknown completion or unknown billing blocks further inference rather than authorizing a blind retry.

Generation reconciliation remains conservative: completion-reported and finalized generation costs are both retained and the larger known amount is charged. Requested model IDs and canonical/versioned model identities are checked against live catalog evidence before new calls and during reconciliation. Mismatching model/provider identity remains a visible failure.

HTTP diagnostics retain bounded status/category/error-body hash and an allowed generation ID when supplied, never raw provider error text or headers. Those diagnostics do not prove zero billing.

Old unresolved responses remain evidence. A superseded-protocol response is never silently reclassified as valid v1 convergence evidence.

## Model board

Routine four-family value board:

- DeepSeek V4.1 Flash
- Qwen3.8 Flash
- GLM 5.3 Flash
- Xiaomi MiMo-V2.5

Model identities remain pinned until a later catalog-review event. Anthropic/Claude, NVIDIA/Nemotron and Mistral/Mistral AI remain excluded. Separate Gemini and ChatGPT lanes do not replace the four OpenRouter branches.

## Live activation evidence inherited from the predecessor worker

The predecessor single-call transport demonstrated automatic dispatch and durable billing reconciliation before this convergence redesign. Run `35097894001` recorded a valid DeepSeek review with finish reason `stop` and reported cost `$0.0013029`, then automatically dispatched Qwen. Together with the earlier incomplete DeepSeek call at `$0.0011595`, known billed spend was `$0.0024624`.

Qwen run `35097998039` then returned an HTTP error through an Alibaba endpoint and left cost/completion UNKNOWN. Its original receipt did not preserve a generation identity. That historical call remains **BLOCKED pending external evidence** from OpenRouter activity around 2026-09-16 12:48:50 UTC (generation ID if any, status, provider and cost). Do not reset, delete, invent zero cost, or treat it as current v1 convergence evidence.

The later HTTP-diagnostics repair can preserve safer evidence for future failures, but cannot reconstruct fields that were not retained by that historical Qwen call. The new worker must therefore inherit the conservative blocker: unidentified/unknown-billing prior inference prevents new inference until evidence-based reconciliation.

This live evidence proves parts of the transport, reservation and continuation path; it does not prove the new four-branch convergence protocol has completed a live end-to-end task.

## Evidence boundary

A completed convergence protocol produces proposal evidence only. It does not establish whole-Garden coverage, semantic correctness, canonical promotion, legal status, authority or human admission. Agreement itself is never the stopping criterion; the stopping criterion is absence of unresolved material contradiction, counterexample, evidence gap, violated invariant or stronger known alternative at the required assurance level.
