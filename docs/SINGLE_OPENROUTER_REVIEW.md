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
- `$0.10` reservation ceiling per call;
- `$2.00` default OpenRouter ceiling per UTC day; a dated, target-bound AUDIT plan may select `$10.00`;
- `$9` routine lifetime allocation from the original `$20` pool;
- **20 OpenRouter inference calls absolute maximum per target/source task, including context expansions**.

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

## Source-backed context and adaptive review depth

The active worker now verifies all five canonical public files against
SOURCE_MANIFEST before constructing a review packet. It includes the exact
canonical overview (reader guide, status distinctions, architecture and whole-system
loop), the target section, and retrieved dependency/mitigation passages. Every
passage retains its file hash, exact line positions and excerpt hash. The initial
five-file corpus produces 532 indexed passages. Source changes rebuild the index;
cache corruption cannot replace canonical source text.

The local index is reused through Actions cache. The cache stores already-public
source, never credentials, private baseline text or private candidate deltas.
Context selection is deterministic. The packet binds the release, complete source
manifest, retrieval policy, profile, supplied passages and explicit omission counts.
It does not claim full dependency closure or that omitted material is absent from
Garden. Exact retrieval is not proof, empirical validation or whole-design review.

| Profile | Generated-token ceiling | Source-context character budget | Reasoning request |
| --- | ---: | ---: | --- |
| ROUTINE | 8,000 | 32,000 | medium |
| COMPLEX | 16,000 | 64,000 | high |
| DEEP | 32,000 | 100,000 | high |

HIGH-risk targets use at least COMPLEX; theories, cross-module targets and CRITICAL
work use DEEP. A directive may request greater depth but cannot lower the floor.
These are starting budgets, not guarantees of sufficient reasoning. Generated-token
ceilings include model reasoning where applicable. The old 1,800-visible-token
instruction is removed. The worker does not force low reasoning for complex work.
Reasoning controls are sent only where advertised; receipts disclose native defaults
when no explicit control can be sent. A live endpoint with insufficient output,
prompt or total context limits is rejected instead of silently shrinking the review.
The full assembled prompt, input byte bound, output budget and live prices must fit
the reserved cost. Timeouts increase with depth while each dispatch stays bounded.

Every active review phase explicitly asks: "Please find any defects or gaps or
worthy upgrades." NO_CHANGE is valid. Findings must check existing mitigations;
missing context must be named rather than treated as a missing Garden mechanism.

## Rebuilding a context packet

Build a packet offline, without calling a model:

```sh
python -m tools.review_context --target DRM-H01-CONSTITUTIONAL-EVENT-BOUNDARY --output /tmp/garden-context.json
```

The command prints the exact packet hash and neutral-query hash for the existing
private-baseline commitment. Use the printed packet hash as source_packet_sha256
in both the directive and its baseline commitment. Baseline text remains private.
The packet may also be inspected with --profile DEEP, --query followed by a bounded
concept, or --chunk followed by an exact passage ID from the omission list/index.
Each changed packet requires a renewed ChatGPT baseline commitment and a new blind
round with that identical packet for all reviewers. Context expansion cannot reset
the task's 20-call limit or create a new spending allowance.

Models may return requested_context as an array of objects containing a query or
chunk_id. These requests enter a durable context_request_queue and stop inference
at AWAITING_CHATGPT_CONTEXT. ChatGPT checks whether each is a neutral source request,
retrieves exact passages and builds a renewed shared packet. An expanded directive
must set context_requests_reviewed_as_neutral to true. Raw branch answers or
inferred peer conclusions must never be passed as additional source context.
This is a deterministic retrieval/handoff facility; it does not claim the external
ChatGPT synthesis step runs unattended in GitHub Actions.

A dedicated matrix target, DRM-X01-AUTHORITY-EXECUTION-RECOVERY, checks interfaces
between authority, AAP, Runtime, transition contracts, time/events and recovery.
The matrix now contains eleven bounded targets. That remains smaller than the
whole Garden design and its theories.

## Dated audit mode and remaining funds

Default spending remains event-driven: a ceiling is not a spending target.
Per-call $0.10 and per-day $2 are upper limits. Selecting AUDIT requires a directive
with spending_mode AUDIT and audit_window fields utc_day, target_id, audit_id and
purpose. The date must equal the current UTC day and the target must match the
directive. The shared daily ceiling becomes $10 only for that admitted work.
Expired audit plans fail closed; they never renew automatically.

The original pools remain $9 routine, $3 challenger, $5 escalation and $3 emergency.
AUDIT still draws only from routine funds; a $10 daily limit cannot override the
$9 lifetime allocation or borrow the other $11. Those funds are not silently
reallocated. Provider-reported spend and conservative local accounting can cause an
earlier stop. Raising or refilling a lifetime allocation requires a separate actual
budget decision. Unknown billing still blocks both spending modes.

All response, context, profile, cost and identity receipts remain proposals. Before
integrating a recommended change, require a reproducible regression/falsification
check or keep its missing evidence as an explicit unverified obligation. Periodic
quality comparison on known-defect cases is recommended before buying higher-cost
models; this configuration does not claim that benchmark has been completed.
