# Automated OpenRouter review queue

The public worker uses the existing OPENROUTER_API_KEY Actions secret. A main-branch
material event admits source-bound work; each finished call dispatches the next
pending reviewer automatically. The older batch workflows and broader coordinator
remain paused. No model output can merge code or promote Garden semantics.

## Execution and scope

The queue covers the ten explicitly registered public targets in
`agents/design-review-matrix.json`: three bounded canonical sections and seven
implementation/governance surfaces. This is not the denominator for all Garden
modules or the five complete design documents. Private candidate content is not
sent by this lane. Canonical inputs must match SOURCE_MANIFEST; public code inputs
must be under registered implementation paths and are bound to exact file hashes.

For each target, four allocated model families review independently, then receive
previous-round findings for challenge, revision and verification. At most four
rounds run (16 successful calls per target). An all-NO_CHANGE challenge round stops
early. Unresolved objections remain proposals requiring source checks and tests;
agreement does not establish truth, independence, approval or qualification.

One workflow run makes at most one inference call. Output has an 8000-token total
ceiling (including reasoning), with concise visible JSON requested. Low reasoning
effort is requested only where the live endpoint advertises reasoning controls.
Every request is rechecked against live pricing, context and the cost reservation.
A completed but unusable response may receive one additional separately billed
attempt for that slot. The original receipt is preserved. Unknown completion or
unknown billing never authorizes a blind retry.

## Durable state and stop conditions

The [persistent ledger](https://github.com/ankitdcx/garden-swarm/blob/garden-review-state/review-state/ledger.json)
contains reservations, answers, generation identities, costs, queue status and
coverage. Both workflows share garden-provider-review concurrency. SHA-conditional
writes reserve the effect before transport; failure to save blocks the call.
Normal state writes are permitted by the installed state-branch ruleset while
force pushes and deletion remain prohibited. Main retains ordinary PR/CI gates.

The secret-free continuation workflow starts on relevant main-branch changes.
Unchanged source/policy/protocol bindings do not restart completed reviews.
Successful worker completion uses GitHub workflow_dispatch to advance. A daily
01:17 UTC recovery wake resumes only already-admitted deferred work or recovers one
unconfirmed dispatch delivery; it cannot create review work from clock passage.
This narrow recovery timer supersedes the former no-timer rule for this workflow
only. Scheduled Actions delivery may be delayed; it is not a real-time deadline.

The continuation statuses are READY, DISPATCHED, IN_FLIGHT, DEFERRED_DAILY, BLOCKED
and COMPLETE_PROPOSALS_ONLY. Setting the ledger paused field to true prevents
further calls. It cannot undo an already-issued request. BLOCKED is a visible stop,
not success; missing credentials, unavailable approved routes, unknown calls,
identity/cost mismatches and exhausted response retries require investigation.
There is no automatic reset or permission expansion. Dispatch delivery recovery
is capped at two attempts; response retry is capped at two attempts per slot.

When a response identity is available, the worker first reads generation metadata
to reconcile the saved call's identity, provider, finalized cost and terminal status. Both completion-reported and final
generation costs are retained; the larger is charged against the local budget.
Mismatching metadata remains visible in the ledger. A merged executor repair can
rearm blocked processing without changing or restarting completed review cycles.
Metadata does not repair truncated JSON or prove a finding correct. Without a
response identity, the lane stays blocked. The first live call from run 35095704429
returned truncated JSON at 1800 output tokens and reported $0.0011595; its original
UNKNOWN receipt must be reconciled, not erased or relabeled as a successful review.

## Spending and evidence

Limits remain $0.05 per call, $1 per UTC day and the $9 routine lifetime allocation.
Accounting is deliberately conservative and may stop early because provider usage
and local receipts overlap. The other budget pools are unavailable to this worker.
All admitted callers must share this ledger/key boundary; unrelated concurrent
callers cannot be accounted for safely by a repository-local lock.

Allowed models and exclusions come from the current policies. No silent model or
endpoint fallback is permitted. Requests require ZDR/no data collection; these
are routing constraints, not independent certification of provider practices.
Known costs, finish reasons and typed results persist even when review validation
fails. Each call also uploads an Actions receipt. The ledger's coverage lists
finished, pending and blocked registered targets, never whole-Garden completion.

Validation includes reservation-before-call, identity reconciliation, incomplete
answer limits, duplicate events, daily deferral, delivery recovery, provider
exclusions, completed-queue no-op and GitHub's empty 204 dispatch response. Live
activation is established only by new receipts and successor workflow runs.

Free/Gemini lanes, private candidate review, full design-section coverage and
integration of findings remain separate pending work. This configuration does not
claim Garden v15.8 is complete or automatically approved.

Sources: [GitHub workflow dispatch behavior](https://github.blog/changelog/2022-09-08-github-actions-use-github_token-with-workflow_dispatch-and-repository_dispatch/),
[OpenRouter reasoning budgets](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens),
and [generation reconciliation](https://openrouter.ai/docs/api/api-reference/generations/get-request-%26-usage-metadata-for-a-generation).

Source obligations: existing agents/openrouter-paid-review-policy.json execution
limits, agents/provider-exclusion-policy.json exclusions, agents/design-review-matrix.json
review requirements, and AGENTS.md status distinctions. The operator's explicit
request authorizes bounded automatic OpenRouter continuation; it grants no new
design authority.
