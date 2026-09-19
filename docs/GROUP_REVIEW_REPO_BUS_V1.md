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

The issue body contains one `GardenGroupReviewPacket/v1` under the `GARDEN_GROUP_REVIEW_PACKET` marker.

For MATERIAL/HIGH_RISK public packets, opening that owner-authored issue automatically starts the real governed OpenRouter lane. No phone API key or manual workflow button is required.

### ChatGPT blind workers

Open independent chats and say only:

`group review worker A #<run_issue_number>`

and, when required:

`group review worker B #<run_issue_number>`

Each worker must:

1. read `GIT_OPERATING_CONTEXT.md`, `AGENTS.md`, and `agents/actions/group-review.json`;
2. fetch the exact run issue by number;
3. read only the frozen packet for the blind phase;
4. not search for or read peer worker/OpenRouter results before freezing;
5. solve the symmetric worker task independently;
6. publish a new immutable issue titled:
   `[GROUP_REVIEW_WORKER] <problem_id> <role>`;
7. bind the exact packet hash, output hash, result hash, timestamp and `peer_exposure_before_freeze=NONE`.

The worker output issue is never edited after freeze. A correction becomes a new superseding artifact.

### Optional phone-model workers

Gemini, DeepSeek, Qwen, or another phone chat can be used as additional blind workers when useful.

The Leader gives the user the exact frozen packet text. The user sends that bit-identical packet to the external phone model and returns the model's raw output unchanged.

The Leader may wrap that exact returned text as an `EXTERNAL_PHONE` worker artifact and hash it. The Leader must not rewrite the model output before freezing it.

Phone workers are optional. They do not replace the governed OpenRouter lane when that lane is required.

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

A material process failure means the affected blind round is discarded and rerun from a new frozen run identity. The failed run remains visible as audit evidence.

## Automatic OpenRouter lane

Workflows:

- `.github/workflows/group-review-openrouter-trigger.yml` — secret-free issue trigger and packet admission.
- `.github/workflows/group-review-openrouter.yml` — credentialed provider workflow; `workflow_dispatch` only.

Opening an owner-authored `[GROUP_REVIEW_RUN]` issue triggers only the secret-free workflow. After packet validation it dispatches the credentialed provider workflow. Each successful provider run performs one OpenRouter inference and dispatches the next provider run until the five-family blind round is complete.

Admission rules:

- packet must validate as `GardenGroupReviewPacket/v1`;
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

An incomplete OpenRouter call, unknown billing state, hash mismatch, peer leakage, or silently edited artifact is not treated as completed work.

## Minimum user work

For a normal MATERIAL review:

1. Tell one chat: `group review`.
2. When it gives the run issue number, open Worker A and Worker B chats and send their one-line commands.
3. Return to Leader and say: `continue group review #N`.
4. When Leader freezes the candidate, open Verifier and send: `group review verify #N`.
5. Return to Leader and say: `continue group review #N`.

OpenRouter runs in GitHub automatically.

For SMALL work, the Leader normally asks for only one blind worker and may not invoke OpenRouter or a separate Verifier.

## Security and privacy

Public GitHub issues are not a place for private, secret, credential, health, identity, or other sensitive data.

If the packet is PRIVATE or SENSITIVE:

- the automatic OpenRouter lane is prohibited;
- the Leader must use an approved private transport or keep the review inside an appropriate trusted boundary;
- redaction must happen before any public issue is created.

The repo bus never accesses phone cache, hidden ChatGPT state, or another app's private storage.
