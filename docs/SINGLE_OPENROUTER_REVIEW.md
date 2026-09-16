# Garden OpenRouter independent-branch convergence

Status: active noncanonical operating protocol for Garden OpenRouter model-inference work.

The public worker uses the existing `OPENROUTER_API_KEY` Actions secret, but OpenRouter is no longer allowed to run a peer-sharing debate. The active protocol is `GardenIndependentBranchConvergencePolicy/v1` in `agents/independent-branch-convergence-policy.json`.

The broad Coordinator and legacy batch workers remain paused/not admitted. The bounded single-call worker can make at most one model inference per dispatch and no model output can merge code, establish truth/Proof, mint authority, or promote Garden semantics.

## Core process

For every Garden task that uses OpenRouter model inference:

1. **ChatGPT private baseline first.** ChatGPT independently solves the task before any OpenRouter inference. The baseline content stays outside the public OpenRouter lane. The repository receives only a SHA-256 commitment proving that a baseline, neutral query and source packet were fixed first.
2. **Four blind branches.** DeepSeek, Qwen, GLM and Xiaomi/MiMo receive the same neutral query and the same source packet, one after another. They do not receive ChatGPT's baseline or another model's answer.
3. **One-to-one reconciliation.** ChatGPT compares its private baseline with each branch separately. A branch follow-up may contain only the same source packet, that model's own previous branch response, and ChatGPT's branch-specific merged candidate. Default is one follow-up; maximum is two. No response or summary from another branch is allowed.
4. **Four reconciled branch results.** ChatGPT then holds four separately reconciled versions. Models do not synthesize across branches.
5. **ChatGPT synthesis.** ChatGPT merges the four branch results and records common conclusions, material disagreements, evidence differences, surviving counterexamples, discarded alternatives, the DO_NOTHING alternative and uncertainty.
6. **Four isolated final reviews.** The bit-identical merged candidate is sent separately to all four reviewers. Each returns `APPROVE`, `BLOCK`, or `APPROVE_WITH_PATCH`. No final reviewer sees another final review.
7. **At most one confirmation round.** If a material block/patch is valid, ChatGPT reintegrates it and the bit-identical revised candidate may be sent once more to all four reviewers. If a material disagreement still survives, the task stops and escalates with an explicit disagreement receipt rather than looping.

Four-of-four agreement is never Proof. Closure still depends on applicable Garden Compare/Reason/Proof/Evidence/AAP/authority/ActionGate/human boundaries.

## Why peer sharing is forbidden

The previous worker used blind review followed by peer cross-examination: every model could receive the previous round's other-model findings. That can create correlated convergence and make apparently independent reviewers anchor on one another.

That behavior is superseded for new OpenRouter work. `free_swarm.cross_examination` and `specialist_free_sweep.cross_examination` are now false. Legacy tools that contain peer-sharing logic remain only for historical/reference compatibility; their outputs are not current `GardenIndependentBranchConvergence/v1` evidence.

## Durable ChatGPT handoff

The public worker cannot create ChatGPT's private baseline or branch synthesis. A durable external ChatGPT directive is staged on the `garden-review-state` branch at:

`review-state/convergence-directive.json`

Directive schema: `GardenIndependentBranchDirective/v1`.

The directive is public-only and contains a baseline **commitment**, not the private baseline text. It binds the exact target, source-packet hash, ordered reviewer families and protocol phase.

Supported phases:

- `BLIND`: same neutral packet for four sequential reviewers.
- `RECONCILE`: exactly one reviewer family, branch round 1 or 2, its own prior response hash, and ChatGPT's branch-specific candidate. The directive must attest that no peer content is present.
- `FINAL`: one merged candidate hash; exact same candidate to all four.
- `CONFIRM`: one revised candidate hash; exact same candidate to all four; confirmation round must equal 1.

Changing candidate bytes within a final/confirmation round fails closed.

## Execution and scope

The active queue still covers the explicitly registered public targets in `agents/design-review-matrix.json`. Private candidate content is not sent by this lane. Canonical inputs are source-hash bound; public implementation inputs are bounded to registered source paths.

`tools/independent_branch_worker.py` is the active inference transport. `tools/independent_branch_continuation.py` may automatically dispatch the next family only when the protocol phase itself is same-packet and isolated (`BLIND`, `FINAL`, or `CONFIRM`). It does not invent ChatGPT reconciliation directives.

A main-branch source/protocol change moves the queue to `AWAITING_CHATGPT_BASELINE_OR_DIRECTIVE`. Clock passage cannot create a baseline, a directive, a query, or model work. The daily recovery wake can only recover already-admitted transport state.

## Calls and spending

Limits remain:

- one inference call per dispatch;
- one concurrent model call maximum;
- `$0.05` reservation ceiling per routine call;
- `$1.00` OpenRouter ceiling per UTC day;
- `$9` routine lifetime allocation from the original `$20` pool;
- **20 OpenRouter inference calls absolute maximum per convergence task**.

The 20-call ceiling is derived as:

`4 blind + up to 8 branch follow-ups + 4 final + up to 4 confirmation = 20`.

Typical work should use fewer calls. Easy tasks can finish at 8 calls (four blind + four final). A normal task is expected around 12 calls (one branch follow-up each). Budget exhaustion stops/defers work; it never authorizes dropping a required reviewer, weakening assurance, or sharing branches to save money.

## Persistent state and failures

The `garden-review-state` ledger preserves reservations, response identities, exact/finalized billing, model/provider identity and protocol receipts. Existing transport reconciliation remains conservative: the larger known completion/final-generation cost is charged.

Old unresolved responses are preserved as evidence. A superseded protocol response is not silently reclassified as valid v1 convergence evidence. Unknown identity or unknown billing blocks new inference.

The active worker accepts a returned versioned model identity only when it is the exact requested pinned model or a version-qualified identity beginning with that pinned model ID; the exact actual model/provider is still recorded.

## Model board

Routine four-family value board remains:

- DeepSeek V4.1 Flash
- Qwen3.8 Flash
- GLM 5.3 Flash
- Xiaomi MiMo-V2.5

Model identities remain pinned until a later model-catalog review event. Anthropic/Claude, NVIDIA/Nemotron and Mistral/Mistral AI remain excluded. The separate Gemini and ChatGPT lanes do not replace the four OpenRouter branches.

## Evidence boundary

A completed protocol produces proposal evidence only. It does not establish whole-Garden coverage, semantic correctness, canonical promotion, legal status, authority, or human admission. Agreement itself is never the stopping criterion; the stopping criterion is absence of unresolved material contradiction, counterexample, evidence gap, violated invariant or stronger known alternative at the required assurance level.
