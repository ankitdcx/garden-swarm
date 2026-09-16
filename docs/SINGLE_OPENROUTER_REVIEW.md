# Single OpenRouter review worker

Deployment status (2026-09-16): STORAGE_RULESET_OBSTRUCTION_REMOVED. The operator
installed the dedicated review-state ruleset and work-branch rules. The state
branch now blocks deletion and force pushes without requiring a pull request for
normal updates. Main remains protected by PR and required CI rules. A successful
Actions reservation write and first live provider receipt are still required;
this ruleset inspection is not a claim that OpenRouter has run.

This is a bounded activation path, not a claim that the previous multi-agent
coordinator is running. It uses the existing OPENROUTER_API_KEY Actions secret.
The older batch workflows remain paused. The existing admission guard gains one
explicit mode that verifies this worker's exact Actions workflow identity and
persistent state before exposing the inference secret. Its default legacy path
still rejects dispatch; arbitrary workflows cannot claim this new mode.

After this change is reviewed and merged, open Actions, select **Garden single
OpenRouter review**, select **Run workflow**, and use **main**. Each run makes at
most one model request. The next run continues saved progress; it does not repeat
a recorded review. No cron, background coordinator, or automatic retry is enabled.

State is retained in the [review ledger](https://github.com/ankitdcx/garden-swarm/blob/garden-review-state/review-state/ledger.json)
on the `garden-review-state` branch. A SHA-conditional GitHub write reserves the call before inference. Do not
delete/reset/rebase that branch. Missing state blocks execution. The workflow
uses the existing `garden-provider-review` concurrency group. A timeout, crash,
missing cost, unexpected provider/model, incomplete answer, or failed state write
stops the lane; an unresolved reservation requires evidence-backed reconciliation.
There is deliberately no reset button that could silently repeat a billed call.

## Review sequence

One exact public matrix target and source hash is used throughout a cycle.
The current policy allocates four reviewer families. Every family first receives
the source without peer answers. Then each challenges the previous round, revises
the proposal, and checks it again. Maximum: four rounds, sixteen calls. A no-change
challenge round can stop earlier. Completion of rounds means proposal evidence,
not agreement-as-proof, tested correctness, merge authority or canonical approval.
Unresolved objections remain in receipts. Source/policy/worker changes create a
new binding; unchanged work does not create another charge for the same slot.

The first connection test is one of these actual reviews. Each receipt contains
source hashes, requested and returned model/provider, generation identity, cost,
round, answer and structured finding. It is stored in the state branch and an
Actions artifact. An online success is not claimed until that receipt exists.

## Spending and disclosure

Only already-public canonical text with a matching SOURCE_MANIFEST hash is sent.
Private v15.7/v15.8 deltas are not eligible for this lane. The current approved
model board and exclusion policy are read at execution time. There is no silent
model replacement. Routing requires no data collection and ZDR, one allowed
endpoint, no fallbacks, live endpoint pricing and a bounded request. Those are
provider API constraints, not an independent audit of the provider's internals.

The worker reserves at most $0.05 per call and enforces at most $1 per UTC day.
It uses current key usage plus conservative local accounting, and counts all
historical key spend against the $9 routine lifetime pool. This can block early;
it cannot withdraw from the other pools. This deployment assumes the existing
Actions key is the shared Garden inference key and no other caller uses it outside
the paused legacy workers/this serialized lane. Concurrent use from another host
or another key needs shared accounting before it is admitted. Free/Gemini lanes
are not activated here, so their unavailable prior quota history is not guessed.

Remaining deployment work: prove one live receipt; inspect provider account
reconciliation; connect authenticated completion events/delayed wakes to this
same ledger; qualify free/Gemini lanes and private review routing; add test-backed
closure of findings. This worker intentionally does not claim those are complete.

Source obligations: existing agents/openrouter-paid-review-policy.json execution
limits, agents/provider-exclusion-policy.json exclusions, agents/design-review-matrix.json
independent/cross-examination requirements, and the public source status boundaries
in AGENTS.md. This is ordinary review infrastructure with no new design authority.
