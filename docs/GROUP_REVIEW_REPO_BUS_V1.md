# GROUP_REVIEW Repo Bus v1

Status: **active noncanonical operating process** once merged. This is workflow infrastructure, not Garden canonical semantics or authority.

## Goal

Make multi-chat review usable from a phone with the least possible manual relay.

GitHub Issues are the durable bus. Chat memory is optional convenience only.

No Obsidian vault, Termux hashing, phone cache access, local server, or phone-side OpenRouter key is required.

## User commands

### Start / lead

In any connected Garden chat:

`group review`

That current chat becomes Leader for the current review instance under `agents/actions/group-review.json`.

The Leader discusses the situation with the user, triages it, freezes one packet, computes its SHA-256 and opens exactly one run issue:

`[GROUP_REVIEW_RUN] <problem_id>`

The issue body contains one `GardenGroupReviewPacket/v1` under the `GARDEN_GROUP_REVIEW_PACKET` marker. Every `source_ref` must be immutable: either `repo:<owner>/<repo>@<40-hex commit>:<path>` or `content:sha256:<64-hex>:<label>`. The packet must contain a `source_hashes` object whose keys exactly equal `source_refs` and whose values are SHA-256 hashes of the frozen source bytes. Mutable PR URLs, branch refs, default-branch paths and unpinned web pages are invalid blind sources.

For MATERIAL/HIGH_RISK public packets, opening that owner-authored issue automatically starts the real governed OpenRouter lane. No phone API key or manual workflow button is required.

### ChatGPT blind workers

A **fresh chat is not automatically a blind chat**. A qualifying ChatGPT worker context must exclude Garden project context, relevant memory/personal-context/prior-chat material, prior GROUP_REVIEW artifacts and peer outputs before semantic review begins. If the product cannot provide that isolation, the ChatGPT blind lane is `BLOCKED_BY_CONTEXT_ISOLATION`; do not keep asking the user to open equivalent fresh chats.

When a qualifying isolated context is available, open independent chats and say:

`group review worker A #<run_issue_number>`

and, when required:

`group review worker B #<run_issue_number>`

Each worker must:

1. establish context isolation **before** semantic review; fresh-chat identity alone is insufficient;
2. read `GIT_OPERATING_CONTEXT.md`, `AGENTS.md`, and `agents/actions/group-review.json`;
3. fetch the exact run issue by number;
4. read only the frozen packet for the blind phase and verify retrieved source bytes against the packet `source_hashes` before using them;
5. not use personal-context/memory/prior-chat retrieval and not search for or read peer worker/OpenRouter results before freezing;
6. solve the symmetric worker task independently;
7. publish a new immutable issue titled:
   `[GROUP_REVIEW_WORKER] <problem_id> <role>`;
8. bind the exact packet hash, result hash, timestamp, worker status and a machine-readable `context_isolation` attestation.

A valid semantic result uses `status=FROZEN_RESULT`, `context_isolation.status=VERIFIED`, `peer_exposure_before_freeze=NONE`, and has no excluded-context flags.

If excluded project/memory/prior-review/peer context is present, publish `PROCESS_FAIL` with no semantic findings. If the product cannot provide isolation at all, publish `BLOCKED_BY_CONTEXT_ISOLATION` with no semantic findings. After a confirmed unavailable-isolation result, do not repeat equivalent reruns until the context-isolation capability materially changes.

The worker output issue is never edited after freeze. A correction becomes a new superseding artifact.

### Optional phone-model workers

Gemini, DeepSeek, Qwen, or another phone chat can be used as additional blind workers when useful.

The Leader gives the user the exact frozen packet text. The user sends that bit-identical packet to the external phone model and returns the model's raw output unchanged.

The Leader may wrap that exact returned text as an `EXTERNAL_PHONE` worker artifact and hash it. The Leader must not rewrite the model output before freezing it.

Phone workers are optional. They do not replace the governed OpenRouter lane when that lane is required.

### Worker lifecycle checkpoints

Workers may publish hash-bound `GardenGroupReviewWorkerStatus/v1` checkpoints with states:

`STARTED -> SOURCE_HASH_VERIFIED -> BLIND_REVIEW -> FROZEN_RESULT`

or terminal:

`PROCESS_FAIL` / `BLOCKED_BY_CONTEXT_ISOLATION`.

`SOURCE_HASH_VERIFIED`, `BLIND_REVIEW`, and `FROZEN_RESULT` require verified context isolation. Status checkpoints contain no semantic findings and do not count as review evidence by themselves.

### Leader integration

After required blind outputs are frozen, return to the Leader and say:

`continue group review #<run_issue_number>`

The Leader retrieves the run issue and only then retrieves the frozen worker/OpenRouter artifacts.

The Leader:

- validates hashes;
- classifies disagreements;
- preserves minority/blocking findings;
- uses tests/direct evidence before reasoning/opinion;
- records every retained/rejected/superseded/unresolved finding;
- creates one immutable candidate issue:
  `[GROUP_REVIEW_CANDIDATE] <problem_id>`
  using `GardenGroupReviewCandidate/v1`.

A rejected minority finding always needs an evidence-backed reason.

### Verifier

In an independent verifier chat:

`group review verify #<run_issue_number>`

The Verifier reads the exact run packet, frozen blind artifacts, and frozen Leader candidate.

It first audits process integrity, then attacks the candidate.

It publishes:

`[GROUP_REVIEW_VERIFIER] <problem_id>`

using `GardenGroupReviewVerifierResult/v1`.

Allowed verdicts:

- `PASS`
- `FAIL`
- `UNKNOWN`
- `PASS_WITH_CAVEATS`

If process integrity is `FAIL` or `UNKNOWN`, the verifier cannot return `PASS` or `PASS_WITH_CAVEATS`.

A material process failure means the affected blind result cannot count toward convergence. The failed artifact remains visible as audit evidence. A rerun is appropriate only when the failure cause is materially changed. If context isolation is unavailable or an equivalent isolated attempt is still contaminated, record `BLOCKED_BY_CONTEXT_ISOLATION` and stop repeat ChatGPT-worker reruns until the product/context capability changes.

## Automatic OpenRouter lane

Workflows:

- `.github/workflows/group-review-openrouter-trigger.yml` — secret-free issue trigger and packet admission.
- `.github/workflows/group-review-openrouter.yml` — credentialed provider workflow; `workflow_dispatch` only.

Opening an owner-authored `[GROUP_REVIEW_RUN]` issue triggers only the secret-free workflow. After packet validation it dispatches the credentialed provider workflow. Each successful provider run performs one OpenRouter inference and dispatches the next provider run until the five-family blind round is complete.

Admission rules:

- packet must validate as `GardenGroupReviewPacket/v1`, including exact immutable source refs and one-for-one source SHA-256 bindings;
- `public_only=true`;
- `data_classification=PUBLIC`;
- triage must be `MATERIAL` or `HIGH_RISK`;
- `openrouter_requested=true`;
- exactly five governed ACTIVE reviewer slots;
- existing provider exclusions and budget policy apply;
- one inference per Actions dispatch;
- reviewers receive no peer output during blind review.

The first successful reviewer result causes the worker to dispatch the next family. This continues sequentially until all five are frozen.

The final public result is published as:

`[GROUP_REVIEW_OPENROUTER_RESULT] <problem_id>`

with a `GardenGroupReviewOpenRouterBundle/v1` hash.

Any UNKNOWN/RESERVED/unreconciled external call blocks further inference. No silent retry or model substitution is allowed.

## Stopping midway

Stopping a chat or leaving the app does not invalidate already frozen artifacts.

Safe checkpoints are:

- run issue frozen;
- each worker issue frozen;
- each OpenRouter reviewer receipt frozen;
- candidate issue frozen;
- verifier issue frozen.

On resume, the Leader reads the run issue plus currently available frozen artifacts and continues from the last valid checkpoint.

A partially written chat message that was never frozen is not state.

An incomplete OpenRouter call, unknown billing state, packet/source hash mismatch, mutable-source drift, peer leakage, or silently edited artifact is not treated as completed work. A source-hash mismatch after freeze is a material process failure; preserve the failed run and start a new run identity rather than silently refreshing the source.

## Minimum user work

For a normal MATERIAL review:

1. Tell one chat: `group review`.
2. Attempt Worker A/B only if a genuinely isolated ChatGPT context is available.
3. If isolation is available, send the one-line worker commands and return to Leader with `continue group review #N`.
4. If isolation is not available, record `BLOCKED_BY_CONTEXT_ISOLATION`; **do not ask the user to keep opening new equivalent chats**.
5. When a valid candidate is frozen and verifier isolation is available, run the verifier; otherwise preserve the verifier lane as non-PASS/blocked.

Authorized external review lanes remain separate. A blocked ChatGPT lane is never silently treated as satisfied by another lane unless a separately reviewed policy explicitly permits substitution.

For SMALL work, the Leader normally asks for only one blind worker and may not invoke OpenRouter or a separate Verifier.

## Security and privacy

Public GitHub issues are not a place for private, secret, credential, health, identity, or other sensitive data.

If the packet is PRIVATE or SENSITIVE:

- the automatic OpenRouter lane is prohibited;
- the Leader must use an approved private transport or keep the review inside an appropriate trusted boundary;
- redaction must happen before any public issue is created.

The repo bus never accesses phone cache, hidden ChatGPT state, or another app's private storage.
